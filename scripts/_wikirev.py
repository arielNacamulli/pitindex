"""Event derivation from the Wikipedia page *revision history*.

For sp400/sp600 there is no equivalent of the fja05680 seed dataset, and
the pages' "changes" tables are measurably incomplete (see DESIGN.md §3).
This module recovers the missing events from the page history itself:

1. List all revisions of the page via the MediaWiki API.
2. Sample the last revision of each calendar month.
3. Render + parse the constituents table at each sample (lenient: falls
   back to header-based table detection for revisions that predate the
   stable ``id="constituents"`` markup), rejecting rosters outside the
   index's sanity band.
4. Diff consecutive rosters into add/remove events, dated at the
   revision timestamp (an upper bound on the effective date — PIT-safe).

The derived events are persisted under ``data/`` as a committed baseline
(events CSV + state JSON) so that weekly builds only extend the tail
instead of re-rendering 15 years of revisions.
"""

from __future__ import annotations

import csv
import datetime as dt
import itertools
import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from loguru import logger as log

from ._wiki import ChangeEvent, parse_constituents_table

API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "pitindex/0.2 (+https://github.com/arielnacamulli/pitindex) python-requests"
_HEADERS = {"User-Agent": USER_AGENT}
_SLEEP_S = 0.3  # courtesy pause between rendered-revision fetches


@dataclass(frozen=True)
class RevisionSample:
    revid: int
    timestamp: str  # full ISO timestamp from the API
    roster: frozenset[str]

    @property
    def date(self) -> str:
        return self.timestamp[:10]


def list_revisions(title: str, timeout: int = 30) -> list[tuple[int, str]]:
    """Return [(revid, timestamp), ...] oldest-first for the full page history."""
    out: list[tuple[int, str]] = []
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "ids|timestamp",
        "rvlimit": 500,
        "rvdir": "newer",
        "format": "json",
        "formatversion": 2,
    }
    cont: dict[str, str] = {}
    while True:
        r = requests.get(API_URL, params={**params, **cont}, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        page = j["query"]["pages"][0]
        for rev in page.get("revisions", []):
            out.append((rev["revid"], rev["timestamp"]))
        cont = j.get("continue") or {}
        if not cont:
            return out


def monthly_samples(revisions: list[tuple[int, str]], after: str | None = None) -> list[tuple[int, str]]:
    """Last revision of each calendar month (plus the very last revision).

    ``after`` (ISO timestamp) restricts to strictly-newer revisions — used
    to extend an existing baseline without re-rendering its window.
    """
    if after:
        revisions = [rv for rv in revisions if rv[1] > after]
    by_month: dict[str, tuple[int, str]] = {}
    for revid, ts in revisions:
        by_month[ts[:7]] = (revid, ts)  # revisions are oldest-first: keeps the last
    picked = sorted(by_month.values(), key=lambda rv: rv[1])
    if revisions and (not picked or picked[-1][0] != revisions[-1][0]):
        picked.append(revisions[-1])
    return picked


def fetch_roster(revid: int, band: tuple[int, int], timeout: int = 60) -> frozenset[str] | None:
    """Render one revision and parse its roster; None when unusable."""
    r = requests.get(
        API_URL,
        params={"action": "parse", "oldid": revid, "prop": "text", "format": "json"},
        headers=_HEADERS,
        timeout=timeout,
    )
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        log.debug("rev {}: parse API error {}", revid, j["error"].get("code"))
        return None
    html = j["parse"]["text"]["*"]
    soup = BeautifulSoup(html, "lxml")

    tables = []
    table = soup.find("table", id="constituents")
    if table is not None:
        tables = [table]
    else:
        # Pre-2021 revisions lack the stable id: consider every table whose
        # header carries both a symbol/ticker and a company/security column,
        # largest first.
        for t in soup.find_all("table"):
            first_row = t.find("tr")
            if first_row is None:
                continue
            hdr = " ".join(c.get_text(" ", strip=True).lower() for c in first_row.find_all(["th", "td"]))
            if ("symbol" in hdr or "ticker" in hdr) and ("security" in hdr or "company" in hdr):
                tables.append(t)
        tables.sort(key=lambda t: len(t.find_all("tr")), reverse=True)

    for t in tables:
        try:
            roster = frozenset(c.ticker for c in parse_constituents_table(t))
        except RuntimeError:
            continue
        if band[0] <= len(roster) <= band[1]:
            return roster
        log.debug("rev {}: roster size {} outside band {}", revid, len(roster), band)
    return None


def derive_fill_events(samples: list[RevisionSample]) -> list[ChangeEvent]:
    """Diff consecutive sampled rosters into add/remove events."""
    events: list[ChangeEvent] = []
    for prev, cur in itertools.pairwise(samples):
        provenance = f"derived from wiki revision diff (rev {cur.revid} @ {cur.date}, prev {prev.date})"
        for t in sorted(cur.roster - prev.roster):
            events.append(
                ChangeEvent(
                    date=cur.date, action="added", ticker=t, name=None, reason=provenance, origin="fill"
                )
            )
        for t in sorted(prev.roster - cur.roster):
            events.append(
                ChangeEvent(
                    date=cur.date, action="removed", ticker=t, name=None, reason=provenance, origin="fill"
                )
            )
    return events


# --- committed baseline ------------------------------------------------------


def load_baseline(events_csv: Path, state_json: Path) -> tuple[list[ChangeEvent], dict | None]:
    if not (events_csv.exists() and state_json.exists()):
        return [], None
    events: list[ChangeEvent] = []
    with events_csv.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            events.append(
                ChangeEvent(
                    date=row["date"],
                    action=row["action"],
                    ticker=row["ticker"],
                    name=row["name"] or None,
                    reason=row["reason"] or None,
                    origin="fill",  # everything in the baseline is revision-derived
                )
            )
    with state_json.open("r", encoding="utf-8") as f:
        state = json.load(f)
    return events, state


def save_baseline(
    events_csv: Path,
    state_json: Path,
    events: list[ChangeEvent],
    last: RevisionSample,
    seed_date: str,
    seed_roster: frozenset[str],
) -> None:
    events_csv.parent.mkdir(parents=True, exist_ok=True)
    with events_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "action", "ticker", "name", "reason"])
        for e in sorted(events, key=lambda e: (e.date, e.action, e.ticker)):
            w.writerow([e.date, e.action, e.ticker, e.name or "", e.reason or ""])
    with state_json.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "seed_date": seed_date,
                "seed_roster": sorted(seed_roster),
                "last_revid": last.revid,
                "last_rev_timestamp": last.timestamp,
                "last_roster": sorted(last.roster),
            },
            f,
            indent=1,
        )


def build_revision_events(
    title: str,
    start_date: dt.date,
    band: tuple[int, int],
    events_csv: Path,
    state_json: Path,
) -> tuple[dt.date, frozenset[str], list[ChangeEvent]]:
    """Return ``(seed_date, seed_roster, fill_events)`` for one index.

    Incremental: when a committed baseline exists, only revisions newer
    than its ``last_rev_timestamp`` are rendered; the baseline files are
    rewritten with the extended tail (committable drift, like the other
    data outputs).
    """
    baseline_events, state = load_baseline(events_csv, state_json)
    revisions = list_revisions(title)
    log.info("{}: {} revisions in page history", title, len(revisions))

    if state is not None:
        prior = RevisionSample(
            revid=state["last_revid"],
            timestamp=state["last_rev_timestamp"],
            roster=frozenset(state["last_roster"]),
        )
        samples = [prior]
        picked = monthly_samples(revisions, after=state["last_rev_timestamp"])
        seed_date = dt.date.fromisoformat(state["seed_date"])
        seed_roster = frozenset(state["seed_roster"])
    else:
        samples = []
        # Start sampling one month before the floor so the seed snapshot
        # is the newest usable revision at or before start_date.
        picked = monthly_samples(revisions)
        picked = [rv for rv in picked if rv[1][:10] >= (start_date - dt.timedelta(days=45)).isoformat()]
        seed_date = start_date
        seed_roster = frozenset()

    skipped = 0
    for revid, ts in picked:
        roster = fetch_roster(revid, band)
        time.sleep(_SLEEP_S)
        if roster is None:
            skipped += 1
            continue
        samples.append(RevisionSample(revid=revid, timestamp=ts, roster=roster))

    if state is None:
        if not samples:
            raise RuntimeError(f"{title}: no parseable revision found at or after {start_date}.")
        seed_date = dt.date.fromisoformat(samples[0].date)
        seed_roster = samples[0].roster

    new_events = derive_fill_events(samples)
    all_events = baseline_events + new_events
    log.info(
        "{}: {} baseline + {} new fill events ({} samples skipped)",
        title,
        len(baseline_events),
        len(new_events),
        skipped,
    )
    if samples:
        save_baseline(events_csv, state_json, all_events, samples[-1], seed_date.isoformat(), seed_roster)
    return seed_date, seed_roster, all_events


__all__ = [
    "RevisionSample",
    "build_revision_events",
    "derive_fill_events",
    "fetch_roster",
    "list_revisions",
    "monthly_samples",
]
