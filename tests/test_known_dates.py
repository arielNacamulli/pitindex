"""Snapshot tests on dates with well-documented index changes.

Each parameterized case asserts that a specific ticker is/isn't in the
roster on a specific date. These are the canary tests that catch
regressions in the build pipeline (parser, reconciliation, renames).

Sources for the change dates: S&P Dow Jones Indices press releases and
the Wikipedia "Selected changes to the list of S&P 500 components"
table, cross-checked against major-press coverage.
"""
from __future__ import annotations

import pytest

import pitindex

# (description, date, ticker, expected_in_roster)
CASES: list[tuple[str, str, str, bool]] = [
    # Tesla added at the close of trading on 2020-12-21
    ("Tesla in by 2020-12-22", "2020-12-22", "TSLA", True),
    ("Tesla NOT in on 2020-12-18", "2020-12-18", "TSLA", False),

    # Facebook (FB) added 2013-12-23
    ("FB in by 2013-12-24", "2013-12-24", "FB", True),
    ("FB NOT in 2013-12-20", "2013-12-20", "FB", False),

    # FB -> META rename effective 2022-06-09
    ("META present after rename 2022-07-01", "2022-07-01", "META", True),
    ("FB absent after rename 2022-07-01", "2022-07-01", "FB", False),
    ("FB still present 2022-06-01 (before rename)", "2022-06-01", "FB", True),
    ("META not yet present 2022-06-01", "2022-06-01", "META", False),

    # Lehman Brothers (LEH) exited around 2008-09-15 bankruptcy
    ("LEH still present early 2008", "2008-06-30", "LEH", True),
    ("LEH gone by end of 2008", "2008-12-31", "LEH", False),

    # GE was removed from the DJIA on 2018-06-26 (replaced by WBA there) but
    # has remained continuously in the S&P 500. After the 2024 GE conglomerate
    # spin-off the ticker now represents GE Aerospace.
    ("GE present pre-2018-06-26 (S&P 500)", "2018-06-25", "GE", True),
    ("GE present post-2018-06-26 (S&P 500)", "2018-07-15", "GE", True),
    ("GE present today", "2025-12-01", "GE", True),

    # United Technologies -> Raytheon Technologies merger 2020-04-03
    ("UTX present pre-merger", "2020-03-15", "UTX", True),
    ("RTX present post-merger", "2020-05-01", "RTX", True),
    ("UTX absent post-merger", "2020-05-01", "UTX", False),

    # Apple has been a member throughout the entire coverage window
    ("AAPL present 2005-06-15", "2005-06-15", "AAPL", True),
    ("AAPL present 2015-06-15", "2015-06-15", "AAPL", True),
    ("AAPL present today-ish", "2025-12-01", "AAPL", True),
]


@pytest.mark.parametrize("desc,date,ticker,expected", CASES, ids=[c[0] for c in CASES])
def test_known_membership(desc: str, date: str, ticker: str, expected: bool):
    df = pitindex.get_constituents(date)
    assert (ticker in df["ticker"].values) is expected, (
        f"{desc}: expected {ticker} {'in' if expected else 'absent'} on {date}; "
        f"roster size={len(df)}"
    )


def test_roster_size_stays_in_band():
    """The S&P 500 carries ~500-505 members at any point in our window."""
    for date in ("2008-01-15", "2010-06-15", "2015-06-15", "2020-06-15", "2025-06-15"):
        df = pitindex.get_constituents(date)
        assert 495 <= len(df) <= 510, f"Roster size {len(df)} on {date} is outside expected band"
