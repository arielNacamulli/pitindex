"""Wikipedia table location + changes parsing (unit, offline).

Regression cover for the August 2026 weekly-refresh failure. On 2026-08-11
Wikipedia moved the changes tables out of 'List of S&P NNN companies' into
'Historical components of the S&P NNN', so the build aborted with
"Could not find table id='changes'". The parser now reads both pages and
merges them, and falls back to a header signature when the id is missing.
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

# Mirrors the live layout of 'Historical components of the S&P 500': the date
# column is headed "Effective Date" and a trailing Refs column follows Reason.
CHANGES_ROWS = """
  <tr><th rowspan="2">Effective Date</th><th colspan="2">Added</th>
      <th colspan="2">Removed</th><th rowspan="2">Reason</th><th rowspan="2">Refs</th></tr>
  <tr><th>Ticker</th><th>Security</th><th>Ticker</th><th>Security</th></tr>
  <tr><td>June 30, 2026</td><td>NEWCO</td><td>Newco Inc.</td>
      <td>OLDCO</td><td>Oldco Inc.</td><td>Market cap change</td><td>[1]</td></tr>
  <tr><td>March 24, 2026</td><td>ACME</td><td>Acme Corp.</td>
      <td></td><td></td><td>S&amp;P 500 constituent</td><td>[2]</td></tr>
"""

ROSTER_PAGE = (
    f'<html><body><table class="wikitable" id="constituents">{CONSTITUENTS_ROWS}</table></body></html>'
)
HISTORICAL_PAGE = f'<html><body><table class="wikitable" id="changes">{CHANGES_ROWS}</table></body></html>'

EXPECTED_EVENTS = {
    ("2026-03-24", "added", "ACME"),
    ("2026-06-30", "added", "NEWCO"),
    ("2026-06-30", "removed", "OLDCO"),
}


def page(*, constituents_id: str | None = "constituents", changes_id: str | None = "changes") -> str:
    def attr(value: str | None) -> str:
        return f' id="{value}"' if value else ""

    return f"""<html><body>
      <table class="wikitable"{attr(constituents_id)}>{CONSTITUENTS_ROWS}</table>
      <table class="wikitable"{attr(changes_id)}>{CHANGES_ROWS}</table>
    </body></html>"""


def test_tables_are_found_by_id():
    assert [c.ticker for c in parse_current_constituents(page())] == ["AAPL", "MSFT"]
    assert {(e.date, e.action, e.ticker) for e in parse_changes(page())} == EXPECTED_EVENTS


def test_changes_come_from_the_historical_components_page():
    """The live post-split layout: roster on one page, events on another."""
    assert [c.ticker for c in parse_current_constituents(ROSTER_PAGE)] == ["AAPL", "MSFT"]
    events = parse_changes(ROSTER_PAGE, HISTORICAL_PAGE)
    assert {(e.date, e.action, e.ticker) for e in events} == EXPECTED_EVENTS


def test_both_pages_carrying_the_table_is_deduped():
    """A revert of the split must not double every event."""
    assert parse_changes(page(), HISTORICAL_PAGE) == parse_changes(HISTORICAL_PAGE)


def test_changes_table_is_found_without_its_id():
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


def test_no_changes_table_anywhere_still_raises():
    """What the build must keep doing if the table moves again."""
    with pytest.raises(RuntimeError, match="moved or changed layout"):
        parse_changes(ROSTER_PAGE)


def test_missing_changes_table_is_tolerated_when_optional():
    assert parse_changes(ROSTER_PAGE, required=False) == []


def test_events_record_their_source_row():
    """Anomalies in the reconciliation report trace back to the Wikipedia row."""
    events = parse_changes(ROSTER_PAGE, HISTORICAL_PAGE, sources=("List", "Historical"))
    newco = next(e for e in events if e.ticker == "NEWCO")
    assert newco.source is not None
    assert newco.source.startswith("Historical · table 1 · row 1: June 30, 2026 | NEWCO")


def test_duplicate_shows_both_copies_in_report():
    import datetime as dt

    from scripts._reconcile import ReconciliationError, reconcile, render_report_md
    from scripts._wiki import ChangeEvent

    events = [
        ChangeEvent("2015-07-08", "added", "JACK", None, None, source="Historical · row 7"),
        ChangeEvent("2015-07-30", "added", "JACK", None, None, source="Historical · row 9"),
    ]
    with pytest.raises(ReconciliationError) as exc:
        reconcile(set(), dt.date(2015, 1, 1), events, [], end_date=dt.date(2015, 12, 31))
    md = render_report_md(exc.value.report)
    assert "this event: `Historical · row 9`" in md
    assert "last applied: `2015-07-08 added: Historical · row 7`" in md


# The roster page's older copy of the S&P 400 table (back since ~2026-10):
# footnote refs inside date cells, and dates shared via rowspan.
OLD_COPY_ROWS = """
  <tr><th rowspan="2">Date</th><th colspan="2">Added</th>
      <th colspan="2">Removed</th><th rowspan="2">Reason</th></tr>
  <tr><th>Ticker</th><th>Security</th><th>Ticker</th><th>Security</th></tr>
  <tr><td>July 8, 2015<sup>[320]</sup></td><td>JACK</td><td>Jack in the Box</td>
      <td>AAP</td><td>Advance Auto Parts</td><td>Dollar Tree acquired Family Dollar.</td></tr>
  <tr><td rowspan="2">July 1, 2015</td><td>CC</td><td>Chemours</td>
      <td>SMTC</td><td>Semtech</td><td>DuPont spun off Chemours.</td></tr>
  <tr><td>EPC</td><td>Edgewell Personal Care</td>
      <td>HSC</td><td>Harsco</td><td>Energizer spin-off.</td></tr>
"""
OLD_COPY_PAGE = f'<html><body><table class="wikitable" id="changes">{OLD_COPY_ROWS}</table></body></html>'


def test_footnote_in_date_cell_keeps_the_date():
    events = parse_changes(OLD_COPY_PAGE)
    assert {(e.date, e.ticker) for e in events if e.ticker in {"JACK", "AAP"}} == {
        ("2015-07-08", "JACK"),
        ("2015-07-08", "AAP"),
    }


def test_rowspan_date_does_not_shift_columns():
    """The continuation row used to read 'Harsco' as a removed ticker."""
    events = {(e.date, e.action, e.ticker) for e in parse_changes(OLD_COPY_PAGE)}
    assert ("2015-07-01", "added", "EPC") in events
    assert ("2015-07-01", "removed", "HSC") in events
    assert not any(t == "HARSCO" for _, _, t in events)


def test_secondary_page_only_adds_events_newer_than_the_primary():
    """The roster page's copy must not re-date events the primary already has."""
    primary = HISTORICAL_PAGE.replace("June 30, 2026", "June 30, 2015").replace(
        "March 24, 2026", "March 24, 2015"
    )
    secondary = HISTORICAL_PAGE.replace("June 30, 2026", "June 2, 2015")  # same changes, older date
    events = {(e.date, e.action, e.ticker) for e in parse_changes(primary, secondary)}
    assert events == {
        ("2015-03-24", "added", "ACME"),
        ("2015-06-30", "added", "NEWCO"),
        ("2015-06-30", "removed", "OLDCO"),
        ("2026-03-24", "added", "ACME"),  # newer than anything on the primary
    }
