"""Tests for the :class:`pitindex.PitIndex` wrapper."""

from __future__ import annotations

import datetime as dt

import pandas as pd

import pitindex


def test_class_as_of_matches_function():
    idx = pitindex.PitIndex()
    df_class = idx.as_of("2020-12-22")
    df_func = pitindex.get_constituents("2020-12-22")
    pd.testing.assert_frame_equal(df_class, df_func)


def test_class_history_matches_function():
    idx = pitindex.PitIndex()
    df_class = idx.history("2020-01-01", "2020-12-31")
    df_func = pitindex.get_constituents_history("2020-01-01", "2020-12-31")
    pd.testing.assert_frame_equal(df_class, df_func)


def test_class_contains():
    idx = pitindex.PitIndex()
    assert idx.contains("AAPL", "2020-06-15") is True
    assert idx.contains("aapl", "2020-06-15") is True  # case-insensitive
    assert idx.contains("ZZZZ_NOT_REAL", "2020-06-15") is False
    # Tesla added 2020-12-21
    assert idx.contains("TSLA", "2020-12-22") is True
    assert idx.contains("TSLA", "2020-12-18") is False


def test_class_info_matches_function():
    idx = pitindex.PitIndex()
    assert idx.info() == pitindex.info()


def test_class_coverage_bounds_are_dates():
    idx = pitindex.PitIndex()
    assert isinstance(idx.coverage_start, dt.date)
    assert isinstance(idx.coverage_end, dt.date)
    assert idx.coverage_start <= idx.coverage_end
