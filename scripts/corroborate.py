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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline" / "src"))
from rulecheck_pipeline.lexicon import stem, tokenize  # noqa: E402

# How far apart the words may sit and still count as one statement. A section
# can run to 100,000 characters, so words scattered the whole way down it share
# a section and nothing else. Roughly a long sentence or two.
DEFAULT_WINDOW = 40


def stems_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """Each word's stem and where it sits in the original text.

    Offsets are what let the output quote the sentence back, which is the
    difference between "this section mentions those words somewhere" and
    "here is the line that says it".
    """
    out = []
    for match in re.finditer(r"[A-Za-zÀ-ÿ]+", text):
        word = match.group()
        if len(word) > 1:
            out.append((stem(word.lower()), match.start(), match.end()))
    return out


def tightest_window(marks: list[tuple[str, int, int]],
                    wanted: set[str]) -> tuple[int, int, int] | None:
    """Smallest run of words holding every wanted stem.

    Returns (words spanned, start offset, end offset), or None if the text
    never holds all of them. Walks the text once, keeping the most recent
    position of each wanted word.
    """
    if not wanted:
        return None
    last: dict[str, int] = {}
    positions = [(i, s, a, b) for i, (s, a, b) in enumerate(marks) if s in wanted]
    best = None
    for i, s, a, b in positions:
        last[s] = i
        if len(last) < len(wanted):
            continue
        first_index = min(last.values())
        span = i - first_index + 1
        if best is None or span < best[0]:
            start = marks[first_index][1]
            best = (span, start, b)
    return best


def snippet(text: str, start: int, end: int, pad: int = 60) -> str:
    """The matching text with a little either side, on one line."""
    left = max(0, start - pad)
    right = min(len(text), end + pad)
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return prefix + " ".join(text[left:right].split()) + suffix


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


def search(index: dict, terms: list[str], match_all: bool = True,
           window: int | None = DEFAULT_WINDOW) -> list[dict]:
    """Sections holding the terms, closest together first.

    `window` is the most words the terms may span and still count. Pass None
    to match anywhere in the section, which is the older and much weaker
    behaviour: on a long section it reports a match for words that share
    nothing but the section itself.
    """
    wanted = {stem(t) for t in terms}
    hits = []
    for sid, texts in index.items():
        row = {"section": sid, "quote": None, "span": None}
        for kind in ("source", "authored"):
            text = texts.get(kind, "")
            marks = stems_with_offsets(text)
            row[kind] = {s for s, _, _ in marks if s in wanted}
            best = tightest_window(marks, wanted)
            if best and (window is None or best[0] <= window):
                span, start, end = best
                if row["span"] is None or span < row["span"]:
                    row["span"] = span
                    row["quote"] = snippet(text, start, end)
                    row["quote_from"] = kind
        every = row["source"] | row["authored"]
        if not every:
            continue
        if match_all:
            # Every word must appear, and close enough together to be one
            # statement rather than two unrelated mentions.
            if every != wanted or row["span"] is None:
                continue
        row["score"] = len(every)
        hits.append(row)
    # Tightest first: the section that says it in one sentence beats the one
    # that happens to use the same words a page apart.
    return sorted(hits, key=lambda h: (h["span"] if h["span"] is not None else 10**6,
                                       -h["score"], h["section"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    # Several words rather than one quoted string, because `just` splits its
    # arguments on whitespace and the quotes never reach this script.
    ap.add_argument("query", nargs="+", help="the words to look for")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--any", action="store_true",
                    help="match a section holding any of the words (default: all)")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                    help=f"how many words the terms may span (default "
                         f"{DEFAULT_WINDOW}, 0 for anywhere in the section)")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    terms = tokenize(" ".join(args.query))
    if not terms:
        print("nothing to search for", file=sys.stderr)
        return 2

    index, have_source = build_index(args.root)
    if not have_source:
        print("note: no build/content, so only our own entries were searched. "
              "Run `just parse` to search the source text too.\n", file=sys.stderr)

    window = None if args.window == 0 else args.window
    hits = search(index, terms, match_all=not args.any, window=window)
    scope = "all" if not args.any else "any"
    near = "anywhere in a section" if window is None else f"within {window} words"
    print(f"searching for {terms} ({scope}, {near})")
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
        if hit["quote"]:
            print(f"       {hit['quote_from']}: {hit['quote']}")

    if len(hits) > args.limit:
        print(f"  ... and {len(hits) - args.limit} more")

    if have_source and not any(h["source"] for h in hits):
        print("\nNo section of the source documents holds all these words. "
              "If an entry asserts this, nothing in the rulebooks backs it up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
