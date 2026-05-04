"""Curated ticker rename events.

Wikipedia's "Selected changes" table treats a ticker change for a
continuing index member as a no-op (the *company* did not enter or
leave the index, so there is no entry). The seed dataset, similarly,
sometimes records the removal of the old ticker without recording the
addition of the new ticker for merger-style rebrands. The result is a
walk-forward roster that mixes pre-rename and post-rename ticker
notations.

This module loads ``data/ticker_renames.csv`` and turns each row into a
matching pair of ``ChangeEvent`` records — one ``removed`` for the old
ticker, one ``added`` for the new ticker — both dated to the rename
day. The reconciliation logic gracefully no-ops events that clash with
existing roster state, so spurious entries here cause warnings rather
than corruption.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from ._wiki import ChangeEvent

log = logging.getLogger(__name__)


def load_renames(path: Path) -> list[ChangeEvent]:
    """Read a renames CSV and return a flat list of paired events."""
    if not path.exists():
        log.warning("Renames CSV not found at %s; proceeding without renames.", path)
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
            out.append(ChangeEvent(
                date=date, action="removed",
                ticker=old, name=None,
                reason=f"rename → {new}: {reason or ''}".rstrip(": "),
            ))
            out.append(ChangeEvent(
                date=date, action="added",
                ticker=new, name=None,
                reason=f"rename ← {old}: {reason or ''}".rstrip(": "),
            ))
    log.info("Loaded %d rename events from %s", len(out), path)
    return out


def load_manual_events(path: Path) -> list[ChangeEvent]:
    """Load explicit add/remove events that close known upstream data gaps.

    Used for cases where neither the seed nor the Wikipedia changes
    table captures a real index event (e.g. the GE removal on
    2018-06-26 which the upstream seed dataset omits).
    """
    if not path.exists():
        log.warning("Manual events CSV not found at %s; proceeding without overrides.", path)
        return []
    out: list[ChangeEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            date = (row.get("date") or "").strip()
            action = (row.get("action") or "").strip().lower()
            ticker = (row.get("ticker") or "").strip().upper()
            name = (row.get("name") or "").strip() or None
            reason = (row.get("reason") or "").strip() or None
            if not (date and action and ticker):
                continue
            if action not in {"added", "removed"}:
                log.warning("Skipping manual event with unknown action %r", action)
                continue
            out.append(ChangeEvent(
                date=date, action=action,
                ticker=ticker, name=name,
                reason=f"manual override: {reason or ''}".rstrip(": "),
            ))
    log.info("Loaded %d manual override events from %s", len(out), path)
    return out


__all__ = ["load_manual_events", "load_renames"]
