"""TEMPORARY diagnostic: dump the table structure of the index wiki pages.

Run from CI when the build cannot find a table it expects. Prints, per page,
every section heading and every table's id / class / size / header text, so we
can see how the article was restructured.

    python -m scripts.probe_wiki
"""

from __future__ import annotations

import sys

from bs4 import BeautifulSoup

from scripts._indices import SPECS
from scripts._wiki import fetch_html


def probe(url: str) -> None:
    soup = BeautifulSoup(fetch_html(url), "lxml")

    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"])]
    print(f"  headings: {headings}")

    for i, table in enumerate(soup.find_all("table")):
        rows = table.find_all("tr")
        header = " | ".join(
            c.get_text(" ", strip=True)[:22] for row in rows[:2] for c in row.find_all(["th", "td"])
        )
        first = (
            " | ".join(c.get_text(" ", strip=True)[:22] for c in rows[2].find_all(["td", "th"]))
            if len(rows) > 2
            else ""
        )
        print(f"  [{i}] id={table.get('id')!r} class={table.get('class')} rows={len(rows)}")
        print(f"      header: {header[:400]}")
        print(f"      row2  : {first[:400]}")


def main() -> int:
    for key, spec in SPECS.items():
        print(f"\n=== {key}: {spec.wiki_url} ===")
        try:
            probe(spec.wiki_url)
        except Exception as exc:
            print(f"  FAILED: {exc!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
