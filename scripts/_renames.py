"""Curated ticker rename events.

Wikipedia's "Selected changes" table treats a ticker change for a
continuing index member as a no-op (the *company* did not enter or
leave the index, so there is no entry). The seed dataset, similarly,
sometimes records the removal of the old ticker without recording the
addition of the new ticker for merger-style rebrands. The result is a
walk-forward roster that mixes pre-rename and post-rename ticker
notations.

This module loads ``data/ticker_renames.csv`` and turns each row into a
single ``renamed`` ChangeEvent (old ticker in ``ticker``, new one in
``new_ticker``). The reconciliation walk applies a rename *only when the
old ticker is in the roster* — which makes the file safely global across
indices: S&P 1500 sub-indices are mutually exclusive, so each rename
fires in exactly the index that holds the old ticker and silently
no-ops everywhere else (DESIGN.md §4).
"""

from __future__ import annotations

import csv
from pathlib import Path

from loguru import logger as log

from ._wiki import ChangeEvent


def load_renames(path: Path) -> list[ChangeEvent]:
    """Read a renames CSV and return one ``renamed`` event per row."""
    if not path.exists():
        log.warning("Renames CSV not found at {}; proceeding without renames.", path)
        return []
    out: list[ChangeEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            date = (row.get("date") or "").strip()
            old = (row.get("old_ticker") or "").strip().upper()
            new = (row.get("new_ticker") or "").strip().upper()
            reason = (row.get("reason") or "").strip() or None
            if not (date and old and new):
                continue
            out.append(
                ChangeEvent(
                    date=date,
                    action="renamed",
                    ticker=old,
                    name=None,
                    reason=reason,
                    new_ticker=new,
                )
            )
    log.info("Loaded {} rename events from {}", len(out), path)
    return out


def load_manual_events(path: Path, index: str = "sp500") -> list[ChangeEvent]:
    """Load explicit add/remove events that close known upstream data gaps.

    Used for cases where neither the seed nor the Wikipedia changes
    table captures a real index event (e.g. the GE removal on
    2018-06-26 which the upstream seed dataset omits).

    Rows carry an ``index`` column; rows with an empty value default to
    ``sp500`` (the file predates multi-index support). Only rows for the
    requested ``index`` are returned.
    """
    if not path.exists():
        log.warning("Manual events CSV not found at {}; proceeding without overrides.", path)
        return []
    out: list[ChangeEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row_index = (row.get("index") or "").strip().lower() or "sp500"
            if row_index != index:
                continue
            date = (row.get("date") or "").strip()
            action = (row.get("action") or "").strip().lower()
            ticker = (row.get("ticker") or "").strip().upper()
            name = (row.get("name") or "").strip() or None
            reason = (row.get("reason") or "").strip() or None
            if not (date and action and ticker):
                continue
            if action not in {"added", "removed"}:
                log.warning("Skipping manual event with unknown action {!r}", action)
                continue
            out.append(
                ChangeEvent(
                    date=date,
                    action=action,
                    ticker=ticker,
                    name=name,
                    reason=f"manual override: {reason or ''}".rstrip(": "),
                )
            )
    log.info("Loaded {} manual override events from {}", len(out), path)
    return out


__all__ = ["load_manual_events", "load_renames"]
