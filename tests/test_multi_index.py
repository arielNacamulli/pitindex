"""Multi-index surface tests: sp400/sp600 datasets and the sp1500 composite.

Data-quality canaries for the new indices live in test_known_dates.py;
these cover the API mechanics (index routing, composite union, floors).
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

import pitindex
from pitindex._api import _index


def test_registry_exports():
    assert pitindex.PHYSICAL_INDICES == ("sp500", "sp400", "sp600")
    assert "sp1500" in pitindex.ALL_INDICES


def test_unknown_index_raises():
    with pytest.raises(ValueError, match="Unknown index"):
        pitindex.get_constituents("2023-06-15", index="sp42")


@pytest.mark.parametrize(("index", "lo", "hi"), [("sp400", 390, 410), ("sp600", 590, 615)])
def test_new_indices_roster_bands(index: str, lo: int, hi: int):
    df = pitindex.get_constituents("2023-06-15", index=index)
    assert isinstance(df, pd.DataFrame)
    assert lo <= len(df) <= hi
    assert df["ticker"].is_unique


def test_indices_are_disjoint():
    """S&P 1500 sub-indices are mutually exclusive by construction."""
    date = "2024-06-14"
    rosters = [set(pitindex.get_constituents(date, index=k)["ticker"]) for k in pitindex.PHYSICAL_INDICES]
    assert not (rosters[0] & rosters[1])
    assert not (rosters[0] & rosters[2])
    assert not (rosters[1] & rosters[2])


def test_sp1500_is_union_with_index_column():
    date = "2024-06-14"
    df = pitindex.get_constituents(date, index="sp1500")
    assert "index" in df.columns
    assert set(df["index"].unique()) == set(pitindex.PHYSICAL_INDICES)
    total = sum(len(pitindex.get_constituents(date, index=k)) for k in pitindex.PHYSICAL_INDICES)
    assert len(df) == total
    assert 1450 <= total <= 1550


def test_sp1500_floor_is_max_of_members():
    floor = max(_index(k).seed_date for k in pitindex.PHYSICAL_INDICES)
    with pytest.raises(ValueError, match="before seed coverage"):
        pitindex.get_constituents(floor - dt.timedelta(days=1), index="sp1500")
    assert len(pitindex.get_constituents(floor, index="sp1500")) > 1400


def test_per_index_floors():
    with pytest.raises(ValueError, match="before seed coverage"):
        pitindex.get_constituents("2011-06-01", index="sp400")
    with pytest.raises(ValueError, match="before seed coverage"):
        pitindex.get_constituents("2020-06-01", index="sp600")
    # sp500 keeps its deep history
    assert len(pitindex.get_constituents("2005-06-01")) > 450


def test_info_per_index():
    for key in pitindex.PHYSICAL_INDICES:
        meta = pitindex.info(index=key)
        assert meta["index"] == key
        assert meta["current_size"] > 390
        assert "start_date" in meta
    composite = pitindex.info(index="sp1500")
    assert composite["current_size"] > 1400
    assert set(composite["members"]) == set(pitindex.PHYSICAL_INDICES)


def test_history_with_index_param():
    df = pitindex.get_constituents_history("2024-01-01", "2024-03-31", index="sp600")
    assert "as_of" in df.columns
    assert df["as_of"].nunique() >= 1


def test_pitindex_class_with_index():
    mid = pitindex.PitIndex("sp400")
    df = mid.as_of("2023-06-15")
    assert 390 <= len(df) <= 410
    assert mid.coverage_start <= dt.date(2012, 6, 1)
    broad = pitindex.PitIndex("sp1500")
    assert broad.coverage_start >= dt.date(2021, 1, 1)


def test_default_index_unchanged():
    """v0.1 call shapes still return the S&P 500."""
    df = pitindex.get_constituents("2020-06-15")
    assert len(df) > 450
    assert "index" not in df.columns
