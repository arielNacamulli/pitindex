# pitindex

Point-in-time constituents of major equity indices, derived from free public
sources, shipped as a small Python package.

The first index supported is the **S&P 500**, with PIT coverage from
**2005-01-03 through today**.

```python
import pitindex

# Membership snapshot at a point in time:
df = pitindex.get_constituents("2020-12-22")
# -> DataFrame[ticker, name, cik, gics_sector, gics_sub_industry]

# Sparse history: one snapshot per change date in [start, end]:
hist = pitindex.get_constituents_history("2020-01-01", "2020-12-31")

# Build metadata (sources, sizes, last refresh):
pitindex.info()

# Refresh the local cache from upstream sources (requires the [build] extra):
pitindex.update()
```

## Install

```bash
pip install pitindex            # runtime only
pip install "pitindex[build]"   # adds the build pipeline (used by update())
```

The package ships with a pre-built dataset, so the runtime has no network
dependencies. `pitindex.update()` is an optional escape hatch for users who
need data fresher than the most recent release.

## API

### `get_constituents(as_of)`

Returns the index membership at the end of the given date.

- `as_of` accepts `datetime.date`, `datetime.datetime`, or an ISO-format
  string `"YYYY-MM-DD"`.
- Output columns: `ticker, name, cik, gics_sector, gics_sub_industry`.
- `cik` and the GICS columns are populated for tickers that are still
  index members today; for delisted constituents only what was preserved
  upstream is returned (typically the company name).
- Weekend / holiday dates simply return the last preceding event-driven
  membership state — no calendar interpolation is required.
- The `as_of` value is also exposed via `df.attrs["as_of"]`.

### `get_constituents_history(start, end)`

Returns one snapshot per **change date** in `[start, end]` plus a snapshot
at `start`. The output adds an `as_of` column to the schema above.

This is intentionally sparse to avoid the huge cartesian product of a
fully-densified daily history. To obtain a per-trading-day view, iterate
`get_constituents` over your trading calendar.

### `update(force=False)`

Re-runs the build pipeline against current upstream sources and writes
the result into `~/.cache/pitindex/`, taking precedence over the bundled
data on subsequent calls. Pass `force=True` to bypass the 24-hour cache
freshness check.

### `info()`

Returns a `dict` of metadata about the loaded dataset: build timestamp,
source URLs, roster sizes, reconciliation diff ratio, plus
`data_age_days`, `stale_threshold_days`, and `is_stale`.

## Staying fresh

The package ships a snapshot of the dataset built at release time. The
upstream Wikipedia roster does change (a few times a year), so the
library has two complementary mechanisms to keep you current:

- **Weekly cron in this repo.** A GitHub Actions workflow rebuilds the
  data every Monday morning UTC and commits any drift back to `main`.
  Releases get cut from those refreshed commits, so a normal
  `pip install -U pitindex` pulls in the latest weekly snapshot. This is
  free CI on public repositories.
- **Runtime staleness reminder.** When the loaded dataset is older than
  the freshness threshold (default 14 days), the first call into the
  library emits a `pitindex.StaleDataWarning` telling you to upgrade or
  call `update()`. Configure with:

  ```bash
  export PITINDEX_STALE_DAYS=30   # custom threshold
  export PITINDEX_STALE_DAYS=0    # opt out entirely
  ```

  Or programmatically:

  ```python
  import warnings, pitindex
  warnings.filterwarnings("ignore", category=pitindex.StaleDataWarning)
  ```

Together they cover the two failure modes: the maintainer-side ("did
the cron run?") and the user-side ("did the user remember to upgrade?").

## How the data is built

The build pipeline (`python -m scripts.build_dataset`) combines three
free public sources, in order of trust:

1. **Seed snapshot dataset** — the community-maintained
   [`fja05680/sp500`](https://github.com/fja05680/sp500) repository
   provides daily-resolution membership snapshots from 1996 through
   roughly 2019. We compute event diffs between consecutive snapshots
   to obtain the bulk of the historical event log, which is more
   complete than any single curated source. The seed is the *primary*
   source for everything within its coverage window.

2. **Wikipedia "List of S&P 500 companies"** — used for (a) the current
   roster (with GICS sector and CIK), and (b) the change events for the
   period **after** the seed dataset's coverage ends. Wikipedia's
   "Selected changes" table is *not* exhaustive (it omits many
   2008-financial-crisis exits, for example), so we deliberately defer
   to the seed where they overlap.

3. **Curated overrides** — two CSVs in `data/` close gaps that neither
   upstream source captures:
   - `data/ticker_renames.csv`: index members whose **ticker changed**
     (FB → META, BBT → TFC, UTX → RTX, …). Wikipedia treats those as
     no-ops because the *company* did not enter or leave the index;
     the seed sometimes records only the removal of the old ticker.
   - `data/manual_events.csv`: explicit `added`/`removed` events that
     correct known errors or omissions in the upstream data (e.g. the
     period-correct `LEH` ticker for Lehman Brothers, where the seed
     uses the post-bankruptcy notation `LEHMQ` throughout).

Every build runs a **reconciliation gate**: the seed roster is walked
forward through the merged event log and compared against the current
Wikipedia roster. If the resulting diff exceeds 5% of the current
roster, the build fails loud rather than shipping silently-corrupt
data. The full reconciliation report lands in `data/build_log.md`.

## Limitations

- **Tickers for delisted constituents may be the upstream-encoded form.**
  The seed dataset uses post-event tickers for some delisted companies
  (`LEHMQ`, `WAMUQ`, `ABKFQ`, …). We patch the most prominent ones via
  `ticker_renames.csv` but coverage is best-effort. PRs welcome.
- **No index weights.** Weights require contemporaneous market-cap and
  float data that no truly-free source provides at PIT granularity. If
  you need weights, derive them from the constituent list plus your
  preferred price/shares-outstanding source.
- **No corporate-action provenance.** The change events carry a `reason`
  field where one was captured by the source, but the library is not a
  corporate-actions database.
- **2005-01-03 is the earliest supported date.** Before that, the seed
  dataset's reliability and our coverage of ticker renames degrade.

## Contributing

The most common contribution is **adding a new ticker rename** when an
S&P 500 member changes its ticker. Append a row to
`data/ticker_renames.csv`:

```csv
date,old_ticker,new_ticker,reason
2024-09-12,BLL,BALL,Ball Corporation ticker change.
```

Then re-run `python -m scripts.build_dataset` and commit the regenerated
files in `pitindex/data/`. The same applies to `data/manual_events.csv`
for genuine add/remove events that neither upstream captures.

## License

MIT — see [`LICENSE`](LICENSE).

The bundled data is derived from public sources:
[Wikipedia](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies)
(CC BY-SA 4.0) and the
[`fja05680/sp500`](https://github.com/fja05680/sp500) dataset
(MIT). Factual data (membership, ticker symbols, dates) is not itself
copyrightable; the curation in this repo is MIT.
