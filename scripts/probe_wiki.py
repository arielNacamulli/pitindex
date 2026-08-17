"""TEMPORARY diagnostic: dump the new 'Historical components' articles.

On 2026-08-11 the 'Selected changes' tables were split out of the three
'List of S&P NNN companies' articles into 'Historical components of the
S&P NNN'. This probe dumps the table structure of the new articles so the
parser can be pointed at them.

    python -m scripts.probe_wiki
"""

from __future__ import annotations

import sys

from bs4 import BeautifulSoup

from scripts._wiki import fetch_html

PAGES = [
    "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500",
    "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_400",
    "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_600",
]


def probe(url: str) -> None:
    soup = BeautifulSoup(fetch_html(url), "lxml")
    print(f"  headings: {[h.get_text(' ', strip=True) for h in soup.find_all(['h2', 'h3'])]}")

    for i, table in enumerate(soup.find_all("table")):
        rows = table.find_all("tr")
        print(f"  [{i}] id={table.get('id')!r} class={table.get('class')} rows={len(rows)}")
        for j, row in enumerate(rows[:4]):
            cells = " | ".join(
                f"{c.name}:{c.get_text(' ', strip=True)[:26]}" for c in row.find_all(["th", "td"])
            )
            print(f"      r{j}: {cells[:420]}")
        for j, row in enumerate(rows[-2:]):
            cells = " | ".join(c.get_text(" ", strip=True)[:26] for c in row.find_all(["th", "td"]))
            print(f"      last{j}: {cells[:420]}")


def main() -> int:
    for url in PAGES:
        print(f"\n=== {url} ===")
        try:
            probe(url)
        except Exception as exc:
            print(f"  FAILED: {exc!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
