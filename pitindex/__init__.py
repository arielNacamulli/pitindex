"""pitindex — point-in-time constituents of major equity indices.

Public API:

    >>> import pitindex
    >>> pitindex.get_constituents("2020-12-22")
    >>> pitindex.get_constituents_history("2015-01-01", "2015-12-31")
    >>> pitindex.update()  # refresh data from upstream sources
"""

from ._api import (
    StaleDataWarning,
    get_constituents,
    get_constituents_history,
    info,
    update,
)

__all__ = [
    "StaleDataWarning",
    "get_constituents",
    "get_constituents_history",
    "info",
    "update",
]

__version__ = "0.1.0"
