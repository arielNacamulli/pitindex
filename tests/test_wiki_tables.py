"""Wikipedia table location + changes parsing (unit, offline).

Regression cover for the August 2026 weekly-refresh failure: the ``changes``
id disappeared from the S&P 500 page and the build aborted with
"Could not find table id='changes'". The parser now falls back to matching
the table by its header signature.
"""

from __future__ import annotations

import pytest

from scripts._wiki import parse_changes, parse_current_constituents

CONSTITUENTS_ROWS = """
  <tr><th>Symbol</th><th>Security</th><th>GICS Sector</th>
      <th>CIK</th><th>Date added</th></tr>
  <tr><td>AAPL</td><td>Apple Inc.</td><td>Information Technology</td>
      <td>0000320193</td><td>November 30, 1982</td></tr>
  <tr><td>MSFT</td><td>Microsoft</td><td>Information Technology</td>
      <td>0000789019</td><td>June 1, 1994</td></tr>
"""

CHANGES_ROWS = """
  <tr><th rowspan="2">Date</th><th colspan="2">Added</th>
      <th colspan="2">Removed</th><th rowspan="2">Reason</th></tr>
  <tr><th>Ticker</th><th>Security</th><th>Ticker</th><th>Security</th></tr>
  <tr><td>June 30, 2026</td><td>NEWCO</td><td>Newco Inc.</td>
      <td>OLDCO</td><td>Oldco Inc.</td><td>Market cap change</td></tr>
  <tr><td>March 24, 2026</td><td>ACME</td><td>Acme Corp.</td>
      <td></td><td></td><td>S&amp;P 500 constituent</td></tr>
"""


def page(*, constituents_id: str | None = "constituents", changes_id: str | None = "changes") -> str:
    def attr(value: str | None) -> str:
        return f' id="{value}"' if value else ""

    return f"""<html><body>
      <table class="wikitable"{attr(constituents_id)}>{CONSTITUENTS_ROWS}</table>
      <table class="wikitable"{attr(changes_id)}>{CHANGES_ROWS}</table>
    </body></html>"""


def test_tables_are_found_by_id():
    assert [c.ticker for c in parse_current_constituents(page())] == ["AAPL", "MSFT"]
    events = parse_changes(page())
    assert {(e.date, e.action, e.ticker) for e in events} == {
        ("2026-03-24", "added", "ACME"),
        ("2026-06-30", "added", "NEWCO"),
        ("2026-06-30", "removed", "OLDCO"),
    }


def test_changes_table_is_found_without_its_id():
    """The exact failure mode of the 2026-08-17 refresh run."""
    assert parse_changes(page(changes_id=None)) == parse_changes(page())


def test_constituents_table_is_found_without_its_id():
    """The changes table also has Ticker/Security headers — don't pick it."""
    roster = parse_current_constituents(page(constituents_id=None))
    assert [c.ticker for c in roster] == ["AAPL", "MSFT"]


def test_split_changes_tables_are_merged_and_deduped():
    html = f"""<html><body>
      <table class="wikitable" id="constituents">{CONSTITUENTS_ROWS}</table>
      <table class="wikitable">{CHANGES_ROWS}</table>
      <table class="wikitable">{CHANGES_ROWS}
        <tr><td>January 2, 2015</td><td>OLDIE</td><td>Oldie Inc.</td>
            <td></td><td></td><td>Archive</td></tr>
      </table>
    </body></html>"""
    events = parse_changes(html)
    assert len(events) == 4
    assert events[0].date == "2015-01-02"
    assert events[0].ticker == "OLDIE"


def test_missing_table_still_raises():
    html = '<html><body><table class="wikitable"><tr><th>Nope</th></tr></table></body></html>'
    with pytest.raises(RuntimeError, match="header signature"):
        parse_changes(html)
