"""Index registry shared by the runtime and the CLI.

The physical indices each have their own bundled data files
(``{key}_seed.csv``, ``{key}_changes.csv``, ``{key}_current.csv``).
``sp1500`` is a *virtual* composite: it is computed at query time as the
union of the three physical indices and has no files of its own (see
DESIGN.md §5).
"""

from __future__ import annotations

PHYSICAL_INDICES: tuple[str, ...] = ("sp500", "sp400", "sp600")
COMPOSITE_INDICES: dict[str, tuple[str, ...]] = {"sp1500": PHYSICAL_INDICES}
ALL_INDICES: tuple[str, ...] = (*PHYSICAL_INDICES, *COMPOSITE_INDICES)

DISPLAY_NAMES: dict[str, str] = {
    "sp500": "S&P 500",
    "sp400": "S&P 400 (MidCap)",
    "sp600": "S&P 600 (SmallCap)",
    "sp1500": "S&P 1500 (composite)",
}


def validate_index(index: str) -> str:
    key = index.strip().lower()
    if key not in ALL_INDICES:
        raise ValueError(f"Unknown index {index!r}. Supported: {', '.join(ALL_INDICES)}.")
    return key


__all__ = [
    "ALL_INDICES",
    "COMPOSITE_INDICES",
    "DISPLAY_NAMES",
    "PHYSICAL_INDICES",
    "validate_index",
]
