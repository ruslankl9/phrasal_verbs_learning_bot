#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dump all pages from Wiktionary category "English phrasal verbs" (with subcategories) to CSV.

Usage:
  python fetch_wikt_phrasals.py --out phrasal_verbs.csv
  python fetch_wikt_phrasals.py --root "Category:English phrasal verbs" --out out.csv --delay 0.1

Requires:
  pip install requests

Notes:
- Traverses subcategories recursively (BFS).
- Fetches only namespace=0 (main/article pages).
- Adds category_path column for traceability.
"""

import argparse
import csv
import time
import typing as T
from collections import deque
from dataclasses import dataclass
from urllib.parse import quote

import requests


API = "https://en.wiktionary.org/w/api.php"


@dataclass(frozen=True)
class Page:
    pageid: int
    title: str
    url: str
    category_path: str


class WikiClient:
    def __init__(self, api_url: str = API, delay: float = 0.1, retries: int = 4, timeout: int = 30):
        self.api_url = api_url
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "phrasal-verbs-crawler/1.0 (contact: you@example.com)"
        })

    def _get(self, params: dict) -> dict:
        """GET with basic retries and backoff."""
        last_err = None
        for attempt in range(self.retries):
            try:
                resp = self.session.get(self.api_url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    raise requests.HTTPError(data["error"])
                return data
            except Exception as e:
                last_err = e
                sleep = self.delay * (2 ** attempt)
                time.sleep(sleep)
        raise RuntimeError(f"API request failed after {self.retries} attempts: {last_err}")

    def list_category_members(
        self,
        category_title: str,
        cmtype: str,
        cmnamespace: T.Optional[int] = None,
        limit: int = 500,
    ) -> T.Iterable[dict]:
        """
        Generator over categorymembers (handles pagination).
        cmtype: "page" | "subcat" | "file" (we use page/subcat)
        cmnamespace: 0 for articles, 14 for categories, or None
        """
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_title,
            "cmtype": cmtype,
            "cmlimit": str(limit),
            "format": "json",
        }
        if cmnamespace is not None:
            params["cmnamespace"] = str(cmnamespace)

        cont = None
        while True:
            if cont:
                params["cmcontinue"] = cont
            data = self._get(params)
            members = data.get("query", {}).get("categorymembers", [])
            for m in members:
                yield m
            cont = data.get("continue", {}).get("cmcontinue")
            if not cont:
                break
            time.sleep(self.delay)

    @staticmethod
    def title_to_url(title: str) -> str:
        # MediaWiki page URL
        return f"https://en.wiktionary.org/wiki/{quote(title.replace(' ', '_'))}"


def crawl_phrasal_verbs(
    client: WikiClient,
    root_category: str = "Category:English phrasal_verbs",
    include_subcats: bool = True,
) -> T.List[Page]:
    """
    Traverse category graph (BFS) and collect all article pages (ns=0).
    Returns list[Page] with unique pageids.
    """
    # Normalize root title (Wiki uses underscores in category titles)
    root = root_category.replace(" ", "_")
    visited_cats: set[str] = set()
    pages_seen: set[int] = set()
    out: list[Page] = []

    queue = deque([(root, [root])])  # (category_title, path)

    while queue:
        cat_title, path = queue.popleft()
        if cat_title in visited_cats:
            continue
        visited_cats.add(cat_title)

        # 1) Articles (namespace=0)
        for m in client.list_category_members(cat_title, cmtype="page", cmnamespace=0):
            pid = m["pageid"]
            if pid in pages_seen:
                continue
            pages_seen.add(pid)
            title = m["title"]
            url = client.title_to_url(title)
            category_path = " > ".join(p.replace("_", " ") for p in path)
            out.append(Page(pageid=pid, title=title, url=url, category_path=category_path))

        if not include_subcats:
            continue

        # 2) Subcategories (namespace=14)
        subcats = []
        for m in client.list_category_members(cat_title, cmtype="subcat", cmnamespace=14):
            subcats.append(m["title"].replace(" ", "_"))

        # Push subcategories to queue
        for subcat in sorted(set(subcats)):
            if subcat not in visited_cats:
                queue.append((subcat, path + [subcat]))

    return out


def write_csv(rows: T.List[Page], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "pageid", "url", "category_path"])
        for p in sorted(rows, key=lambda x: (x.title.lower(), x.pageid)):
            w.writerow([p.title, p.pageid, p.url, p.category_path])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="Category:English phrasal verbs",
                    help='Root category title (default: "Category:English phrasal verbs")')
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--no-subcats", action="store_true", help="Do NOT traverse subcategories")
    ap.add_argument("--delay", type=float, default=0.1, help="Base delay between requests (seconds)")
    ap.add_argument("--retries", type=int, default=4, help="Retries per API call")
    ap.add_argument("--timeout", type=int, default=30, help="HTTP timeout per request (seconds)")
    args = ap.parse_args()

    client = WikiClient(delay=args.delay, retries=args.retries, timeout=args.timeout)
    rows = crawl_phrasal_verbs(
        client,
        root_category=args.root,
        include_subcats=not args.no_subcats,
    )
    write_csv(rows, args.out)
    print(f"OK: {len(rows)} pages written to {args.out}")


if __name__ == "__main__":
    main()
