"""Build the shipped data files for ``pitindex``.

Run from the repository root:

    python -m scripts.build_dataset

Outputs (overwritten in place):
    pitindex/data/sp500_seed.csv
    pitindex/data/sp500_changes.csv
    pitindex/data/sp500_current.csv
    pitindex/data/build_metadata.json
    data/build_log.md

The script is intentionally I/O-tolerant: any single network failure
aborts the build with a clear error rather than producing partial data.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import sys
from pathlib import Path

from . import _reconcile, _renames, _seed, _wiki

LOG_FMT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DATA = REPO_ROOT / "pitindex" / "data"
LOG_DIR = REPO_ROOT / "data"
RENAMES_CSV = REPO_ROOT / "data" / "ticker_renames.csv"
MANUAL_CSV = REPO_ROOT / "data" / "manual_events.csv"

DEFAULT_START = dt.date(2005, 1, 3)  # First trading day of 2005


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        format=LOG_FMT,
        level=logging.DEBUG if verbose else logging.INFO,
    )


def _write_seed_csv(path: Path, effective_date: dt.date, tickers: set[str]) -> None:
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
            w.writerow([
                c.ticker, c.name, cik,
                c.gics_sector or "", c.gics_sub_industry or "",
                c.date_added or "",
            ])


def _write_metadata(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build pitindex data files.")
    parser.add_argument("--start-date", default=DEFAULT_START.isoformat(),
                        help="Bootstrap date (default: %(default)s).")
    parser.add_argument("--max-diff-ratio", type=float, default=0.05,
                        help="Reconciliation tolerance (default: %(default)s).")
    parser.add_argument("--seed-url", default=None,
                        help="Override the seed CSV URL (otherwise auto-discovered).")
    parser.add_argument("--cached-html", default=None,
                        help="Path to a local HTML file for offline testing.")
    parser.add_argument("--cached-seed", default=None,
                        help="Path to a local seed CSV for offline testing.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    start_date = dt.date.fromisoformat(args.start_date)
    today = dt.date.today()
    log = logging.getLogger("build")

    # -- 1. Wikipedia --------------------------------------------------------
    log.info("Fetching Wikipedia 'List of S&P 500 companies'...")
    if args.cached_html:
        html = Path(args.cached_html).read_text(encoding="utf-8")
    else:
        html = _wiki.fetch_html()
    current = _wiki.parse_current_constituents(html)
    wiki_events = _wiki.parse_changes(html)
    log.info("Wikipedia: %d current constituents, %d change events", len(current), len(wiki_events))

    # -- 2. Seed-derived events (primary, complete) --------------------------
    log.info("Fetching seed dataset...")
    if args.cached_seed:
        seed_csv = Path(args.cached_seed).read_text(encoding="utf-8")
    else:
        seed_csv = _seed.fetch_seed_csv(args.seed_url)
    seed_effective_date, seed_roster, seed_events, last_seed_date = _seed.derive_events(
        seed_csv, start_date,
    )

    # -- 3. Merge: seed events for the seed-covered window, then Wikipedia events
    #     for everything strictly after the last seed snapshot.
    last_seed_iso = last_seed_date.isoformat()
    wiki_tail = [e for e in wiki_events if e.date > last_seed_iso]
    log.info(
        "Combining %d seed-derived events (≤ %s) with %d Wikipedia events (> %s)",
        len(seed_events), last_seed_iso, len(wiki_tail), last_seed_iso,
    )

    # -- 3b. Curated rename events (close gaps Wikipedia/seed don't track) ---
    rename_events = _renames.load_renames(RENAMES_CSV)
    log.info("Loaded %d curated rename events", len(rename_events))

    # -- 3c. Manual override events (cover seed dataset errors and omissions) ---
    manual_events = _renames.load_manual_events(MANUAL_CSV)
    log.info("Loaded %d manual override events", len(manual_events))

    merged_events = seed_events + wiki_tail + rename_events + manual_events

    # -- 4. Reconcile --------------------------------------------------------
    log.info("Reconciling event log against current roster...")
    try:
        reconciled, report = _reconcile.reconcile(
            seed_roster=seed_roster,
            start_date=seed_effective_date,
            events=merged_events,
            current=current,
            end_date=today,
            max_diff_ratio=args.max_diff_ratio,
        )
    except _reconcile.ReconciliationError as exc:
        # Even on failure, dump the report for debugging
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / "build_log.md").write_text(
            _reconcile.render_report_md(exc.report), encoding="utf-8")
        log.error("Reconciliation failed: %s", exc)
        log.error("See data/build_log.md for details.")
        return 2

    log.info(
        "Reconciliation OK: diff_ratio=%.2f%%, %d synthetic events inserted",
        report.diff_ratio * 100, report.synthetic_events_added,
    )

    # -- 4. Persist ----------------------------------------------------------
    PACKAGE_DATA.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    _write_seed_csv(PACKAGE_DATA / "sp500_seed.csv", seed_effective_date, seed_roster)
    _write_changes_csv(PACKAGE_DATA / "sp500_changes.csv", reconciled)
    _write_current_csv(PACKAGE_DATA / "sp500_current.csv", current)
    _write_metadata(PACKAGE_DATA / "build_metadata.json", {
        "build_timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "start_date": seed_effective_date.isoformat(),
        "end_date": today.isoformat(),
        "seed_source": f"https://github.com/{_seed.GITHUB_REPO}",
        "wikipedia_source": _wiki.WIKI_URL,
        "current_size": report.current_size,
        "seed_size": report.seed_size,
        "events_count": len(reconciled),
        "diff_ratio": report.diff_ratio,
        "synthetic_events": report.synthetic_events_added,
    })

    (LOG_DIR / "build_log.md").write_text(
        _reconcile.render_report_md(report), encoding="utf-8")

    log.info("Build complete. Data written to %s", PACKAGE_DATA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
