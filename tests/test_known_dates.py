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


@pytest.mark.parametrize(("desc", "date", "ticker", "expected"), CASES, ids=[c[0] for c in CASES])
def test_known_membership(desc: str, date: str, ticker: str, expected: bool):
    df = pitindex.get_constituents(date)
    assert (ticker in df["ticker"].values) is expected, (
        f"{desc}: expected {ticker} {'in' if expected else 'absent'} on {date}; roster size={len(df)}"
    )


def test_roster_size_stays_in_band():
    """The S&P 500 carries ~500-505 members at any point in our window."""
    for date in ("2008-01-15", "2010-06-15", "2015-06-15", "2020-06-15", "2025-06-15"):
        df = pitindex.get_constituents(date)
        assert 495 <= len(df) <= 510, f"Roster size {len(df)} on {date} is outside expected band"


# (description, index, date, ticker, expected_in_roster)
# Sources: S&P DJI press releases cross-checked against company IR/SEC filings.
MULTI_INDEX_CASES: list[tuple[str, str, str, str, bool]] = [
    # Wright Express: in the S&P 400 from 2012-03-26; WXS -> WEX ticker
    # change effective 2013-04-15.
    ("WXS in sp400 mid-2012", "sp400", "2012-06-01", "WXS", True),
    ("WEX in sp400 by 2014", "sp400", "2014-01-02", "WEX", True),
    ("WXS gone from sp400 by 2014", "sp400", "2014-01-02", "WXS", False),
    # Monster Beverage: HANS -> MNST rename 2012-01-05, then promoted to
    # the S&P 500 effective 2012-06-28 (replaced Sara Lee).
    ("MNST in sp400 early 2012", "sp400", "2012-03-01", "MNST", True),
    ("MNST out of sp400 after promotion", "sp400", "2012-07-02", "MNST", False),
    ("MNST in sp500 after promotion", "sp500", "2012-07-02", "MNST", True),
    # HollyFrontier -> HF Sinclair (HFC -> DINO), 2022-03.
    ("DINO in sp400 2023", "sp400", "2023-01-03", "DINO", True),
    ("HFC gone from sp400 2023", "sp400", "2023-01-03", "HFC", False),
    # HTA acquired Healthcare Realty (closed 2022-07-20); combined company
    # kept the HR ticker.
    ("HR in sp400 after merger", "sp400", "2022-09-01", "HR", True),
    ("HTA gone from sp400 after merger", "sp400", "2022-09-01", "HTA", False),
    # Super Micro: joined the S&P 400 2022-12-22, promoted to the S&P 500
    # effective 2024-03-18 (never in the S&P 600).
    ("SMCI in sp400 2023", "sp400", "2023-06-01", "SMCI", True),
    ("SMCI out of sp400 after promotion", "sp400", "2024-06-03", "SMCI", False),
    ("SMCI in sp500 after promotion", "sp500", "2024-06-03", "SMCI", True),
    # InterDigital moved S&P 400 -> S&P 600 effective 2021-04-12.
    ("IDCC in sp600 after move", "sp600", "2021-05-03", "IDCC", True),
    # SolarEdge demoted S&P 500 -> S&P 600 effective 2023-12-18.
    ("SEDG in sp500 before demotion", "sp500", "2023-11-01", "SEDG", True),
    ("SEDG in sp600 after demotion", "sp600", "2024-01-15", "SEDG", True),
    ("SEDG out of sp500 after demotion", "sp500", "2024-01-15", "SEDG", False),
]


@pytest.mark.parametrize(
    ("desc", "index", "date", "ticker", "expected"),
    MULTI_INDEX_CASES,
    ids=[c[0] for c in MULTI_INDEX_CASES],
)
def test_known_membership_multi_index(desc: str, index: str, date: str, ticker: str, expected: bool):
    df = pitindex.get_constituents(date, index=index)
    assert (ticker in df["ticker"].values) is expected, (
        f"{desc}: expected {ticker} {'in' if expected else 'absent'} on {date} ({index}); "
        f"roster size={len(df)}"
    )


def test_new_indices_roster_sizes_in_band():
    for date in ("2013-06-14", "2017-06-15", "2021-06-15", "2025-06-16"):
        df = pitindex.get_constituents(date, index="sp400")
        assert 395 <= len(df) <= 410, f"sp400 size {len(df)} on {date} outside band"
    for date in ("2021-06-15", "2023-06-15", "2025-06-16"):
        df = pitindex.get_constituents(date, index="sp600")
        assert 590 <= len(df) <= 615, f"sp600 size {len(df)} on {date} outside band"
