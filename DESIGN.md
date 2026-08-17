# DESIGN — pitindex

Cumulative design rationale. Each section records the decision, the why,
the alternatives discarded, and open caveats. Update this file whenever a
structural decision lands.

## 1. Scope: which indices (2026-07-12)

**Decision:** extend from S&P 500-only to the S&P 1500 family:
`sp500`, `sp400` (MidCap), `sp600` (SmallCap), plus a virtual composite
`sp1500`.

**Why:** the downstream use case is a cross-sectional factor model
(toraniko-style). That needs breadth and small-cap names, and — the
binding constraint of this project — point-in-time membership from
*free* sources. The S&P 1500 components are the only broad-US family
whose membership changes are publicly tracked (Wikipedia) at usable
fidelity.

**Alternatives discarded:**
- *Russell 3000*: membership is FTSE Russell proprietary; the only free
  path is forward-collection of iShares IWV daily holdings (no history).
- *Wilshire 5000*: constituents are not published at all.
- *Rule-based top-N universe from pitedgar market caps*: closest to what
  practitioners actually use, but requires prices for every US listed
  security (free-data graveyard for delisted small caps). Deferred until
  the S&P 1500 pipeline proves itself.

## 2. Per-index coverage floors (2026-07-12)

**Decision:** heterogeneous floors, dictated by the sources:

| Index | Floor (seed revision) | Binding source |
|---|---|---|
| sp500 | 2005-01-03 | fja05680/sp500 seed dataset |
| sp400 | 2011-11-20 | Wikipedia page usable from late 2011 |
| sp600 | 2021-03-26 | Wikipedia page carried the wrong roster (~1000 names, likely S&P 1000) until 2021-03 |
| sp1500 | 2021-03-26 | max of the three floors |

**Why:** measured empirically (2026-07-12) by sampling quarterly page
revisions and parsing the constituents table:
- "List of S&P 400 companies" created 2010-12-31; parseable roster of
  ~400 names from the 2011-12-14 revision onward.
- "List of S&P 600 companies" created 2018-08-27, but its constituents
  table held 993–1057 rows until early 2021 — the S&P 600 has ~601-603
  members, so pre-2021 revisions are unusable. First in-band revision:
  2021-03-26 (n=600).

**Caveat:** no free source exists for pre-2021 S&P 600 membership. If a
deeper 600 history ever matters, candidates are Wayback captures of
iShares IJR holdings CSVs (spotty) or paid data (CRSP/Compustat).

## 3. Event sources for sp400/sp600: changes table + revision diffs (2026-07-12)

**Decision:** for the new indices, the event log is the union of:
1. Wikipedia "changes" table events (precise effective dates), and
2. **fill events** derived from diffs between monthly-sampled page
   revisions (dated at the revision timestamp),
with fills suppressed when a changes-table event for the same
(ticker, action) exists within the sampling window (±slack).

**Why:** measured completeness of the changes tables alone is bad:
walking the 2021-03 roster through the changes table to today leaves a
9-11% diff vs the current roster (68-79% from older seeds). Roughly half
the residual is ticker renames; the rest is genuinely missing events —
mostly removals. Revision diffs recover them from the page history
itself, the same "snapshot diff" technique `_seed.py` applies to the
fja05680 dataset for the sp500.

**PIT semantics of fill events:** their `date` is the revision
timestamp — the first date the information was demonstrably public on
the source — which is an *upper bound* on the effective date (lag ≤ one
sampling interval). Conservative in the no-look-ahead direction, so safe
for backtests. The `reason` field carries revid provenance.

**Alternatives discarded:**
- *Changes table only*: fails reconciliation (see numbers above).
- *Revision diffs only*: throws away the precise effective dates the
  changes table does have.
- *Per-revision (not monthly) sampling*: more API load and more exposure
  to transient vandalism; monthly + sanity band + final reconciliation
  gate is enough.

**Mechanics:** revision-derived events are bootstrapped once and
committed as `data/{index}_revision_events.csv` plus a state JSON
(`last_revid`, `last_rev_timestamp`, `last_roster`). Weekly builds only
extend the tail from `last_rev_timestamp`, so CI stays fast and the
historical baseline is frozen and reviewable (same philosophy as
pitprices' frozen WIKI baseline).

**Sanity band:** parsed rosters must fall inside a per-index band
(sp500 490-515, sp400 390-410, sp600 590-615); out-of-band samples are
skipped and logged. This is what protects against the pre-2021 sp600
S&P-1000 contamination recurring.

## 3b. Fill no-ops are benign, not anomalies (2026-07-12)

**Decision:** a fill event that lands on already-consistent state (add on
a present ticker, remove on an absent one) is counted as `fill_noops` in
the reconciliation report and excluded from `diff_ratio`.

**Why:** the sp400 page's constituents table historically lagged its own
changes table by *months* (e.g. DPZ added effective 2013-05-30, table
updated 2013-10-30). A fill is an upper-bound-dated confirmation of
state, so redundancy with a precise event is the expected case, not a
defect. Without this, the first sp400 build tripped the gate at 97.5%
with 305 benign no-ops counted as anomalies. Precise-event conflicts
still count — only `origin="fill"` events get the benign treatment. The
120-day dedupe window is kept to reduce event-log noise and to protect
against announcement-before-effective inversions.

## 3c. Ticker-shape validation on changes-table rows (2026-07-12)

**Decision:** `parse_changes` drops entries whose ticker cell does not
match `^[A-Z0-9]{1,6}(\.[A-Z])?$`, logging the count.

**Why:** the sp400 changes table switched column layout around mid-2019;
older rows carry the *company name* where the parser expects the ticker
("PS BUSINESS PARKS", "UA/UAA", …) — 66 garbage events that corrupted
the walk. Dropped rows are recovered by revision-diff fills, at the cost
of date precision (month-level) for pre-2019 sp400 events. Name-shaped
strings that happen to look like tickers (HARSCO, WEBMD) survive the
filter but die as no-op invalid removes in the walk — inflating
diff_ratio slightly (~3.5% residual on sp400), which we accept.

## 3d. Changes tables live on their own articles (2026-08-17)

**Decision:** each `IndexSpec` carries a `changes_url` alongside
`wiki_url`. The build fetches both pages and `parse_changes` takes any
number of HTML documents, merging their events and deduplicating on
(date, action, ticker). Table location falls back from the stable id to
a header signature (changes: date + added + removed; constituents:
symbol/ticker + security/company, rejecting anything mentioning
"removed").

**Why:** on 2026-08-11 Wikipedia editors moved the "Selected changes"
tables out of the three "List of S&P NNN companies" articles into new
"Historical components of the S&P NNN" articles (edit summary: *move to
[[Historical components of the S&P 600]]*, page shrinking 296,681 →
117,885 bytes). The 2026-08-17 weekly refresh aborted on the first index
with `Could not find table id='changes'`. Reading both pages rather than
just the new one means a revert of the split — plausible, the articles
are edited by hand — needs no code change; the dedupe makes the overlap
harmless. The header-signature fallback covers the narrower case of an
id being dropped in place, which is how these anchors usually break.

Upside of the split: the new articles are deeper than the sections they
replaced (sp500 back to 1976-07-01, sp400 to 2012-01, sp600 to 2019-12),
so the precise-dated event source now extends past our coverage floors.

## 4. Renames become conditional events (2026-07-12)

**Decision:** `data/ticker_renames.csv` stays a single global file; a
rename is applied to an index only if the old ticker is in that index's
roster on the rename date (`renamed` pseudo-action handled atomically in
the reconcile walk). Rename entries that were actually *compensating
adds* for seed omissions (e.g. PX→LIN where the seed recorded the PX
removal but not the LIN add) move to `data/manual_events.csv`, which
gains an `index` column.

**Why:** the old semantics (unconditional removed(old)+added(new) pair,
validator drops the half that doesn't apply) worked when there was one
index; with three, an unconditional add would inject phantom members
into indices the company never belonged to. Conditional application
makes the global file safe: S&P indices are mutually exclusive, so each
rename fires in exactly the index that holds the old ticker.

**Regression gate:** the rebuilt sp500 dataset must be semantically
identical to the pre-refactor one (diff of `sp500_changes.csv` /
`sp500_seed.csv` / roster spot checks); any discrepancy must be
explained and fixed via `manual_events.csv` before merging.

## 5. Composite sp1500 is virtual (2026-07-12)

**Decision:** `index="sp1500"` is computed at query time as the union of
the three physical indices (extra `index` column in the output telling
which sub-index each ticker belongs to). No sp1500 data files.

**Why:** the three event logs are the source of truth; materializing a
fourth would triple-count maintenance. Floor = max of floors; querying
earlier raises, same as any pre-floor query.

## 6. Ready-made alternatives investigated and rejected (2026-07-12)

**Question:** does a pre-built dataset exist so we don't have to derive
sp400/sp600 (or Russell) membership ourselves?

**Answer: no.** Searched GitHub, Kaggle and the quant blogosphere:
- `fja05680/sp500`, `hanshof/sp500_constituents` — S&P 500 only.
- `yfiua/index-constituents` — no S&P 400/600, and history starts 2023.
- Russell 3000 historical membership: FTSE-proprietary; only paid vendors
  (Algoseek et al.) or forward-collection of iShares IWV daily holdings.
- Wilshire 5000: constituents not published at all.

**Identified for v0.3 — SEC fund filings as an ETF-proxy source:**
N-PORT filings (quarterly full holdings, public since mid-2019) exist on
EDGAR for iShares IJR (S&P 600), IJH (S&P 400), and IWV (Russell 3000);
N-Q filings extend the same idea back to ~2004-2019 in messier formats.
Verified 2026-07-12: 1,639 N-PORT hits for "iShares Core S&P Small-Cap",
866 for "iShares Russell 3000". This is the only credible free path to
(a) backfilling sp600 into 2019-2021 and (b) any Russell index — at
quarterly granularity, using ETF holdings as a membership proxy. It also
plays to the existing pitedgar EDGAR tooling. Deliberately *not* done in
v0.2: quarterly holdings complement rather than replace the event-dated
Wikipedia pipeline, and N-Q parsing is a project of its own.

## 7. API compatibility (2026-07-12)

**Decision:** every public entry point grows an `index="sp500"` keyword
with the old default, so v0.1 callers (pitprices `_integrations.py`
included) keep working unchanged. Data files are renamed per-index
(`sp500_*.csv` pattern extended to `sp400_*`, `sp600_*`);
`build_metadata.json` becomes `{"build_timestamp_utc", "indices": {key:
{...}}}` with legacy sp500 top-level keys preserved.
