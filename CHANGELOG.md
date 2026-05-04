# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-04

Initial release. Point-in-time S&P 500 constituents from free public sources,
with PIT coverage from 2005-01-03 through today.

### Added
- Build pipeline (`scripts/build_dataset.py`) combining three trust-ordered sources:
  the `fja05680/sp500` daily seed (1996–2019), Wikipedia "List of S&P 500
  companies" (current roster + post-2019 events), and curated CSVs in `data/`
  for ticker renames (`ticker_renames.csv`) and explicit override events
  (`manual_events.csv`) that close gaps neither source captures.
- Reconciliation gate (`scripts/_reconcile.py`): the seed roster walked
  forward through merged events must reproduce the current Wikipedia roster
  within `max_diff_ratio` (default 5%); the build fails loud above the
  threshold and dumps `data/build_log.md` for debugging.
- Runtime API:
  - `pitindex.get_constituents(as_of)` returns the membership snapshot at
    the end of the given date as a `pandas.DataFrame`
    (`ticker, name, cik, gics_sector, gics_sub_industry`).
  - `pitindex.get_constituents_history(start, end)` returns one snapshot
    per change date in the window (sparse).
  - `pitindex.update(force=False)` re-runs the build into
    `~/.cache/pitindex/`, taking precedence over the bundled data.
  - `pitindex.info()` exposes build metadata and staleness flags.
  - `pitindex.PitIndex` thin class wrapper mirroring the
    `pitedgar.PitQuery` shape (`as_of`, `history`, `info`).
- `pitindex.StaleDataWarning` automatically emitted by the runtime when
  the bundled data exceeds the freshness threshold (default 14 days,
  configurable via `PITINDEX_STALE_DAYS`).
- CLI (`pitindex info|get|history|update|build`) via Click.
- CI: `.github/workflows/ci.yml` runs ruff lint + format + mypy + pytest
  with coverage on Python 3.11 / 3.12. `weekly-refresh.yml` rebuilds the
  data every Monday 06:00 UTC and commits drift back to `master`.
  `release.yml` publishes to PyPI on tag push via OIDC trusted publishing.

[Unreleased]: https://github.com/arielNacamulli/pitindex/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/arielNacamulli/pitindex/releases/tag/v0.1.0
