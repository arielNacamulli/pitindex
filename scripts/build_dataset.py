"""Build the shipped data files for ``pitindex``.

Run from the repository root:

    python -m scripts.build_dataset                 # all indices
    python -m scripts.build_dataset --index sp400   # one index

Outputs (overwritten in place), per index KEY in {sp500, sp400, sp600}:
    pitindex/data/KEY_seed.csv
    pitindex/data/KEY_changes.csv
    pitindex/data/KEY_current.csv
    pitindex/data/build_metadata.json               (shared, per-index sections)
    data/build_log.md                               (shared, per-index sections)

For the wiki-revision-seeded indices (sp400/sp600) the build also
maintains the committed revision baseline under data/:
    data/KEY_revision_events.csv
    data/KEY_revision_state.json

The script is intentionally I/O-tolerant: any single network failure
aborts the build with a clear error rather than producing partial data.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from loguru import logger as log

from . import _reconcile, _renames, _sec, _seed, _wiki, _wikirev
from ._indices import SPECS, IndexSpec

LOG_FMT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
    "<level>{level:<7}</level> "
    "<cyan>{name}</cyan> :: <level>{message}</level>"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DATA = REPO_ROOT / "pitindex" / "data"
LOG_DIR = REPO_ROOT / "data"
RENAMES_CSV = REPO_ROOT / "data" / "ticker_renames.csv"
MANUAL_CSV = REPO_ROOT / "data" / "manual_events.csv"

# A revision-diff fill event is suppressed when a precise-dated event for
# the same (ticker, action) sits within this many days of it — the fill
# and the changes-table entry describe the same underlying index change.
FILL_DEDUPE_WINDOW_DAYS = 120


def _setup_logging(verbose: bool) -> None:
    log.remove()
    log.add(
        sys.stderr,
        format=LOG_FMT,
        level="DEBUG" if verbose else "INFO",
        colorize=True,
    )


def _write_seed_csv(path: Path, effective_date: dt.date, tickers: set[str] | frozenset[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["effective_date", "ticker"])
        for t in sorted(tickers):
            w.writerow([effective_date.isoformat(), t])


def _write_changes_csv(path: Path, events: list[_wiki.ChangeEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "action", "ticker", "name", "reason"])
        for e in events:
            w.writerow([e.date, e.action, e.ticker, e.name or "", e.reason or ""])


def _write_current_csv(path: Path, current: list[_wiki.Constituent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "cik", "gics_sector", "gics_sub_industry", "date_added"])
        for c in sorted(current, key=lambda x: x.ticker):
            cik = c.cik.zfill(10) if c.cik else ""
            w.writerow(
                [
                    c.ticker,
                    c.name,
                    cik,
                    c.gics_sector or "",
                    c.gics_sub_industry or "",
                    c.date_added or "",
                ]
            )


def _dedupe_fill_events(
    fills: list[_wiki.ChangeEvent],
    precise: list[_wiki.ChangeEvent],
) -> list[_wiki.ChangeEvent]:
    """Drop fill events already explained by a precise-dated event nearby."""
    precise_dates: dict[tuple[str, str], list[dt.date]] = {}
    for e in precise:
        if e.action in {"added", "removed"}:
            precise_dates.setdefault((e.ticker, e.action), []).append(dt.date.fromisoformat(e.date))
        elif e.action == "renamed" and e.new_ticker:
            # A rename explains both the old-ticker removal and the
            # new-ticker addition a revision diff would observe.
            d = dt.date.fromisoformat(e.date)
            precise_dates.setdefault((e.ticker, "removed"), []).append(d)
            precise_dates.setdefault((e.new_ticker, "added"), []).append(d)

    kept: list[_wiki.ChangeEvent] = []
    dropped = 0
    for f in fills:
        f_date = dt.date.fromisoformat(f.date)
        nearby = precise_dates.get((f.ticker, f.action), [])
        if any(abs((f_date - d).days) <= FILL_DEDUPE_WINDOW_DAYS for d in nearby):
            dropped += 1
            continue
        kept.append(f)
    log.info("Fill dedupe: kept {}, dropped {} (explained by precise-dated events)", len(kept), dropped)
    return kept


def build_index(
    spec: IndexSpec,
    *,
    today: dt.date,
    max_diff_ratio: float,
    cached_html: str | None = None,
    cached_changes_html: str | None = None,
    cached_seed: str | None = None,
    sec_map: dict[str, str] | None = None,
) -> tuple[dict, _reconcile.ReconciliationReport]:
    """Build one index end-to-end and write its per-index data files."""
    key = spec.key

    # -- 1. Wikipedia (roster page + historical-components page) -------------
    log.info("[{}] Fetching Wikipedia '{}'...", key, spec.wiki_title)
    html = Path(cached_html).read_text(encoding="utf-8") if cached_html else _wiki.fetch_html(spec.wiki_url)
    current = _wiki.parse_current_constituents(html)
    # Since 2026-08-11 the changes table lives on its own article; keep reading
    # the roster page too, so a revert of that split needs no code change.
    log.info("[{}] Fetching changes from '{}'...", key, spec.changes_url)
    changes_html = (
        Path(cached_changes_html).read_text(encoding="utf-8")
        if cached_changes_html
        else _wiki.fetch_html(spec.changes_url)
    )
    wiki_events = _wiki.parse_changes(html, changes_html)
    log.info("[{}] Wikipedia: {} current constituents, {} change events", key, len(current), len(wiki_events))
    if not (spec.roster_band[0] <= len(current) <= spec.roster_band[1]):
        raise RuntimeError(
            f"[{key}] current roster size {len(current)} outside sanity band {spec.roster_band}."
        )

    # -- 1b. Correct/fill CIKs against the SEC's official mapping ------------
    cik_corrected = cik_filled = 0
    if sec_map:
        current, cik_corrected, cik_filled = _sec.correct_ciks(current, sec_map, key)
        if cik_corrected or cik_filled:
            log.info("[{}] CIKs: {} corrected, {} filled from SEC map", key, cik_corrected, cik_filled)

    # -- 2. Seed + primary event source, per strategy -------------------------
    if spec.seed_strategy == "fja05680":
        log.info("[{}] Fetching fja05680 seed dataset...", key)
        seed_csv = Path(cached_seed).read_text(encoding="utf-8") if cached_seed else _seed.fetch_seed_csv()
        seed_effective_date, seed_roster, seed_events, last_seed_date = _seed.derive_events(
            seed_csv, spec.start_date
        )
        # Seed events are authoritative within their window; Wikipedia's
        # changes table covers only the post-seed tail.
        last_seed_iso = last_seed_date.isoformat()
        wiki_tail = [e for e in wiki_events if e.date > last_seed_iso]
        log.info(
            "[{}] {} seed-derived events (≤ {}) + {} Wikipedia events (> {})",
            key,
            len(seed_events),
            last_seed_iso,
            len(wiki_tail),
            last_seed_iso,
        )
        primary_events = seed_events + wiki_tail
        fill_events: list[_wiki.ChangeEvent] = []
        seed_source = f"https://github.com/{_seed.GITHUB_REPO}"
    elif spec.seed_strategy == "wiki_revision":
        log.info("[{}] Deriving seed + fill events from the page revision history...", key)
        seed_effective_date, seed_roster_frozen, fill_events = _wikirev.build_revision_events(
            title=spec.wiki_title,
            start_date=spec.start_date,
            band=spec.roster_band,
            events_csv=LOG_DIR / f"{key}_revision_events.csv",
            state_json=LOG_DIR / f"{key}_revision_state.json",
        )
        seed_roster = set(seed_roster_frozen)
        # The changes table is the precise-dated source for the whole
        # window (there is no fja05680 equivalent for these indices).
        primary_events = [e for e in wiki_events if e.date >= seed_effective_date.isoformat()]
        seed_source = f"wikipedia revision history of '{spec.wiki_title}'"
    else:  # pragma: no cover - registry is static
        raise ValueError(f"Unknown seed strategy {spec.seed_strategy!r}")

    # -- 3. Curated overrides -------------------------------------------------
    rename_events = _renames.load_renames(RENAMES_CSV)
    manual_events = _renames.load_manual_events(MANUAL_CSV, index=key)

    # -- 3b. Revision-diff fills only where nothing precise explains them ----
    if fill_events:
        fill_events = _dedupe_fill_events(fill_events, primary_events + rename_events + manual_events)

    merged_events = primary_events + fill_events + rename_events + manual_events

    # -- 4. Reconcile ----------------------------------------------------------
    log.info("[{}] Reconciling event log against current roster...", key)
    reconciled, report = _reconcile.reconcile(
        seed_roster=seed_roster,
        start_date=seed_effective_date,
        events=merged_events,
        current=current,
        end_date=today,
        max_diff_ratio=max_diff_ratio,
    )
    log.info(
        "[{}] Reconciliation OK: diff_ratio={:.2f}%, {} synthetic events",
        key,
        report.diff_ratio * 100,
        report.synthetic_events_added,
    )

    # -- 5. Persist ------------------------------------------------------------
    _write_seed_csv(PACKAGE_DATA / f"{key}_seed.csv", seed_effective_date, seed_roster)
    _write_changes_csv(PACKAGE_DATA / f"{key}_changes.csv", reconciled)
    _write_current_csv(PACKAGE_DATA / f"{key}_current.csv", current)

    meta = {
        "start_date": seed_effective_date.isoformat(),
        "end_date": today.isoformat(),
        "seed_source": seed_source,
        "wikipedia_source": spec.wiki_url,
        "wikipedia_changes_source": spec.changes_url,
        "current_size": report.current_size,
        "seed_size": report.seed_size,
        "events_count": len(reconciled),
        "diff_ratio": report.diff_ratio,
        "synthetic_events": report.synthetic_events_added,
        "renames_applied": report.renames_applied,
        "cik_corrected_from_sec": cik_corrected,
        "cik_filled_from_sec": cik_filled,
    }
    return meta, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build pitindex data files.")
    parser.add_argument(
        "--index",
        default="all",
        choices=["all", *SPECS],
        help="Which index to build (default: %(default)s).",
    )
    parser.add_argument(
        "--max-diff-ratio", type=float, default=0.05, help="Reconciliation tolerance (default: %(default)s)."
    )
    parser.add_argument(
        "--cached-html", default=None, help="Path to a local sp500 HTML file for offline testing."
    )
    parser.add_argument(
        "--cached-changes-html",
        default=None,
        help="Path to a local sp500 'Historical components' HTML file for offline testing.",
    )
    parser.add_argument("--cached-seed", default=None, help="Path to a local seed CSV for offline testing.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    today = dt.date.today()
    keys = list(SPECS) if args.index == "all" else [args.index]

    PACKAGE_DATA.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    metadata_path = PACKAGE_DATA / "build_metadata.json"
    existing_indices: dict[str, dict] = {}
    if metadata_path.exists():
        try:
            existing_indices = json.loads(metadata_path.read_text(encoding="utf-8")).get("indices", {})
        except (json.JSONDecodeError, OSError):
            existing_indices = {}

    log.info("Fetching the SEC ticker→CIK map...")
    sec_map = _sec.fetch_sec_ticker_map()

    report_sections: list[str] = []
    indices_meta: dict[str, dict] = dict(existing_indices)
    for key in keys:
        spec = SPECS[key]
        try:
            meta, report = build_index(
                spec,
                today=today,
                max_diff_ratio=args.max_diff_ratio,
                cached_html=args.cached_html if key == "sp500" else None,
                cached_changes_html=args.cached_changes_html if key == "sp500" else None,
                cached_seed=args.cached_seed if key == "sp500" else None,
                sec_map=sec_map,
            )
        except _reconcile.ReconciliationError as exc:
            report_sections.append(f"# {key}\n\n" + _reconcile.render_report_md(exc.report))
            (LOG_DIR / "build_log.md").write_text("\n\n".join(report_sections), encoding="utf-8")
            log.error("[{}] Reconciliation failed: {}", key, exc)
            log.error("See data/build_log.md for details.")
            return 2
        indices_meta[key] = meta
        report_sections.append(f"# {key}\n\n" + _reconcile.render_report_md(report))

    payload: dict = {
        "build_timestamp_utc": dt.datetime.now(dt.UTC).isoformat(),
        "indices": indices_meta,
    }
    # Legacy top-level sp500 keys, kept for pre-0.2 consumers of info().
    payload.update(indices_meta.get("sp500", {}))
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    (LOG_DIR / "build_log.md").write_text("\n\n".join(report_sections), encoding="utf-8")

    log.info("Build complete ({}). Data written to {}", ", ".join(keys), PACKAGE_DATA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
