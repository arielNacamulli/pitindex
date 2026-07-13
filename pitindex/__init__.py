"""pitindex — point-in-time constituents of major equity indices.

Public API:

    >>> import pitindex
    >>> pitindex.get_constituents("2020-12-22")                  # S&P 500
    >>> pitindex.get_constituents("2023-06-30", index="sp400")   # S&P 400
    >>> pitindex.get_constituents("2023-06-30", index="sp1500")  # composite
    >>> pitindex.get_constituents_history("2015-01-01", "2015-12-31")
    >>> pitindex.update()  # refresh data from upstream sources
"""

from ._api import (
    PitIndex,
    StaleDataWarning,
    get_constituents,
    get_constituents_history,
    info,
    update,
)
from ._registry import ALL_INDICES, PHYSICAL_INDICES

__all__ = [
    "ALL_INDICES",
    "PHYSICAL_INDICES",
    "PitIndex",
    "StaleDataWarning",
    "get_constituents",
    "get_constituents_history",
    "info",
    "update",
]

__version__ = "0.2.1"
