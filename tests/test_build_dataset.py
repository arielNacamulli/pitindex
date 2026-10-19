"""Build orchestration: per-index failure isolation (unit, offline)."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from scripts import _reconcile, _wiki, _wikirev, build_dataset
from scripts._indices import SPECS

OLD_TS = "2026-09-07T06:00:00+00:00"


def _report(key: str) -> _reconcile.ReconciliationReport:
    return _reconcile.ReconciliationReport(
        start_date="2012-01-03",
        end_date="2026-10-19",
        seed_size=400,
        current_size=400,
        final_size_after_events=400,
        missing_from_walk=[f"{key.upper()}X"],
        diff_ratio=0.112,
    )


@pytest.fixture
def build_env(tmp_path, monkeypatch):
    """Redirect outputs to tmp dirs, stub the SEC fetch, seed old metadata."""
    package_data = tmp_path / "pkg"
    log_dir = tmp_path / "log"
    package_data.mkdir()
    log_dir.mkdir()
    monkeypatch.setattr(build_dataset, "PACKAGE_DATA", package_data)
    monkeypatch.setattr(build_dataset, "LOG_DIR", log_dir)
    monkeypatch.setattr(build_dataset._sec, "fetch_sec_ticker_map", lambda: {})
    old = {
        "build_timestamp_utc": OLD_TS,
        "indices": {k: {"end_date": "2026-09-07", "events_count": 1} for k in SPECS},
    }
    (package_data / "build_metadata.json").write_text(json.dumps(old), encoding="utf-8")
    return package_data, log_dir


def _stub_build_index(monkeypatch, failing: set[str]) -> list[str]:
    called: list[str] = []

    def fake(spec, **_kwargs):
        called.append(spec.key)
        if spec.key in failing:
            raise _reconcile.ReconciliationError("diff too large", report=_report(spec.key))
        return {"end_date": "2026-10-19", "events_count": 2}, _report(spec.key)

    monkeypatch.setattr(build_dataset, "build_index", fake)
    return called


def test_keep_going_builds_the_other_indices(build_env, monkeypatch):
    package_data, log_dir = build_env
    called = _stub_build_index(monkeypatch, failing={"sp400"})

    assert build_dataset.main(["--keep-going"]) == 2
    assert called == ["sp500", "sp400", "sp600"]

    meta = json.loads((package_data / "build_metadata.json").read_text(encoding="utf-8"))
    # The failed index keeps its previous section *and* its real build time…
    assert meta["indices"]["sp400"] == {
        "end_date": "2026-09-07",
        "events_count": 1,
        "build_timestamp_utc": OLD_TS,
    }
    # …while the others are refreshed.
    for key in ("sp500", "sp600"):
        assert meta["indices"][key]["end_date"] == "2026-10-19"
        assert meta["indices"][key]["build_timestamp_utc"] > OLD_TS
    assert "SP400X" in (log_dir / "build_log.md").read_text(encoding="utf-8")


def test_default_stops_at_first_failure(build_env, monkeypatch):
    package_data, log_dir = build_env
    called = _stub_build_index(monkeypatch, failing={"sp400"})

    assert build_dataset.main([]) == 2
    assert called == ["sp500", "sp400"]
    meta = json.loads((package_data / "build_metadata.json").read_text(encoding="utf-8"))
    assert meta["build_timestamp_utc"] == OLD_TS  # metadata untouched
    assert "SP400X" in (log_dir / "build_log.md").read_text(encoding="utf-8")


def test_keep_going_survives_non_reconciliation_errors(build_env, monkeypatch):
    def fake(spec, **_kwargs):
        if spec.key == "sp600":
            raise RuntimeError("roster size 12 outside sanity band")
        return {"end_date": "2026-10-19"}, _report(spec.key)

    monkeypatch.setattr(build_dataset, "build_index", fake)
    assert build_dataset.main(["--keep-going"]) == 2
    with pytest.raises(RuntimeError, match="sanity band"):
        build_dataset.main([])


@pytest.mark.parametrize("reconciles", [True, False])
def test_revision_baseline_is_saved_only_after_reconciliation(build_env, monkeypatch, reconciles):
    current = [
        _wiki.Constituent(
            ticker=f"T{i}", name=f"T{i}", cik=None, gics_sector=None, gics_sub_industry=None, date_added=None
        )
        for i in range(400)
    ]
    sample = _wikirev.RevisionSample(revid=1, timestamp="2026-10-18T00:00:00Z", roster=frozenset())
    saved: list[tuple] = []

    monkeypatch.setattr(build_dataset._wiki, "fetch_html", lambda url: "")
    monkeypatch.setattr(build_dataset._wiki, "parse_current_constituents", lambda html: current)
    monkeypatch.setattr(build_dataset._wiki, "parse_changes", lambda *htmls, **_kw: [])
    monkeypatch.setattr(
        build_dataset._wikirev,
        "build_revision_events",
        lambda **_kw: (dt.date(2011, 11, 20), frozenset(), [], sample),
    )
    monkeypatch.setattr(build_dataset._wikirev, "save_baseline", lambda *args: saved.append(args))

    def fake_reconcile(**_kw):
        if not reconciles:
            raise _reconcile.ReconciliationError("diff too large", report=_report("sp400"))
        return [], _report("sp400")

    monkeypatch.setattr(build_dataset._reconcile, "reconcile", fake_reconcile)

    def run():
        return build_dataset.build_index(SPECS["sp400"], today=dt.date(2026, 10, 19), max_diff_ratio=0.05)

    if reconciles:
        run()
        assert len(saved) == 1
        assert saved[0][3] is sample
    else:
        with pytest.raises(_reconcile.ReconciliationError):
            run()
        assert saved == []


def test_fill_undoing_a_roster_flip_is_kept():
    """WBS/SUI, sp400 2026: the roster page reverted a change, then restored it."""

    def ev(date, action, ticker, origin=None):
        return _wiki.ChangeEvent(date, action, ticker, None, None, origin=origin)

    precise = [ev("2026-08-20", "removed", "WBS")]
    fills = [
        ev("2026-08-24", "removed", "WBS", "fill"),  # echo of the precise event: dropped
        ev("2026-09-06", "added", "WBS", "fill"),  # the flip
        ev("2026-10-12", "removed", "WBS", "fill"),  # undoes the flip: must survive
    ]
    kept = build_dataset._dedupe_fill_events(fills, precise)
    assert [(e.date, e.action) for e in kept] == [("2026-09-06", "added"), ("2026-10-12", "removed")]
