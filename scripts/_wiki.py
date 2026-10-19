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
from collections.abc import Sequence
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger as log

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
    action: str  # 'added' | 'removed' | 'renamed'
    ticker: str  # for 'renamed': the OLD ticker
    name: str | None
    reason: str | None
    new_ticker: str | None = None  # only for 'renamed'
    # 'fill' marks events derived from wiki revision diffs. Their dates are
    # upper bounds (the page lags its own changes table by months), so a
    # fill that lands on an already-consistent roster is a benign no-op,
    # not a reconciliation anomaly.
    origin: str | None = None  # None (precise) | 'fill'
    # Where a changes-table event was read (page · table · row: raw cells),
    # quoted in the reconciliation report so an anomaly can be traced back
    # to the Wikipedia row behind it. Not part of the event's identity.
    source: str | None = field(default=None, compare=False)


def fetch_html(url: str = WIKI_URL, timeout: int = 30) -> str:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    return r.text


# --- table location --------------------------------------------------------

# The table ids are editor-maintained anchors, not guaranteed markup: they get
# dropped or renamed whenever somebody rewrites a table (the 'changes' id
# vanished from the S&P 500 page in August 2026, breaking the weekly refresh).
# When the id is missing we identify the table by its header signature instead,
# the same way ``_wikirev`` copes with pre-2021 revisions of the 400/600 pages.
#
# ``require``: the header must mention at least one needle from every group.
# ``reject``:  the header must mention none of these — it keeps the changes
#              table (whose second header row carries Ticker/Security) from
#              masquerading as a roster table.
_TableSignature = tuple[tuple[tuple[str, ...], ...], tuple[str, ...]]

_HEADER_SIGNATURES: dict[str, _TableSignature] = {
    "constituents": ((("symbol", "ticker"), ("security", "company")), ("removed",)),
    "changes": ((("date",), ("added",), ("removed",)), ()),
}


def _header_text(table: Tag) -> str:
    """Lowercased text of a table's first two rows.

    Two rows, because the changes table has a two-level header (Date | Added |
    Removed | Reason, then Ticker | Security | Ticker | Security).
    """
    cells = [c for row in table.find_all("tr")[:2] for c in row.find_all(["th", "td"])]
    return " ".join(_cell_text(c).lower() for c in cells)


def _find_tables(soup: BeautifulSoup, table_id: str, *, required: bool = True) -> list[Tag]:
    """Locate a known table by id, falling back to its header signature.

    Returns every match, largest first — a table split into several (e.g. a
    current list plus an archive) still yields all of its parts. With
    ``required=False`` an absent table gives an empty list instead of raising:
    the changes table no longer lives on the roster page, but we still look
    there in case the split is ever undone.
    """
    table = soup.find("table", id=table_id)
    if table is not None:
        return [table]

    require, reject = _HEADER_SIGNATURES[table_id]
    hits: list[Tag] = []
    for t in soup.find_all("table"):
        header = _header_text(t)
        if any(n in header for n in reject):
            continue
        if all(any(n in header for n in group) for group in require):
            hits.append(t)
    if not hits:
        if not required:
            return []
        raise RuntimeError(
            f"Could not find table id={table_id!r} on Wikipedia page, and no table matches "
            f"its header signature {require}. The page structure may have changed."
        )
    hits.sort(key=lambda t: len(t.find_all("tr")), reverse=True)
    log.warning(
        "Table id={!r} is missing from the Wikipedia page; matched {} table(s) by header instead.",
        table_id,
        len(hits),
    )
    return hits


def _find_table(soup: BeautifulSoup, table_id: str) -> Tag:
    return _find_tables(soup, table_id)[0]


def _cell_text(cell: Tag) -> str:
    # Strip footnote refs, normalize whitespace. get_text(separator=" ")
    # renders a <sup> ref as "[ 320 ]", so allow spaces inside the brackets —
    # a ref left in a date cell made the date unparseable (sp400, 2026-10).
    text = cell.get_text(separator=" ", strip=True)
    text = re.sub(r"\[\s*\d+\s*\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _span(cell: Tag, attr: str) -> int:
    m = re.match(r"\d+", str(cell.get(attr) or "1"))
    return max(int(m.group()), 1) if m else 1


def _table_grid(table: Tag) -> list[tuple[bool, list[str]]]:
    """Rows as ``(is_header_row, cell texts)``, rowspan/colspan expanded.

    A cell spanning several rows (e.g. one date shared by consecutive
    changes) is repeated into each row it covers, so every row keeps its
    full column layout instead of shifting left.
    """
    grid: list[tuple[bool, list[str]]] = []
    carried: dict[int, tuple[int, str]] = {}  # column -> (rows still covered, text)
    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        queue = list(cells)
        row: list[str] = []
        while queue or len(row) in carried:
            col = len(row)
            if col in carried:
                left, text = carried.pop(col)
                if left > 1:
                    carried[col] = (left - 1, text)
                row.append(text)
                continue
            cell = queue.pop(0)
            text, rowspan = _cell_text(cell), _span(cell, "rowspan")
            for _ in range(_span(cell, "colspan")):
                if rowspan > 1:
                    carried[len(row)] = (rowspan - 1, text)
                row.append(text)
        grid.append((all(c.name == "th" for c in cells), row))
    return grid


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
    return parse_constituents_table(table)


def parse_constituents_table(table: Tag) -> list[Constituent]:
    """Parse one roster table. Only Symbol and Security columns are required;
    CIK/GICS/date-added are optional (the S&P 400 page has no CIK column and
    pre-2021 revisions of the 400/600 pages lack the stable table id)."""
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


# A plausible ticker: 1-6 alphanumerics plus an optional .X class suffix.
# Filters out company names that leak into the ticker column of old-format
# changes-table rows (the S&P 400 page switched column layout ~mid-2019)
# and compound cells like "UA/UAA".
_TICKER_SHAPE = re.compile(r"^[A-Z0-9]{1,6}(\.[A-Z])?$")

_SOURCE_MAX = 160  # raw-row excerpt kept in ChangeEvent.source


# --- change events ---------------------------------------------------------


def parse_changes(
    *htmls: str, required: bool = True, sources: Sequence[str] | None = None
) -> list[ChangeEvent]:
    """Parse the changes table(s) of one or more pages into a flat event list.

    Each table has a two-row header:
        (Effective) Date | Added         | Removed       | Reason | Refs
        ---------------- | Ticker | Sec. | Ticker | Sec. |
    A single 'date' row may carry up to one Added (ticker+name) AND one
    Removed (ticker+name). We emit one ChangeEvent per side that has data.

    Pages are given in priority order. The first page that yields events is
    the primary source; later pages contribute only events dated after the
    primary's newest one. Since the 2026-08 split the changes live on
    'Historical components of the S&P NNN', but by 2026-10 the S&P 400/600
    roster pages carried an older copy of the table again, whose dates
    disagree with the primary's — merging both doubled those events. A
    stale primary still picks up recent changes from the other page.
    Within that, events are deduplicated on (date, action, ticker).
    ``required`` guards the result: at least one page must yield events.
    ``sources`` names the pages (same order as ``htmls``) in each event's
    ``source``.
    """
    out: list[ChangeEvent] = []
    seen: set[tuple[str, str, str]] = set()
    dropped = 0
    newest: str | None = None  # primary page's latest event date
    for i, html in enumerate(htmls):
        page = sources[i] if sources else f"page {i + 1}"
        soup = BeautifulSoup(html, "lxml")
        page_events: list[ChangeEvent] = []
        for j, table in enumerate(_find_tables(soup, "changes", required=False), start=1):
            events, table_dropped = _parse_changes_table(table, f"{page} · table {j}")
            dropped += table_dropped
            page_events += events
        for e in page_events:
            key = (e.date, e.action, e.ticker)
            if key not in seen and (newest is None or e.date > newest):
                seen.add(key)
                out.append(e)
        if out and newest is None:
            newest = max(e.date for e in out)
    if dropped:
        log.info("parse_changes: dropped {} non-ticker-shaped entries (old-format rows)", dropped)
    if not out and required:
        raise RuntimeError(
            "No changes events parsed from any of the supplied pages. The changes table has "
            "moved or changed layout again — check 'Historical components of the S&P NNN'."
        )
    # _reconcile re-sorts anyway; sort here so a multi-page merge is deterministic.
    out.sort(key=lambda e: (e.date, e.action, e.ticker))
    return out


def _parse_changes_table(table: Tag, label: str = "") -> tuple[list[ChangeEvent], int]:
    """Parse one changes table. Returns (events, dropped-entry count)."""
    # The first 1-2 rows are headers (th-only rows).
    data_rows = [cells for is_header, cells in _table_grid(table) if not is_header]

    out: list[ChangeEvent] = []
    last_date: str | None = None
    dropped = 0
    for row_no, cells in enumerate(data_rows, start=1):
        if len(cells) < 5:
            continue
        # Standard layout: [date, added_ticker, added_name, removed_ticker, removed_name, reason]
        date_iso_raw, add_t, add_n, rem_t, rem_n, *rest = cells[:6]
        reason = rest[0] if rest else None

        date_iso = _parse_date(date_iso_raw) or last_date
        if date_iso is None:
            # Without a date, we cannot place the event in time; skip.
            continue
        last_date = date_iso

        for action, ticker_raw, name in (("added", add_t, add_n), ("removed", rem_t, rem_n)):
            if not ticker_raw:
                continue
            ticker = _normalize_ticker(ticker_raw)
            if not _TICKER_SHAPE.match(ticker):
                # Old-format row (or compound cell): the "ticker" is a company
                # name. Drop it — revision-diff fills recover the event.
                dropped += 1
                continue
            out.append(
                ChangeEvent(
                    date=date_iso,
                    action=action,
                    ticker=ticker,
                    name=name or None,
                    reason=reason or None,
                    source=f"{label} · row {row_no}: {' | '.join(cells)[:_SOURCE_MAX]}",
                )
            )
    return out, dropped


__all__ = [
    "ChangeEvent",
    "Constituent",
    "fetch_html",
    "parse_changes",
    "parse_constituents_table",
    "parse_current_constituents",
]
