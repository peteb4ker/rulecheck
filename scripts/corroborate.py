#!/usr/bin/env python3
"""Find every section that talks about a given set of terms.

A reviewer checking one entry keeps running into claims the entry's own
section does not support. The question is then whether the corpus supports
the claim somewhere else, or whether the author invented it. In the pilot
review of the game rules that question came up in about a third of the
entries, and each one was answered with a fresh grep.

Grep is the wrong tool for it. It matches the exact string, so a search for
"damage counter" misses "damage counters", and a search for "evolve" misses
"evolving". This stems every word first, using the same stemmer the lexicon
uses, so all the inflections of a word count as one.

Searches two places at once, and the difference matters to a reviewer:

  source    the parsed rulebook text. A claim found here is in the source
            documents somewhere, even if not in the section under review.
  authored  our own entries. A claim found only here is one we wrote and
            nothing in the source backs up, which is what INVENTION means.

Needs the full parse artifact for the source half, so run `just parse`
first. Without it the source half is skipped and only our own entries are
searched, which the output says plainly.

Usage:  python3 scripts/corroborate.py "discard pile face up"
        python3 scripts/corroborate.py --any "mulligan"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline" / "src"))
from rulecheck_pipeline.lexicon import stem, tokenize  # noqa: E402


def entry_text(entry: dict) -> str:
    """Every free-text string in an entry, flattened."""
    out: list[str] = []

    def walk(value):
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key not in ("archetype", "tier", "review", "see_also"):
                    walk(item)

    walk(entry)
    return " ".join(out)


def build_index(root: Path) -> tuple[dict[str, dict[str, str]], bool]:
    """Section id to {source: text, authored: text}. Also whether source was found."""
    index: dict[str, dict[str, str]] = {}

    full_dir = root / "build" / "content"
    have_source = full_dir.is_dir()
    if have_source:
        for path in sorted(full_dir.glob("*.json")):
            for section in json.loads(path.read_text())["sections"]:
                if section.get("body"):
                    index.setdefault(section["id"], {})["source"] = section["body"]

    for path in sorted((root / "rewrites").glob("*.json")):
        for sid, entry in json.loads(path.read_text()).items():
            if "skip" in entry:
                continue
            index.setdefault(sid, {})["authored"] = entry_text(entry)

    return index, have_source


def search(index: dict, terms: list[str], match_all: bool = True) -> list[dict]:
    wanted = {stem(t) for t in terms}
    hits = []
    for sid, texts in index.items():
        row = {"section": sid}
        for kind in ("source", "authored"):
            found = {w for w in (stem(t) for t in tokenize(texts.get(kind, "")))
                     if w in wanted}
            row[kind] = found
        every = row["source"] | row["authored"]
        if not every:
            continue
        if match_all and every != wanted:
            continue
        row["score"] = len(every)
        hits.append(row)
    return sorted(hits, key=lambda h: (-h["score"], h["section"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="words to look for, in quotes")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--any", action="store_true",
                    help="match a section holding any of the words (default: all)")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    terms = tokenize(args.query)
    if not terms:
        print("nothing to search for", file=sys.stderr)
        return 2

    index, have_source = build_index(args.root)
    if not have_source:
        print("note: no build/content, so only our own entries were searched. "
              "Run `just parse` to search the source text too.\n", file=sys.stderr)

    hits = search(index, terms, match_all=not args.any)
    print(f"searching for {terms} ({'all' if not args.any else 'any'})")
    print(f"{len(hits)} section(s) match\n")

    wanted = {stem(t) for t in terms}
    for hit in hits[:args.limit]:
        where = []
        if hit["source"]:
            where.append("source")
        if hit["authored"]:
            where.append("ours")
        # What the source lacks is the useful part. A word our entry uses and
        # the rulebook never does is the claim to go and check.
        only_ours = hit["authored"] - hit["source"]
        note = f"   ours only: {sorted(only_ours)}" if only_ours else ""
        missing = wanted - (hit["source"] | hit["authored"])
        if missing:
            note += f"   absent: {sorted(missing)}"
        print(f"  [{'+'.join(where):14s}] {hit['section']}{note}")

    if len(hits) > args.limit:
        print(f"  ... and {len(hits) - args.limit} more")

    if have_source and not any(h["source"] for h in hits):
        print("\nNo section of the source documents holds all these words. "
              "If an entry asserts this, nothing in the rulebooks backs it up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
