#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Filter only phrasal verbs from a Wiktionary pages CSV and split into batches.

Input CSV is the one produced earlier, with columns:
  title,pageid,url,category_path

Output:
  - <out_base>.all.csv            (one column: phrasal)
  - <out_base>.batch0001.csv      (same schema), size <= --batch-size
  - <out_base>.batch0002.csv
  - ...

Usage:
  python make_phrasal_batches.py --in phrasal_pages.csv --out-base phrasal_verbs --batch-size 1000
"""

import argparse
import csv
import os
import re
import unicodedata
from typing import Iterable, List, Tuple


# reasonably broad list of particles (adverbial particles typically used in PVs)
PARTICLES = {
    "up","down","out","in","on","off","over","under","away","back",
    "through","around","about","along","by","across","ahead","apart",
    "round","forward","together","aside","behind","alongside","upwards","downwards"
}

# common prepositions that often make 3-part PVs (put up with, look forward to, come up against, etc.)
PREPOSITIONS = {
    "with","to","for","at","from","of","on","about","over","into","onto","in","off","against","through","after","under","without","beyond","between","across","around","by","up","down"
}

# simple English-verb token (base form) heuristic: letters + optional apostrophe (rare), no digits
VERB_RE = r"[a-z][a-z']*"

# two-part:  verb + particle
PATTERN_2 = re.compile(rf"^{VERB_RE}\s+(?:{'|'.join(sorted(PARTICLES))})$", re.IGNORECASE)

# three-part: verb + particle + preposition  (e.g., "put up with", "look forward to")
PATTERN_3 = re.compile(
    rf"^{VERB_RE}\s+(?:{'|'.join(sorted(PARTICLES))})\s+(?:{'|'.join(sorted(PREPOSITIONS))})$",
    re.IGNORECASE
)

PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")  # strip trailing " (transitive)" etc.
WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    # normalize unicode, underscores->spaces, strip parentheses suffixes, collapse spaces, lowercase
    t = title.replace("_", " ")
    t = PAREN_RE.sub("", t)
    t = unicodedata.normalize("NFKC", t)
    t = WS_RE.sub(" ", t).strip()
    return t


def is_phrasal_verb(lemma: str) -> bool:
    """
    Heuristic filter:
      - must be 2 or 3 tokens
      - token1 looks like a verb (letters/apostrophe)
      - token2 is a particle; token3 (if present) is a preposition
      - all-lowercase preferred (we lowercase before checks)
    """
    s = lemma.lower()
    # quick reject: titles starting with uppercase (proper names) are rare PVs
    # (we already lowercased, so this is moot; but keep form-based checks below)
    if PATTERN_2.match(s) or PATTERN_3.match(s):
        return True
    # additionally allow a small set of common three-part PVs where middle token sometimes treated as particle/prep
    # (covered above already; keep function simple)
    return False


def read_titles(in_csv: str) -> Iterable[str]:
    with open(in_csv, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if "title" not in r.fieldnames:
            raise SystemExit("Input CSV must have a 'title' column")
        for row in r:
            yield row["title"]


def filter_phrasals(titles: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for t in titles:
        norm = normalize_title(t)
        # skip empty / very short / obvious non-lemma
        if not norm or " " not in norm:
            continue
        low = norm.lower()
        if low not in seen:
            seen.add(low)
            out.append(low)
    return out


def write_batches(lemmas: List[str], out_base: str, batch_size: int) -> Tuple[str, List[str]]:
    # 1) write ALL file
    all_path = f"{out_base}.all.csv"
    with open(all_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["phrasal"])
        for pv in lemmas:
            w.writerow([pv])

    # 2) write batches
    batch_paths: List[str] = []
    if batch_size <= 0:
        batch_size = len(lemmas) or 1

    total = len(lemmas)
    digits = max(4, len(str((total + batch_size - 1) // batch_size)))
    for i in range(0, total, batch_size):
        idx = i // batch_size + 1
        batch_path = f"{out_base}.batch{idx:0{digits}d}.csv"
        with open(batch_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["phrasal"])
            for pv in lemmas[i:i + batch_size]:
                w.writerow([pv])
        batch_paths.append(batch_path)

    return all_path, batch_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True, help="Input CSV with columns including 'title'")
    ap.add_argument("--out-base", required=True, help="Output files base name (without extension)")
    ap.add_argument("--batch-size", type=int, default=1000, help="Batch size (default: 1000)")
    args = ap.parse_args()

    titles = list(read_titles(args.in_csv))
    phrasals = filter_phrasals(titles)

    if not phrasals:
        print("No phrasal verbs found after filtering.")
        return

    # sort for stability
    phrasals = sorted(phrasals, key=lambda s: (s.split()[-1], s.split()[0], s))

    all_path, batch_paths = write_batches(phrasals, args.out_base, args.batch_size)
    print(f"OK: {len(phrasals)} phrasal verbs")
    print(f"All-in-one: {all_path}")
    for p in batch_paths:
        print(f"Batch: {p}")


if __name__ == "__main__":
    main()
