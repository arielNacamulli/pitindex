# Contributing

Contributions are welcome — especially **adding new ticker renames** when
an S&P 500 constituent changes its symbol (Wikipedia treats those as
no-ops because the company itself didn't enter or leave the index, so
the curated CSV is the only place to capture them).

## Development setup

```bash
git clone https://github.com/arielNacamulli/pitindex.git
cd pitindex

python -m venv .venv
source .venv/bin/activate
pip install -e ".[build,dev]"

pre-commit install
```

## Running the gates locally

```bash
ruff check pitindex scripts tests
ruff format --check pitindex scripts tests
mypy pitindex
pytest -v
pytest --cov=pitindex --cov-report=term-missing
```

`pre-commit run --all-files` runs the same lint/format/mypy gates as CI.

## Rebuilding the dataset locally

```bash
python -m scripts.build_dataset -v
```

This downloads the upstream Wikipedia HTML and the `fja05680/sp500`
seed CSV, applies the curated overrides under `data/`, runs the
reconciliation gate, and writes the four files in `pitindex/data/`. If
the build fails (`diff_ratio > 5%`) inspect `data/build_log.md` for the
specific deltas — typically one of the following pull requests fixes it.

## Common contributions

### New ticker rename (most frequent)

Append a row to [`data/ticker_renames.csv`](data/ticker_renames.csv):

```csv
date,old_ticker,new_ticker,reason
2026-01-26,MMC,MRSH,Marsh McLennan ticker change.
```

Re-run the build and commit the regenerated files in `pitindex/data/`.

### Real index event missed by both upstreams

If a true add/remove event is absent from both the seed and Wikipedia
"Selected changes", append a row to
[`data/manual_events.csv`](data/manual_events.csv) instead:

```csv
date,action,ticker,name,reason
2008-09-15,removed,LEH,Lehman Brothers Holdings,S&P 500 removal post-bankruptcy.
```

### Bug fix or feature

1. Branch from `master`.
2. Add or update tests (`tests/test_api.py` for API behaviour,
   `tests/test_known_dates.py` for membership snapshot regressions).
3. Ensure all gates pass.
4. Open a PR with a clear description of the change and why.

## Reporting bugs

Open an issue and include:
- Python version and OS
- Full traceback
- Output of `python -c "import pitindex; print(pitindex.info())"`
- Minimal reproduction steps

## License

By contributing you agree that your contributions will be licensed under
the [MIT License](LICENSE).
