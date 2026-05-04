"""Public query API.

The runtime model is event-sourcing on a tiny event log:
  - Load the seed roster (a single date snapshot, ~500 tickers).
  - Load the change events (~1000-2000 events over 20 years).
  - To get the membership at any point in time T, walk events in order
    up to T, applying each one to a running set.

Even with a naive O(N) walk per query this is < 1 ms — there is no
need for a more sophisticated index for v1.

Metadata enrichment (name, CIK, GICS sector) comes from the current
Wikipedia roster snapshot for tickers that are still members today; for
tickers that have since left the index, the only metadata we have is
whatever the change-events table preserved (typically the company name).
"""

from __future__ import annotations

import datetime as dt
import functools
import logging
import os
import warnings
from collections.abc import Iterable

import pandas as pd

from . import _loader

log = logging.getLogger(__name__)

DateLike = str | dt.date | dt.datetime

_OUTPUT_COLUMNS = ["ticker", "name", "cik", "gics_sector", "gics_sub_industry"]
_HISTORY_COLUMNS = ["as_of", *_OUTPUT_COLUMNS]

# Default freshness budget: a week for the upstream cron to run plus a
# week of grace before nagging the user. Override with the env var.
_DEFAULT_STALE_DAYS = 14
_STALE_DAYS = int(os.environ.get("PITINDEX_STALE_DAYS", _DEFAULT_STALE_DAYS))


class StaleDataWarning(UserWarning):
    """The bundled dataset is older than the configured freshness budget."""


def _coerce_date(d: DateLike) -> dt.date:
    if isinstance(d, dt.datetime):
        return d.date()
    if isinstance(d, dt.date):
        return d
    if isinstance(d, str):
        return dt.date.fromisoformat(d)
    raise TypeError(f"Unsupported date type: {type(d).__name__}")


@functools.lru_cache(maxsize=1)
def _index() -> _Index:
    return _Index.load()


class _Index:
    __slots__ = ("seed_date", "seed", "events", "current_by_ticker", "name_by_ticker", "metadata")

    def __init__(
        self,
        seed_date: dt.date,
        seed: set[str],
        events: list[_loader.Event],
        current_by_ticker: dict[str, _loader.CurrentEntry],
        name_by_ticker: dict[str, str],
        metadata: dict,
    ):
        self.seed_date = seed_date
        self.seed = seed
        self.events = events
        self.current_by_ticker = current_by_ticker
        self.name_by_ticker = name_by_ticker
        self.metadata = metadata

    @classmethod
    def load(cls) -> _Index:
        seed_date, seed = _loader.load_seed()
        events = _loader.load_events()
        current = _loader.load_current()
        current_by_ticker = {c.ticker: c for c in current}
        # Best-effort name lookup: prefer current name, fall back to name
        # captured in a change event when the ticker has since left.
        name_by_ticker: dict[str, str] = {c.ticker: c.name for c in current}
        for e in events:
            if e.ticker not in name_by_ticker and e.name:
                name_by_ticker[e.ticker] = e.name
        metadata = _loader.load_metadata()
        _maybe_warn_stale(metadata)
        return cls(seed_date, seed, events, current_by_ticker, name_by_ticker, metadata)

    @property
    def coverage_start(self) -> dt.date:
        return self.seed_date

    @property
    def coverage_end(self) -> dt.date:
        return dt.date.fromisoformat(self.metadata.get("end_date") or self.seed_date.isoformat())

    def roster_at(self, as_of: dt.date) -> set[str]:
        if as_of < self.seed_date:
            raise ValueError(
                f"as_of={as_of.isoformat()} is before seed coverage "
                f"({self.seed_date.isoformat()}). pitindex does not extrapolate."
            )
        roster = set(self.seed)
        for ev in self.events:
            if ev.date > as_of:
                break
            if ev.action == "added":
                roster.add(ev.ticker)
            elif ev.action == "removed":
                roster.discard(ev.ticker)
        return roster

    def to_frame(self, as_of: dt.date, tickers: Iterable[str]) -> pd.DataFrame:
        rows = []
        for t in sorted(tickers):
            cur = self.current_by_ticker.get(t)
            rows.append({
                "ticker": t,
                "name": cur.name if cur else self.name_by_ticker.get(t),
                "cik": cur.cik if cur else None,
                "gics_sector": cur.gics_sector if cur else None,
                "gics_sub_industry": cur.gics_sub_industry if cur else None,
            })
        df = pd.DataFrame(rows, columns=_OUTPUT_COLUMNS)
        df.attrs["as_of"] = as_of.isoformat()
        df.attrs["build_timestamp_utc"] = self.metadata.get("build_timestamp_utc")
        return df


def _data_age_days(metadata: dict) -> int | None:
    raw = metadata.get("build_timestamp_utc")
    if not raw:
        return None
    try:
        built = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if built.tzinfo is None:
        built = built.replace(tzinfo=dt.timezone.utc)
    delta = dt.datetime.now(dt.timezone.utc) - built
    return max(delta.days, 0)


def _maybe_warn_stale(metadata: dict) -> None:
    if _STALE_DAYS <= 0:
        return  # opt-out via PITINDEX_STALE_DAYS=0
    age = _data_age_days(metadata)
    if age is None or age <= _STALE_DAYS:
        return
    warnings.warn(
        f"pitindex bundled data is {age} days old "
        f"(threshold {_STALE_DAYS}). Run `pip install -U pitindex` to "
        f"pick up the latest weekly refresh, or call `pitindex.update()` "
        f"to rebuild from upstream sources right now. Suppress this "
        f"warning with `PITINDEX_STALE_DAYS=0` or "
        f"`warnings.filterwarnings('ignore', category=pitindex.StaleDataWarning)`.",
        StaleDataWarning,
        stacklevel=4,
    )


# --- public API ------------------------------------------------------------

def get_constituents(as_of: DateLike) -> pd.DataFrame:
    """Return the S&P 500 constituents as of ``as_of`` (end-of-day UTC).

    Parameters
    ----------
    as_of
        A ``datetime.date``, ``datetime.datetime``, or ISO-format string
        (``YYYY-MM-DD``).

    Returns
    -------
    pd.DataFrame
        Columns: ``ticker, name, cik, gics_sector, gics_sub_industry``.
        ``cik`` and GICS fields are populated only for tickers that are
        still index members today; historical members carry ``None`` for
        those fields. ``as_of`` is exposed via ``df.attrs['as_of']``.
    """
    as_of_d = _coerce_date(as_of)
    idx = _index()
    if as_of_d > dt.date.today():
        raise ValueError(f"as_of={as_of_d.isoformat()} is in the future.")
    roster = idx.roster_at(as_of_d)
    return idx.to_frame(as_of_d, roster)


def get_constituents_history(start: DateLike, end: DateLike) -> pd.DataFrame:
    """Return one snapshot per *change date* in ``[start, end]``.

    The result is a sparse history: rows are emitted only on dates when
    the membership actually changed (plus the boundary ``start`` date).
    To obtain a *daily* history, iterate :func:`get_constituents` over
    your trading calendar — this avoids materializing the full Cartesian
    product when you only need it on specific days.

    Parameters
    ----------
    start, end
        Inclusive bounds (date / datetime / ISO string).

    Returns
    -------
    pd.DataFrame
        Columns: ``as_of, ticker, name, cik, gics_sector, gics_sub_industry``.
    """
    start_d = _coerce_date(start)
    end_d = _coerce_date(end)
    if end_d < start_d:
        raise ValueError(f"end {end_d} precedes start {start_d}")
    idx = _index()
    today = dt.date.today()
    if end_d > today:
        end_d = today

    # Snapshot at start, then again at each date when an event lands inside
    # the window.
    change_dates = sorted({ev.date for ev in idx.events
                           if start_d <= ev.date <= end_d})
    snapshot_dates = [start_d, *[d for d in change_dates if d != start_d]]

    frames = []
    for d in snapshot_dates:
        roster = idx.roster_at(d)
        snap = idx.to_frame(d, roster)
        snap.insert(0, "as_of", d.isoformat())
        frames.append(snap)
    if not frames:
        return pd.DataFrame(columns=_HISTORY_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def info() -> dict:
    """Return metadata about the bundled dataset (build time, sources, sizes).

    Includes ``data_age_days`` (None if the build timestamp is missing),
    ``stale_threshold_days`` (the configured freshness budget), and
    ``is_stale`` (whether the data has crossed the threshold).
    """
    idx = _index()
    out = dict(idx.metadata)
    age = _data_age_days(idx.metadata)
    out["data_age_days"] = age
    out["stale_threshold_days"] = _STALE_DAYS
    out["is_stale"] = (age is not None and _STALE_DAYS > 0 and age > _STALE_DAYS)
    return out


def update(*, force: bool = False) -> dict:
    """Refresh the local data cache from upstream sources.

    Runs the same build pipeline used to ship the package and writes the
    output to ``~/.cache/pitindex`` so that subsequent calls pick up the
    fresher data without reinstalling. Requires the ``[build]`` extra
    (``pip install pitindex[build]``).

    Parameters
    ----------
    force
        Refresh even if the cache was updated less than 24 hours ago.

    Returns
    -------
    dict
        The build metadata for the freshly-built dataset.
    """
    try:
        from scripts import build_dataset  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "pitindex.update() requires the build extras. "
            "Install with: pip install 'pitindex[build]'"
        ) from exc

    cache = _loader.USER_CACHE
    cache.mkdir(parents=True, exist_ok=True)
    metadata_path = cache / "build_metadata.json"
    if not force and metadata_path.exists():
        try:
            mtime = dt.datetime.fromtimestamp(metadata_path.stat().st_mtime)
            if (dt.datetime.now() - mtime) < dt.timedelta(hours=24):
                log.info("Cache is fresh (< 24h). Pass force=True to override.")
                with metadata_path.open() as f:
                    import json
                    return json.load(f)
        except OSError:
            pass

    # Redirect package data writes into the user cache for this run.
    original = build_dataset.PACKAGE_DATA
    build_dataset.PACKAGE_DATA = cache
    try:
        rc = build_dataset.main([])
    finally:
        build_dataset.PACKAGE_DATA = original
    if rc != 0:
        raise RuntimeError(f"update() build failed with exit code {rc}")
    _index.cache_clear()
    return info()


__all__ = [
    "get_constituents",
    "get_constituents_history",
    "info",
    "update",
]
