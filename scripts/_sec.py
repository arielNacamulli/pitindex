"""CIK validation against the SEC's official ticker→CIK mapping.

Wikipedia's constituent tables occasionally carry *stale* CIKs — e.g.
the S&P 600 page listed the pre-bankruptcy Noble CIK for today's NE and
the long-dead Wendy's International CIK for WEN (found by pitdata's
cik-consistency cross-check, 2026-07-13). The SEC's
``company_tickers.json`` is the authoritative *current* mapping, so at
build time we correct mismatches and fill CIKs Wikipedia doesn't carry
at all (the S&P 400 page has no CIK column).

Scope note: the mapping is current-only, so it applies to the *current*
roster snapshot — exactly where it is used. Historical (delisted)
tickers must not be resolved this way: the SEC map would return
whatever company holds the recycled ticker today.
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Callable

import requests
from loguru import logger as log

from ._wiki import Constituent, _normalize_ticker

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
# SEC fair-access policy requires a UA with a contact; override via env
# for forks. Same convention as pitedgar's --identity.
# NB: sec.gov's WAF rejects UAs containing URLs/parentheses on /files/;
# the accepted shape is a plain "app contact" string.
USER_AGENT = os.environ.get("PITINDEX_SEC_IDENTITY", "pitindex ariel.nacamulli@gmail.com")


def fetch_sec_ticker_map(url: str = SEC_TICKERS_URL, timeout: int = 30) -> dict[str, str]:
    """ticker (dot-notation) -> zero-padded CIK from the SEC's official file."""
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    out: dict[str, str] = {}
    for row in r.json().values():
        ticker = _normalize_ticker(str(row.get("ticker", "")))
        cik = str(row.get("cik_str", "")).strip()
        if ticker and cik.isdigit():
            out[ticker] = cik.zfill(10)
    if len(out) < 5000:  # the real file carries ~10k tickers
        raise RuntimeError(f"SEC ticker map suspiciously small ({len(out)} entries).")
    return out


def ticker_confirmed(cik: str, ticker: str, timeout: int = 30) -> bool | None:
    """Whether the SEC submissions record for ``cik`` lists ``ticker``.

    Returns None on network trouble (caller must stay conservative).
    Used to arbitrate wiki-vs-company_tickers disagreements: the file
    can carry premature entries (e.g. a pending holdco reorg shell
    claiming XOM while EXXON MOBIL CORP is still the registrant).
    """
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        r.raise_for_status()
        listed = {_normalize_ticker(t) for t in r.json().get("tickers", [])}
    except (requests.RequestException, ValueError):
        return None
    return _normalize_ticker(ticker) in listed


def correct_ciks(
    current: list[Constituent],
    sec_map: dict[str, str],
    index_key: str,
    confirm: Callable[[str, str], bool | None] = ticker_confirmed,
) -> tuple[list[Constituent], int, int]:
    """Return (corrected roster, n_corrected, n_filled).

    - Wiki CIK missing but the SEC map has the ticker → filled.
    - Wiki CIK disagrees with the SEC map → arbitrated via the SEC
      submissions API: the CIK whose submissions actually list the
      ticker wins; on ambiguity or network failure the wiki value is
      kept (conservative: never override with an unverified value).
    - Ticker absent from the SEC map → left untouched.
    """
    corrected = 0
    filled = 0
    out: list[Constituent] = []
    for c in current:
        sec_cik = sec_map.get(c.ticker)
        if sec_cik is None:
            out.append(c)
            continue
        wiki_cik = c.cik.zfill(10) if c.cik else None
        if wiki_cik is None:
            out.append(dataclasses.replace(c, cik=sec_cik.lstrip("0")))
            filled += 1
        elif wiki_cik != sec_cik:
            if confirm(sec_cik, c.ticker):
                log.warning(
                    "[{}] stale wiki CIK for {}: {} → {} (SEC company_tickers, confirmed by submissions)",
                    index_key,
                    c.ticker,
                    wiki_cik,
                    sec_cik,
                )
                out.append(dataclasses.replace(c, cik=sec_cik.lstrip("0")))
                corrected += 1
            else:
                log.warning(
                    "[{}] company_tickers says {} → {}, but submissions do not confirm; "
                    "keeping wiki CIK {} (premature/shell entry?)",
                    index_key,
                    c.ticker,
                    sec_cik,
                    wiki_cik,
                )
                out.append(c)
        else:
            out.append(c)
    return out, corrected, filled


__all__ = ["correct_ciks", "fetch_sec_ticker_map", "ticker_confirmed"]
