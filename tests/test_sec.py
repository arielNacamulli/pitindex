"""CIK correction against the SEC official map (unit, offline)."""

from __future__ import annotations

from scripts._sec import correct_ciks
from scripts._wiki import Constituent


def c(ticker, cik):
    return Constituent(
        ticker=ticker, name=f"{ticker} Co", cik=cik, gics_sector=None, gics_sub_industry=None, date_added=None
    )


SEC = {"NE": "0001895262", "WEN": "0000030697", "AAPL": "0000320193", "BRK.B": "0001067983"}


def test_stale_wiki_cik_is_corrected():
    out, corrected, filled = correct_ciks(
        [c("NE", "72207"), c("WEN", "105668")], SEC, "sp600", confirm=lambda cik, t: True
    )
    assert corrected == 2
    assert filled == 0
    assert out[0].cik == "1895262"
    assert out[1].cik == "30697"


def test_missing_cik_is_filled():
    out, corrected, filled = correct_ciks([c("AAPL", None)], SEC, "sp400")
    assert filled == 1
    assert corrected == 0
    assert out[0].cik == "320193"


def test_disagreement_without_confirmation_keeps_wiki():
    out, corrected, _filled = correct_ciks([c("NE", "72207")], SEC, "sp600", confirm=lambda cik, t: False)
    assert corrected == 0
    assert out[0].cik == "72207"


def test_disagreement_with_network_failure_keeps_wiki():
    out, corrected, _filled = correct_ciks([c("NE", "72207")], SEC, "sp600", confirm=lambda cik, t: None)
    assert corrected == 0
    assert out[0].cik == "72207"


def test_unknown_ticker_untouched_and_agreement_kept():
    out, corrected, filled = correct_ciks([c("ZZZQ", "999"), c("AAPL", "320193")], SEC, "sp500")
    assert corrected == 0
    assert filled == 0
    assert out[0].cik == "999"
    assert out[1].cik == "320193"
