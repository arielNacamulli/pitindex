# pitindex

Point-in-time constituents of major equity indices, derived from free public
sources, shipped as a small Python package.

The **S&P 1500 family** is supported, with per-index PIT coverage dictated
by what the free sources can honestly reconstruct:

| Index | Key | Coverage from |
|---|---|---|
| S&P 500 | `sp500` (default) | **2005-01-03** |
| S&P 400 MidCap | `sp400` | **2011-11-20** |
| S&P 600 SmallCap | `sp600` | **2021-03-26** |
| S&P 1500 (virtual composite) | `sp1500` | **2021-03-26** (max of the three) |

```python
import pitindex

# Membership snapshot at a point in time:
df = pitindex.get_constituents("2020-12-22")
# -> DataFrame[ticker, name, cik, gics_sector, gics_sub_industry]

# Other indices of the family:
mid = pitindex.get_constituents("2023-06-30", index="sp400")
broad = pitindex.get_constituents("2023-06-30", index="sp1500")
# sp1500 adds an `index` column telling which sub-index each ticker is in.

# Sparse history: one snapshot per change date in [start, end]:
hist = pitindex.get_constituents_history("2020-01-01", "2020-12-31")

# Build metadata (sources, sizes, last refresh):
pitindex.info()                # sp500
pitindex.info(index="sp600")

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

### `get_constituents(as_of, index="sp500")`

Returns the index membership at the end of the given date.

- `as_of` accepts `datetime.date`, `datetime.datetime`, or an ISO-format
  string `"YYYY-MM-DD"`.
- `index` is one of `sp500`, `sp400`, `sp600`, `sp1500`.
- Output columns: `ticker, name, cik, gics_sector, gics_sub_industry`
  (plus `index` for the `sp1500` composite).
- `cik` and the GICS columns are populated for tickers that are still
  index members today; for delisted constituents only what was preserved
  upstream is returned (typically the company name).
- Weekend / holiday dates simply return the last preceding event-driven
  membership state — no calendar interpolation is required.
- The `as_of` value is also exposed via `df.attrs["as_of"]`.

### `get_constituents_history(start, end, index="sp500")`

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

The build pipeline (`python -m scripts.build_dataset`) combines free
public sources, in order of trust. See `DESIGN.md` for the full
rationale behind each choice.

**S&P 500:**

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

**S&P 400 / S&P 600** (no fja05680 equivalent exists):

1. **Wikipedia "changes" table** — the precise-dated event source, but
   measurably incomplete for these pages (mostly missing removals).
2. **Page revision history** — the seed roster comes from the oldest
   reliable page revision, and *fill events* are derived from diffs
   between monthly-sampled revisions (the same snapshot-diff technique,
   applied to Wikipedia's own history). Fill events are dated at the
   revision timestamp — the first date the information was demonstrably
   public — and carry revid provenance in their `reason` field. A
   per-index sanity band on parsed roster sizes rejects corrupt
   revisions (the pre-2021 S&P 600 page carried ~1000 names). The
   derived baseline is committed under `data/{key}_revision_events.csv`
   and only its tail is extended on weekly rebuilds.

**All indices — curated overrides**, two CSVs in `data/` that close gaps
no upstream source captures:

- `data/ticker_renames.csv`: index members whose **ticker changed**
  (FB → META, BBT → TFC, BK → BNY, …). The file is global: a rename is
  applied only in the index whose roster holds the old ticker on the
  rename date, and no-ops silently elsewhere.
- `data/manual_events.csv`: explicit `added`/`removed` events (with an
  `index` column) that correct known errors or omissions in the
  upstream data (e.g. the period-correct `LEH` ticker for Lehman
  Brothers, where the seed uses the post-bankruptcy notation `LEHMQ`
  throughout).

Every build runs a per-index **reconciliation gate**: the seed roster is
walked forward through the merged event log and compared against the
current Wikipedia roster. If the resulting diff exceeds 5% of the
current roster, the build fails loud rather than shipping
silently-corrupt data. The full reconciliation report lands in
`data/build_log.md`.

## Limitations

- **Heterogeneous coverage floors.** sp500 from 2005-01-03, sp400 from
  2011-11-20, sp600 only from 2021-03-26 — before that date the S&P 600
  Wikipedia page carried a wrong (~1000-name) roster and no free source
  for its membership exists. The `sp1500` composite starts at the max of
  the floors. Pre-floor queries raise instead of extrapolating.
- **Fill-event dates are upper bounds.** For sp400/sp600, events
  recovered from revision diffs are dated at the revision timestamp (lag
  ≤ ~1 month vs the true effective date). Precisely-dated changes-table
  events are preferred wherever they exist. This is conservative in the
  no-look-ahead direction.
- **Tickers for delisted constituents may be the upstream-encoded form.**
  The seed dataset uses post-event tickers for some delisted companies
  (`LEHMQ`, `WAMUQ`, `ABKFQ`, …). We patch the most prominent ones via
  `ticker_renames.csv` but coverage is best-effort. PRs welcome.
- **No CIK for sp400 members.** The S&P 400 Wikipedia page does not
  publish a CIK column (the 500 and 600 pages do).
- **No index weights.** Weights require contemporaneous market-cap and
  float data that no truly-free source provides at PIT granularity. If
  you need weights, derive them from the constituent list plus your
  preferred price/shares-outstanding source.
- **No corporate-action provenance.** The change events carry a `reason`
  field where one was captured by the source, but the library is not a
  corporate-actions database.

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
