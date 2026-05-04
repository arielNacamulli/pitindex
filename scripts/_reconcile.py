"""Reconciliation between the seed snapshot and the Wikipedia change log.

Algorithm
---------
1. Start with the seed roster at ``start_date``.
2. Sort all change events chronologically and apply them, one by one.
3. At each step, validate the event:
     - 'added' on a ticker already in the roster -> structural anomaly
     - 'removed' on a ticker not in the roster -> structural anomaly
4. After applying every event, compare the resulting set against the
   *current* Wikipedia roster (as of build time).
5. Any leftover diff implies missing or spurious events. Generate
   "synthetic" events to close the gap and record them in the build log,
   so a downstream consumer can reproduce the exact roster Wikipedia
   shows today.
6. If the magnitude of anomalies exceeds ``max_diff_ratio``, raise so the
   build fails loudly rather than shipping silently-corrupt data.

The output is:
- A reconciled, deduplicated, chronologically-sorted list of events that,
  applied to the seed, *exactly* reproduces today's Wikipedia roster.
- A structured report (dict) summarizing all anomalies and synthetic
  fixes for the build log.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from loguru import logger as log

from ._wiki import ChangeEvent, Constituent


@dataclass
class ReconciliationReport:
    start_date: str
    end_date: str
    seed_size: int
    current_size: int
    final_size_after_events: int
    invalid_add_existing: list[dict] = field(default_factory=list)
    invalid_remove_missing: list[dict] = field(default_factory=list)
    missing_from_walk: list[str] = field(default_factory=list)  # in current but walk lost them
    extra_from_walk: list[str] = field(default_factory=list)  # walk has them, current doesn't
    synthetic_events_added: int = 0
    diff_ratio: float = 0.0


def reconcile(
    seed_roster: set[str],
    start_date: dt.date,
    events: list[ChangeEvent],
    current: list[Constituent],
    *,
    end_date: dt.date | None = None,
    max_diff_ratio: float = 0.05,
) -> tuple[list[ChangeEvent], ReconciliationReport]:
    end_date = end_date or dt.date.today()
    current_set = {c.ticker for c in current}

    # Filter to events within the window we care about
    in_window = [e for e in events if start_date.isoformat() <= e.date <= end_date.isoformat()]
    in_window.sort(key=lambda e: (e.date, 0 if e.action == "removed" else 1))
    # Process removals before additions on the same day so a same-day
    # ticker reuse (rare but possible) does not collide.

    roster = set(seed_roster)
    report = ReconciliationReport(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        seed_size=len(seed_roster),
        current_size=len(current_set),
        final_size_after_events=0,
    )

    cleaned: list[ChangeEvent] = []
    for ev in in_window:
        if ev.action == "added":
            if ev.ticker in roster:
                report.invalid_add_existing.append({"date": ev.date, "ticker": ev.ticker})
                # Skip: keeping it would inflate the roster phantom-style
                continue
            roster.add(ev.ticker)
        elif ev.action == "removed":
            if ev.ticker not in roster:
                report.invalid_remove_missing.append({"date": ev.date, "ticker": ev.ticker})
                continue
            roster.discard(ev.ticker)
        else:
            log.warning("Unknown action {!r} at {}, skipping", ev.action, ev.date)
            continue
        cleaned.append(ev)

    report.final_size_after_events = len(roster)

    # Diff vs. ground truth
    missing = sorted(current_set - roster)  # current has, walk lost
    extra = sorted(roster - current_set)  # walk has, current doesn't

    report.missing_from_walk = missing
    report.extra_from_walk = extra

    # Synthetic fixes:
    #   * For tickers missing from the walk: insert an 'added' event at start_date
    #     (we know they're current and the seed didn't have them; treat as
    #     pre-window admissions).
    #   * For tickers extra in the walk: insert a 'removed' event at end_date
    #     (we know they were members at some point and aren't anymore).
    synthetic_date_add = start_date.isoformat()
    synthetic_date_rem = end_date.isoformat()

    # Map tickers to names from current roster for nicer output
    name_by_ticker = {c.ticker: c.name for c in current}

    for t in missing:
        cleaned.append(
            ChangeEvent(
                date=synthetic_date_add,
                action="added",
                ticker=t,
                name=name_by_ticker.get(t),
                reason="reconciliation: present in current roster, absent from event walk",
            )
        )
        report.synthetic_events_added += 1
    for t in extra:
        cleaned.append(
            ChangeEvent(
                date=synthetic_date_rem,
                action="removed",
                ticker=t,
                name=None,
                reason="reconciliation: absent from current roster, present after event walk",
            )
        )
        report.synthetic_events_added += 1

    cleaned.sort(key=lambda e: (e.date, 0 if e.action == "removed" else 1, e.ticker))

    # Diff ratio against current roster
    diff_n = len(missing) + len(extra) + len(report.invalid_add_existing) + len(report.invalid_remove_missing)
    report.diff_ratio = diff_n / max(len(current_set), 1)

    if report.diff_ratio > max_diff_ratio:
        raise ReconciliationError(
            f"Reconciliation diff ratio {report.diff_ratio:.1%} exceeds threshold "
            f"{max_diff_ratio:.0%}. See report for details.",
            report=report,
        )

    return cleaned, report


class ReconciliationError(RuntimeError):
    def __init__(self, message: str, *, report: ReconciliationReport):
        super().__init__(message)
        self.report = report


def render_report_md(report: ReconciliationReport) -> str:
    lines = [
        "# Reconciliation Report",
        "",
        f"- Window: **{report.start_date} → {report.end_date}**",
        f"- Seed roster size: **{report.seed_size}**",
        f"- Current Wikipedia roster size: **{report.current_size}**",
        f"- Roster size after walking events: **{report.final_size_after_events}**",
        f"- Diff ratio vs. current: **{report.diff_ratio:.2%}**",
        f"- Synthetic events inserted: **{report.synthetic_events_added}**",
        "",
        f"## Invalid 'added' on existing ticker ({len(report.invalid_add_existing)})",
        "",
    ]
    for x in report.invalid_add_existing:
        lines.append(f"- {x['date']}  {x['ticker']}")
    lines += [
        "",
        f"## Invalid 'removed' on missing ticker ({len(report.invalid_remove_missing)})",
        "",
    ]
    for x in report.invalid_remove_missing:
        lines.append(f"- {x['date']}  {x['ticker']}")
    lines += [
        "",
        f"## Missing from event walk (synthetic add at start_date) ({len(report.missing_from_walk)})",
        "",
        ", ".join(report.missing_from_walk) or "_none_",
        "",
        f"## Extra from event walk (synthetic remove at end_date) ({len(report.extra_from_walk)})",
        "",
        ", ".join(report.extra_from_walk) or "_none_",
        "",
    ]
    return "\n".join(lines)


__all__ = [
    "ReconciliationError",
    "ReconciliationReport",
    "reconcile",
    "render_report_md",
]
