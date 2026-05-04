"""Fetch and parse the Wikipedia article 'List of S&P 500 companies'.

The article exposes two tables we care about, both with stable HTML ids:
  - ``constituents``: the current S&P 500 roster
  - ``changes``: the curated list of additions / removals over time

We trust the *current* roster as ground truth for "as of build date" and
use the changes table as the event log to walk the membership backwards
in time. Reconciliation between the two happens in ``_reconcile.py``.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, Tag

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
USER_AGENT = "pitindex/0.1 (+https://github.com/arielnacamulli/pitindex) python-requests"


@dataclass(frozen=True)
class Constituent:
    ticker: str
    name: str
    cik: str | None
    gics_sector: str | None
    gics_sub_industry: str | None
    date_added: str | None  # ISO date or None


@dataclass(frozen=True)
class ChangeEvent:
    date: str  # ISO date, YYYY-MM-DD
    action: str  # 'added' | 'removed'
    ticker: str
    name: str | None
    reason: str | None


def fetch_html(url: str = WIKI_URL, timeout: int = 30) -> str:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    return r.text


# --- table location --------------------------------------------------------


def _find_table(soup: BeautifulSoup, table_id: str) -> Tag:
    table = soup.find("table", id=table_id)
    if table is None:
        raise RuntimeError(
            f"Could not find table id={table_id!r} on Wikipedia page. The page structure may have changed."
        )
    return table


def _cell_text(cell: Tag) -> str:
    # Strip footnote refs like [1], normalize whitespace
    text = cell.get_text(separator=" ", strip=True)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# --- date parsing ----------------------------------------------------------

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _parse_date(s: str) -> str | None:
    """Parse the Wikipedia-style date strings into ISO YYYY-MM-DD.

    Handles: 'January 21, 2010', '2010-01-21', '1976' (year only -> None),
    'October 2 2018', 'Sept 1, 2020' (rare abbreviations).
    Returns None when the string is empty, '-', or just a year.
    """
    # Wikipedia uses several dash glyphs in "no value" cells; normalise them all.
    if not s or s in {"-", "—", "–", "N/A", "n/a"}:  # noqa: RUF001
        return None
    s = s.strip().rstrip(".")

    # ISO-ish
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return s

    # Year only: not specific enough to be useful as an event date
    if re.match(r"^\d{4}$", s):
        return None

    # 'Month Day, Year' or 'Month Day Year'
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", s)
    if m:
        month_name, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        # Normalize 3-letter abbreviations
        for full, num in _MONTHS.items():
            if full.startswith(month_name) or month_name.startswith(full[:3]):
                try:
                    return dt.date(year, num, day).isoformat()
                except ValueError:
                    return None
    return None


# --- current roster --------------------------------------------------------


def parse_current_constituents(html: str) -> list[Constituent]:
    soup = BeautifulSoup(html, "lxml")
    table = _find_table(soup, "constituents")

    # Map header text -> column index
    header_cells = table.find("tr").find_all(["th", "td"])
    headers = [_cell_text(c).lower() for c in header_cells]

    def col(*needles: str) -> int | None:
        for i, h in enumerate(headers):
            if any(n in h for n in needles):
                return i
        return None

    idx_symbol = col("symbol", "ticker")
    idx_security = col("security", "company")
    idx_sector = col("gics sector")
    idx_sub = col("sub-industry", "sub industry")
    idx_cik = col("cik")
    idx_date = col("date added", "date first added")

    if idx_symbol is None or idx_security is None:
        raise RuntimeError(
            f"Cannot locate Symbol/Security columns in constituents table. Headers seen: {headers}"
        )

    out: list[Constituent] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= max(
            filter(None, [idx_symbol, idx_security, idx_sector, idx_sub, idx_cik, idx_date])
        ):
            continue
        # Wikipedia occasionally embeds U+00A0 (no-break space) inside ticker cells.
        ticker = _cell_text(cells[idx_symbol]).replace("\xa0", "").strip()
        if not ticker:
            continue
        name = _cell_text(cells[idx_security])
        cik = _cell_text(cells[idx_cik]) if idx_cik is not None else ""
        cik = cik.lstrip("0") or None  # store unpadded; pad on output
        if cik is not None and not cik.isdigit():
            cik = None
        sector = _cell_text(cells[idx_sector]) if idx_sector is not None else None
        sub = _cell_text(cells[idx_sub]) if idx_sub is not None else None
        date_added = _parse_date(_cell_text(cells[idx_date])) if idx_date is not None else None
        out.append(
            Constituent(
                ticker=_normalize_ticker(ticker),
                name=name,
                cik=cik,
                gics_sector=sector or None,
                gics_sub_industry=sub or None,
                date_added=date_added,
            )
        )
    return out


def _normalize_ticker(t: str) -> str:
    # Wikipedia uses ".B" for class B shares (BRK.B); some sources use "BRK-B".
    # We standardize on dot notation, matching Wikipedia + S&P press releases.
    return t.upper().replace("-", ".").strip()


# --- change events ---------------------------------------------------------


def parse_changes(html: str) -> list[ChangeEvent]:
    """Parse the 'Selected changes' table into a flat list of events.

    The table has a two-row header:
        Date | Added         | Removed       | Reason
        ---- | Ticker | Sec. | Ticker | Sec. |
    A single 'date' row may carry up to one Added (ticker+name) AND one
    Removed (ticker+name). We emit one ChangeEvent per side that has data.
    """
    soup = BeautifulSoup(html, "lxml")
    table = _find_table(soup, "changes")
    rows = table.find_all("tr")

    # The first 1-2 rows are headers. Detect them (any th-only rows).
    data_rows: list[Tag] = []
    for r in rows:
        cells = r.find_all(["td", "th"])
        if not cells:
            continue
        if all(c.name == "th" for c in cells):
            continue
        data_rows.append(r)

    out: list[ChangeEvent] = []
    last_date: str | None = None
    for row in data_rows:
        cells = [_cell_text(c) for c in row.find_all(["td", "th"])]
        if len(cells) < 5:
            continue
        # Standard layout: [date, added_ticker, added_name, removed_ticker, removed_name, reason]
        date_raw, add_t, add_n, rem_t, rem_n, *rest = cells[:6]
        reason = rest[0] if rest else None

        date_iso = _parse_date(date_raw) or last_date
        if date_iso is None:
            # Without a date, we cannot place the event in time; skip.
            continue
        last_date = date_iso

        if add_t:
            out.append(
                ChangeEvent(
                    date=date_iso,
                    action="added",
                    ticker=_normalize_ticker(add_t),
                    name=add_n or None,
                    reason=reason or None,
                )
            )
        if rem_t:
            out.append(
                ChangeEvent(
                    date=date_iso,
                    action="removed",
                    ticker=_normalize_ticker(rem_t),
                    name=rem_n or None,
                    reason=reason or None,
                )
            )
    return out


__all__ = [
    "ChangeEvent",
    "Constituent",
    "fetch_html",
    "parse_changes",
    "parse_current_constituents",
]
