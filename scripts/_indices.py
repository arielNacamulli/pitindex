"""Build-time configuration for each physical index.

The coverage floors and sanity bands were measured empirically on
2026-07-12 by sampling quarterly Wikipedia page revisions — see
DESIGN.md §2 for the numbers and §3 for the event-source strategy.

On 2026-08-11 Wikipedia split the changes tables out of the
'List of S&P NNN companies' articles into 'Historical components of the
S&P NNN', so roster and events now come from two different pages
(``wiki_url`` and ``changes_url``).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class IndexSpec:
    key: str
    wiki_title: str  # MediaWiki page title (for the revisions API)
    wiki_url: str  # rendered page (current roster)
    changes_url: str  # rendered page carrying the add/remove changes table
    start_date: dt.date  # coverage floor
    seed_strategy: str  # 'fja05680' | 'wiki_revision'
    roster_band: tuple[int, int]  # accept parsed rosters only inside this band


SPECS: dict[str, IndexSpec] = {
    "sp500": IndexSpec(
        key="sp500",
        wiki_title="List of S&P 500 companies",
        wiki_url="https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        changes_url="https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500",
        start_date=dt.date(2005, 1, 3),
        seed_strategy="fja05680",
        roster_band=(490, 515),
    ),
    "sp400": IndexSpec(
        key="sp400",
        wiki_title="List of S&P 400 companies",
        wiki_url="https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        changes_url="https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_400",
        start_date=dt.date(2012, 1, 3),
        seed_strategy="wiki_revision",
        roster_band=(390, 410),
    ),
    "sp600": IndexSpec(
        key="sp600",
        wiki_title="List of S&P 600 companies",
        wiki_url="https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
        changes_url="https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_600",
        start_date=dt.date(2021, 4, 1),
        seed_strategy="wiki_revision",
        roster_band=(590, 615),
    ),
}

__all__ = ["SPECS", "IndexSpec"]
