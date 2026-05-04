"""Bootstrap and event derivation from the ``fja05680/sp500`` dataset.

The community-maintained ``fja05680/sp500`` repository hosts a
multi-decade history of S&P 500 membership encoded as a CSV of
date-stamped snapshots. We use it for two things:

1. **Seed roster**: the membership set at our chosen ``start_date``.
2. **Event derivation 2005-2019**: the diff between consecutive snapshots
   gives us add/remove events with date precision sufficient for PIT
   queries.

We deliberately rely on the seed dataset for events through its end
date (~2019-01-11) because Wikipedia's "Selected changes" table is
known to be incomplete (it omits, e.g., 2008 financial-crisis exits
like Lehman, Bear Stearns, WaMu). For dates *after* the seed ends, we
fall back to Wikipedia's event log.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re

import requests
from loguru import logger as log

from ._wiki import ChangeEvent

GITHUB_REPO = "fja05680/sp500"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
USER_AGENT = "pitindex/0.1 (+https://github.com/arielnacamulli/pitindex)"

SEED_FILE_PATTERN = re.compile(r"S&P\s*500\s*Historical\s*Components.*\.csv$", re.IGNORECASE)
_SEED_SUFFIX_RE = re.compile(r"-\d{6}$")


def _find_seed_url() -> str:
    r = requests.get(
        GITHUB_API,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    r.raise_for_status()
    candidates = [
        item
        for item in r.json()
        if item.get("type") == "file" and SEED_FILE_PATTERN.search(item.get("name", ""))
    ]
    if not candidates:
        raise RuntimeError(
            f"Could not find a seed CSV in {GITHUB_REPO}. Repository structure may have changed."
        )
    candidates.sort(key=lambda c: c["name"], reverse=True)
    return candidates[0]["download_url"]


def fetch_seed_csv(url: str | None = None) -> str:
    url = url or _find_seed_url()
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    return r.text


def _normalize(tickers: set[str]) -> set[str]:
    """Strip the ``-YYYYMM`` future-removal annotation from seed tickers.

    The fja05680 dataset annotates delisted tickers with ``-YYYYMM`` as
    a forward-looking note (e.g. ``ABS-200606`` means ABS, scheduled to
    leave in 2006-06). The annotation is metadata about the eventual
    exit and is not part of the symbol. Class-share tickers already use
    dot notation (``BF.B``) and pass through untouched.
    """
    out: set[str] = set()
    for raw in tickers:
        cleaned = _SEED_SUFFIX_RE.sub("", raw.strip().upper())
        if cleaned:
            out.add(cleaned)
    return out


def _parse_snapshots(seed_csv: str) -> list[tuple[dt.date, set[str]]]:
    """Return the full list of (date, normalized ticker set) from the seed."""
    reader = csv.reader(io.StringIO(seed_csv))
    next(reader, None)  # header
    out: list[tuple[dt.date, set[str]]] = []
    for row in reader:
        if not row:
            continue
        try:
            d = dt.date.fromisoformat(row[0].strip())
        except ValueError:
            continue
        if len(row) == 2:
            tickers = {t.strip() for t in row[1].split(",") if t.strip()}
        else:
            tickers = {t.strip() for t in row[1:] if t and t.strip()}
        out.append((d, _normalize(tickers)))
    out.sort(key=lambda p: p[0])
    return out


def roster_at(seed_csv: str, start_date: dt.date) -> tuple[dt.date, set[str]]:
    """Return ``(effective_date, tickers)`` for the snapshot at or before ``start_date``."""
    snaps = _parse_snapshots(seed_csv)
    best: tuple[dt.date, set[str]] | None = None
    for d, tickers in snaps:
        if d > start_date:
            break
        best = (d, tickers)
    if best is None:
        raise RuntimeError(
            f"No seed row at or before {start_date.isoformat()}. Seed dataset may not cover that range."
        )
    log.info("Seed roster: {} tickers as of {}", len(best[1]), best[0])
    return best


def derive_events(
    seed_csv: str,
    start_date: dt.date,
    end_date: dt.date | None = None,
) -> tuple[dt.date, set[str], list[ChangeEvent], dt.date]:
    """Derive add/remove events from snapshot diffs.

    Returns
    -------
    seed_effective_date : dt.date
        Date of the snapshot used as the starting point.
    seed_roster : set[str]
        Tickers in the index at ``seed_effective_date``.
    events : list[ChangeEvent]
        Events derived from consecutive-snapshot diffs, dated to the
        *later* snapshot in each pair, restricted to the window.
    last_seed_date : dt.date
        Date of the most-recent snapshot in the seed dataset. Callers
        should treat dates after this as "out-of-coverage" for the seed
        and route them through an alternative source (e.g. Wikipedia).
    """
    snaps = _parse_snapshots(seed_csv)
    if not snaps:
        raise RuntimeError("Seed dataset has no parseable rows.")

    # Find the seed roster (snapshot at or before start_date)
    seed_idx = -1
    for i, (d, _) in enumerate(snaps):
        if d <= start_date:
            seed_idx = i
        else:
            break
    if seed_idx < 0:
        raise RuntimeError(
            f"No seed row at or before {start_date.isoformat()}. "
            f"Seed dataset starts at {snaps[0][0].isoformat()}."
        )

    seed_effective_date, seed_roster = snaps[seed_idx]
    last_seed_date = snaps[-1][0]
    end = end_date or last_seed_date

    events: list[ChangeEvent] = []
    prev = seed_roster
    for d, tickers in snaps[seed_idx + 1 :]:
        if d > end:
            break
        added = tickers - prev
        removed = prev - tickers
        for t in sorted(added):
            events.append(
                ChangeEvent(
                    date=d.isoformat(),
                    action="added",
                    ticker=t,
                    name=None,
                    reason="derived from seed snapshot diff",
                )
            )
        for t in sorted(removed):
            events.append(
                ChangeEvent(
                    date=d.isoformat(),
                    action="removed",
                    ticker=t,
                    name=None,
                    reason="derived from seed snapshot diff",
                )
            )
        prev = tickers

    log.info(
        "Seed-derived: {} events from {} to {} (seed end = {})",
        len(events),
        seed_effective_date,
        end,
        last_seed_date,
    )
    return seed_effective_date, seed_roster, events, last_seed_date


__all__ = [
    "derive_events",
    "fetch_seed_csv",
    "roster_at",
]
