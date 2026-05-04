"""Lazy loaders for the shipped CSVs.

Data files are bundled inside the wheel under ``pitindex/data/``. We
read them via :mod:`importlib.resources` so the library works correctly
when installed from a wheel, an editable install, or a zip archive.

A user-level cache directory (``~/.cache/pitindex``) takes precedence
when present — that is how :func:`pitindex.update` injects fresher data
between releases.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

PACKAGE_DATA = "pitindex.data"
USER_CACHE = Path(os.environ.get("PITINDEX_CACHE_DIR") or Path.home() / ".cache" / "pitindex")


@dataclass(frozen=True)
class CurrentEntry:
    ticker: str
    name: str
    cik: str | None
    gics_sector: str | None
    gics_sub_industry: str | None
    date_added: dt.date | None


@dataclass(frozen=True)
class Event:
    date: dt.date
    action: str
    ticker: str
    name: str | None
    reason: str | None


@dataclass(frozen=True)
class SeedRow:
    effective_date: dt.date
    ticker: str


def _open_data(name: str):
    """Return an open text-mode file for ``name`` from cache or package."""
    cache_path = USER_CACHE / name
    if cache_path.exists():
        return cache_path.open("r", encoding="utf-8")
    return (resources.files(PACKAGE_DATA) / name).open("r", encoding="utf-8")


def load_seed() -> tuple[dt.date, set[str]]:
    with _open_data("sp500_seed.csv") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("Seed roster CSV is empty.")
    effective_date = dt.date.fromisoformat(rows[0]["effective_date"])
    tickers = {r["ticker"] for r in rows}
    return effective_date, tickers


def load_events() -> list[Event]:
    with _open_data("sp500_changes.csv") as f:
        rows = list(csv.DictReader(f))
    out: list[Event] = []
    for r in rows:
        out.append(
            Event(
                date=dt.date.fromisoformat(r["date"]),
                action=r["action"],
                ticker=r["ticker"],
                name=r["name"] or None,
                reason=r["reason"] or None,
            )
        )
    out.sort(key=lambda e: (e.date, 0 if e.action == "removed" else 1, e.ticker))
    return out


def load_current() -> list[CurrentEntry]:
    with _open_data("sp500_current.csv") as f:
        rows = list(csv.DictReader(f))
    out: list[CurrentEntry] = []
    for r in rows:
        d = r.get("date_added") or ""
        try:
            d_parsed = dt.date.fromisoformat(d) if d else None
        except ValueError:
            d_parsed = None
        out.append(
            CurrentEntry(
                ticker=r["ticker"],
                name=r["name"],
                cik=r["cik"] or None,
                gics_sector=r["gics_sector"] or None,
                gics_sub_industry=r["gics_sub_industry"] or None,
                date_added=d_parsed,
            )
        )
    return out


def load_metadata() -> dict:
    with _open_data("build_metadata.json") as f:
        return json.load(f)


__all__ = [
    "USER_CACHE",
    "CurrentEntry",
    "Event",
    "SeedRow",
    "load_current",
    "load_events",
    "load_metadata",
    "load_seed",
]
