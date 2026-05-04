# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install package + build/dev extras
pip install -e ".[build,dev]"

# Run all gates (mirrors CI)
ruff check pitindex scripts tests
ruff format --check pitindex scripts tests
mypy pitindex
pytest --cov=pitindex --cov-report=term-missing

# Run a single test
pytest tests/test_known_dates.py::test_known_membership

# Rebuild the bundled dataset from upstream sources
python -m scripts.build_dataset -v

# CLI
pitindex --help
pitindex info
pitindex get --as-of 2020-12-22
pitindex history --start 2015-01-01 --end 2015-12-31
pitindex update
pitindex build
```

## Architecture

`pitindex` is a point-in-time index-membership lookup library, the
sister package to [`pitedgar`](https://github.com/arielNacamulli/pitedgar)
(SEC EDGAR fundamental data). Both share the "PIT" branding and the
no-look-ahead-bias philosophy: every value is stamped with the date it
became publicly known, not the date it nominally refers to.

The runtime model is **event-sourcing on a tiny event log** — a seed
roster snapshot at `start_date` plus a chronological list of add/remove
events. To get the membership at any point in time `T`, walk events in
order up to `T`, applying each one to a running set. Naive O(N) walk
per query is < 1 ms — there is no need for a more sophisticated index.

### Data pipeline (`scripts/`)

Three trust-ordered sources are merged into a single event log:

1. **`scripts/_seed.py`** — fetches the
   [`fja05680/sp500`](https://github.com/fja05680/sp500) dataset (daily
   snapshots 1996→2019) via the GitHub Contents API, normalizes the
   `-YYYYMM` exit-date suffix encoding, and computes events as diffs
   between consecutive snapshots. Primary source for the seed-covered
   window because Wikipedia's "Selected changes" table is not
   exhaustive (many 2008-financial-crisis exits are absent there).
2. **`scripts/_wiki.py`** — fetches Wikipedia's "List of S&P 500
   companies" page, parses the two stable-id tables (`#constituents`
   and `#changes`) with BeautifulSoup. Provides the current roster (CIK
   + GICS sector) and the change events for the post-seed tail.
3. **`scripts/_renames.py`** — loads two curated CSVs:
   - `data/ticker_renames.csv` — ticker changes for continuing
     constituents (FB → META, PX → LIN, MMC → MRSH, …) which neither
     source tracks because the *company* didn't enter or leave.
   - `data/manual_events.csv` — explicit add/remove events that fix
     known seed errors (e.g. period-correct `LEH` for Lehman where the
     seed encodes the post-bankruptcy `LEHMQ` throughout).

`scripts/_reconcile.py` is the **reconciliation gate**: walks the seed
forward through merged events and compares against the current
Wikipedia roster. Aborts the build if `diff_ratio > 5%`. The build log
lands in `data/build_log.md`.

`scripts/build_dataset.py` is the orchestrator. Outputs four files
under `pitindex/data/`:
- `sp500_seed.csv` — initial roster at `start_date`
- `sp500_changes.csv` — chronological event log (post-reconciliation)
- `sp500_current.csv` — current roster with full metadata
- `build_metadata.json` — build timestamp, sources, sizes, diff ratio

### Runtime (`pitindex/`)

- **`pitindex/_loader.py`** — lazy CSV loaders. Uses
  `importlib.resources` for the bundled data and falls back to a user
  cache directory (`~/.cache/pitindex/` or `$PITINDEX_CACHE_DIR`) for
  fresher data injected by `pitindex.update()`.
- **`pitindex/_api.py`** — public API: `get_constituents`,
  `get_constituents_history`, `info`, `update`, plus the `PitIndex`
  class wrapper (mirrors the `pitedgar.PitQuery` shape) and the
  `StaleDataWarning` (emitted on first call when the bundled data
  exceeds `PITINDEX_STALE_DAYS`, default 14).
- **`pitindex/cli.py`** — Click-based CLI (`pitindex info|get|history|update|build`).

### How freshness works

Two complementary mechanisms:

1. **Maintainer-side**: `.github/workflows/weekly-refresh.yml` runs the
   build pipeline every Monday 06:00 UTC and commits any drift back to
   `master`. Releases cut from those commits, so `pip install -U
   pitindex` always pulls the latest weekly snapshot.
2. **User-side**: `_api._maybe_warn_stale()` raises
   `StaleDataWarning` on the first API call when the bundled data is
   older than the threshold, with an actionable message ("upgrade or
   call `update()`"). Configure with `PITINDEX_STALE_DAYS` env var
   (set to `0` to opt out).

### Adding a new ticker rename

The most common contribution. Append a row to
`data/ticker_renames.csv`, re-run `python -m scripts.build_dataset`,
commit the regenerated files in `pitindex/data/`. The reconciliation
gate validates the change automatically.
