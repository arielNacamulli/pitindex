"""API-shape tests. These exercise the public surface, not data quality."""
from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

import pitindex


def test_get_constituents_returns_dataframe():
    df = pitindex.get_constituents("2020-06-15")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["ticker", "name", "cik", "gics_sector", "gics_sub_industry"]
    assert len(df) > 450  # S&P 500 always has ~500 members
    assert df["ticker"].is_unique


def test_get_constituents_accepts_date_object():
    df = pitindex.get_constituents(dt.date(2020, 6, 15))
    assert len(df) > 450


def test_get_constituents_accepts_datetime_object():
    df = pitindex.get_constituents(dt.datetime(2020, 6, 15, 12, 0, 0))
    assert len(df) > 450


def test_get_constituents_rejects_unsupported_type():
    with pytest.raises(TypeError):
        pitindex.get_constituents(123)  # type: ignore[arg-type]


def test_get_constituents_rejects_future_dates():
    far_future = dt.date.today() + dt.timedelta(days=365)
    with pytest.raises(ValueError, match="future"):
        pitindex.get_constituents(far_future)


def test_get_constituents_rejects_pre_seed_dates():
    info = pitindex.info()
    pre_seed = dt.date.fromisoformat(info["start_date"]) - dt.timedelta(days=30)
    with pytest.raises(ValueError, match="before seed coverage"):
        pitindex.get_constituents(pre_seed)


def test_history_returns_columns():
    df = pitindex.get_constituents_history("2020-12-01", "2020-12-31")
    assert "as_of" in df.columns
    assert {"ticker", "name", "cik"}.issubset(df.columns)
    # At least one snapshot in this window (TSLA add on 2020-12-21)
    assert df["as_of"].nunique() >= 1


def test_history_rejects_inverted_window():
    with pytest.raises(ValueError):
        pitindex.get_constituents_history("2020-12-31", "2020-12-01")


def test_info_has_required_keys():
    info = pitindex.info()
    for key in ("build_timestamp_utc", "current_size", "events_count", "start_date"):
        assert key in info


def test_info_reports_staleness_fields():
    info = pitindex.info()
    assert "data_age_days" in info
    assert "stale_threshold_days" in info
    assert "is_stale" in info
    # data_age_days should be int (or None on a malformed metadata file)
    assert info["data_age_days"] is None or isinstance(info["data_age_days"], int)


def test_stale_data_warning_class_is_exported():
    assert issubclass(pitindex.StaleDataWarning, UserWarning)


def test_attrs_carry_as_of():
    df = pitindex.get_constituents("2020-06-15")
    assert df.attrs.get("as_of") == "2020-06-15"
