"""TEMPORARY diagnostic: where did the 'Selected changes' tables go?

The 2026-08-17 refresh found no changes table on any of the three pages.
This probe asks the MediaWiki API what happened: recent revision comments
(the edit that removed it should say so) and a full-text search for the
section title (it should surface the article it was split into).

    python -m scripts.probe_wiki
"""

from __future__ import annotations

import sys

import requests

from scripts._indices import SPECS
from scripts._wiki import USER_AGENT

API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": USER_AGENT}


def api(**params: object) -> dict:
    r = requests.get(API_URL, params={"format": "json", **params}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def recent_revisions(title: str, limit: int = 25) -> None:
    j = api(
        action="query",
        prop="revisions",
        titles=title,
        rvprop="timestamp|user|comment|size",
        rvlimit=limit,
    )
    for pageid, page in j["query"]["pages"].items():
        print(f"  revisions of {page.get('title')} (pageid {pageid}):")
        prev_size = None
        for rev in page.get("revisions", []):
            delta = "" if prev_size is None else f" ({rev['size'] - prev_size:+d})"
            prev_size = rev["size"]
            print(
                f"    {rev['timestamp']} size={rev['size']}{delta} {rev.get('user', '?')}: "
                f"{(rev.get('comment') or '')[:160]}"
            )


def search(term: str, limit: int = 10) -> None:
    j = api(action="query", list="search", srsearch=term, srlimit=limit)
    print(f"  search {term!r}:")
    for hit in j["query"]["search"]:
        print(f"    - {hit['title']} (size {hit['size']}, words {hit['wordcount']})")


def links_from(title: str) -> None:
    """Outgoing links whose title mentions changes/components — a split target."""
    j = api(action="query", prop="links", titles=title, pllimit="max")
    for page in j["query"]["pages"].values():
        hits = [
            link["title"]
            for link in page.get("links", [])
            if any(w in link["title"].lower() for w in ("change", "component", "constituent"))
        ]
        print(f"  candidate outgoing links: {hits}")


def main() -> int:
    for key, spec in SPECS.items():
        print(f"\n=== {key}: {spec.wiki_title} ===")
        try:
            recent_revisions(spec.wiki_title)
            links_from(spec.wiki_title)
        except Exception as exc:
            print(f"  FAILED: {exc!r}")

    print("\n=== searches ===")
    for term in (
        '"Selected changes to the list of S&P 500 components"',
        "insource:/Selected changes to the list/",
        "List of S&P 500 companies changes",
    ):
        try:
            search(term)
        except Exception as exc:
            print(f"  FAILED {term!r}: {exc!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
