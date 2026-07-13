# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-07-13

### Added
- Build-time CIK validation against the SEC's official
  `company_tickers.json` (`scripts/_sec.py`): fills the CIKs the S&P 400
  wiki page doesn't carry at all (+400) and corrects stale wiki CIKs.
  Disagreements are arbitrated via the SEC submissions API — the CIK
  whose filings actually list the ticker wins — so premature
  company_tickers entries (e.g. a pending ExxonMobil holdco shell
  claiming XOM) cannot override a valid roster value.

### Fixed
- Stale CIKs on the S&P 600 page, found by pitdata's cik-consistency
  cross-check: NE (pre-Chapter-11 Noble -> 0001895262), WEN (Wendy's
  International, dead 2008 -> 0000030697), FA (-> 0001210677).

## [0.2.0] - 2026-07-12

The S&P 1500 release: adds S&P 400 (MidCap), S&P 600 (SmallCap), and the
virtual `sp1500` composite alongside the existing S&P 500. Motivated by
cross-sectional factor-model work, which needs breadth and small caps.
Design rationale in the new `DESIGN.md`.

### Added
- `index=` keyword on `get_constituents`, `get_constituents_history`,
  `info`, and `PitIndex(...)`; `--index` option on the `get`, `history`,
  `info`, and `build` CLI commands. Default stays `sp500` everywhere, so
  v0.1 call shapes are unchanged.
- **sp400** dataset, PIT coverage from 2011-11-20; **sp600** dataset, PIT
  coverage from 2021-03-26 (the S&P 600 Wikipedia page carried a wrong
  ~1000-name roster before then — no free source covers the gap).
- **sp1500** virtual composite: query-time union of the three physical
  indices with an extra `index` output column; floor = max of the member
  floors.
- New event source for sp400/sp600 (`scripts/_wikirev.py`): seed roster
  and fill events derived from monthly-sampled Wikipedia page *revisions*
  (their changes tables alone leave a 9-11% roster diff). Fill events are
  dated at the revision timestamp (PIT-safe upper bound) with revid
  provenance, guarded by per-index roster sanity bands, and committed as
  an incremental baseline under `data/*_revision_events.csv`.
- Index registry: `pitindex/_registry.py` (runtime) and
  `scripts/_indices.py` (build specs).

### Changed
- Ticker renames are now **conditional**: `ticker_renames.csv` stays one
  global file and a rename fires only in the index whose roster holds the
  old ticker (new atomic `renamed` action in the reconcile walk).
  Compensating adds that abused the old unconditional semantics moved to
  `manual_events.csv`, which gained an `index` column.
- `build_metadata.json` gained per-index sections under `indices`
  (legacy sp500 top-level keys preserved for pre-0.2 consumers).
- `StaleDataWarning` fires once per process instead of once per index.
- Weekly-refresh workflow builds all three indices and commits the
  revision-baseline drift under `data/` too.

### Fixed
- BK → BNY (2026-05-21) and SATS → ECHO (2026-06-24) ticker changes were
  untracked; the sp500 build now reconciles with **zero** synthetic
  events (was 5).

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

[Unreleased]: https://github.com/arielNacamulli/pitindex/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/arielNacamulli/pitindex/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/arielNacamulli/pitindex/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/arielNacamulli/pitindex/releases/tag/v0.1.0
