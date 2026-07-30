#!/usr/bin/env python3
"""Independently check the lexicon against the authored corpus.

The buddy script for the build-lexicon skill. An agent classifying vocabulary
can invent a term that reads plausibly and appears nowhere, or miss a term that
appears two hundred times. Neither is visible by reading the lexicon, so this
checks both against the text and reports coverage as a number rather than a
feeling.

Three questions:

  1. Does every lexicon term actually occur in the corpus?
     Catches invented vocabulary.
  2. Is every recurring corpus term either classified or explicitly declined?
     Catches omissions, which is the failure that prompted this work.
  3. How much of the corpus has been decided either way?
     Progress is classified plus declined, not classified alone. Declining
     ordinary English is the correct answer for much of any corpus, and a
     metric that ignores it rewards padding the lexicon with words that are
     not game vocabulary.

Usage:  python3 scripts/check_lexicon.py [--min-count N] [--root DIR]
Exit 0 when the lexicon agrees with the corpus, 1 when it does not.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline" / "src"))
from rulecheck_pipeline.lexicon import (  # noqa: E402
    extract, stem, stem_phrase, tokenize, validate)

# Ordinary English. Not domain vocabulary, so absence from the lexicon is
# correct rather than an omission.
STOPWORDS = set("""
a an the and or but if when then than that this these those it its is are was were be been
being do does did doing have has had having can cannot could may might must shall should
will would to of in on at by for with from into onto over under about as so such no not
only both each any all every other another same own more most less least few many much
you your they them their there here what which who whom whose how why where while during
before after until since between through against above below up down out off again once
i me my we us our he she him her his hers one two three four five first second next last
also just even still yet already always never sometimes often per via etc eg ie
""".split())


def load_corpus(root: Path) -> dict[str, list[str]]:
    """Every free-text string in the authored entries, per document."""
    def strings(entry):
        out = []
        def walk(v):
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, list):
                for i in v:
                    walk(i)
            elif isinstance(v, dict):
                for k, i in v.items():
                    if k not in ("archetype", "tier", "review", "see_also", "quotes"):
                        walk(i)
        walk(entry)
        return out

    corpus = {}
    for path in sorted((root / "rewrites").glob("*.json")):
        texts = []
        for sid, entry in json.loads(path.read_text()).items():
            if "skip" not in entry:
                texts.extend(strings(entry))
        corpus[path.stem] = texts
    return corpus


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--min-count", type=int, default=5,
                    help="a corpus term appearing at least this often must be "
                         "classified or declined (default 5)")
    args = ap.parse_args()

    # A directory, not a file: content/*.json is the parsed-document glob, and
    # a lexicon sitting in it gets loaded as a document and fails on a missing
    # "document" key. Splitting into files also lets batches be classified in
    # parallel without fighting over one file.
    lex_dir = args.root / "content" / "lexicon"
    files = sorted(lex_dir.glob("*.json")) if lex_dir.is_dir() else []
    if not files:
        print(f"ERROR: no lexicon files in {lex_dir}", file=sys.stderr)
        return 1

    terms, declined = [], {}
    for path in files:
        payload = json.loads(path.read_text())
        terms.extend(payload.get("terms", []))
        for d in payload.get("declined", []):
            declined[stem(d["term"])] = d

    problems = validate(terms)

    corpus = load_corpus(args.root)
    counts: collections.Counter = collections.Counter()
    for texts in corpus.values():
        for text in texts:
            counts.update(w.lower() for w in tokenize(text))

    by_stem: collections.Counter = collections.Counter()
    for word, n in counts.items():
        by_stem[stem(word)] += n

    # Phrases too. Without this a classified "damage counter" is invisible and
    # would be reported as a term that appears nowhere.
    texts = [t for group in corpus.values() for t in group]
    phrases = {c["stem"]: c["count"]
               for c in extract(texts, min_count=1, max_words=3) if c["words"] > 1}

    # 1. every lexicon term occurs
    for entry in terms:
        key = stem_phrase(entry["term"])
        if (by_stem.get(key, 0) or phrases.get(key, 0)) == 0:
            problems.append(
                f"{entry['term']}: classified but appears nowhere in the corpus")
        for variant in entry.get("variants", []):
            # A multi-word variant is a phrase, not a token, so it will never
            # appear in the single-word counts.
            seen = (counts.get(variant.lower(), 0)
                    or phrases.get(stem_phrase(variant), 0))
            if seen == 0:
                problems.append(
                    f"{entry['term']}: declared variant {variant!r} never occurs")

    # 2. every recurring corpus term is classified or declined
    known = {stem_phrase(e["term"]) for e in terms}
    for entry in terms:
        known.update(stem_phrase(v) for v in entry.get("variants", []))
    missing = []
    for key, n in by_stem.most_common():
        if n < args.min_count or key in known or key in declined:
            continue
        if key in STOPWORDS or any(stem(s) == key for s in STOPWORDS):
            continue
        missing.append((n, key))

    # 3. progress, split so declining is visibly productive
    is_stop = {k for k in by_stem
               if k in STOPWORDS or any(stem(s) == k for s in STOPWORDS)}
    domain = {k: n for k, n in by_stem.items() if k not in is_stop}
    domain_total = sum(domain.values())
    n_classified = sum(n for k, n in domain.items() if k in known)
    n_declined = sum(n for k, n in domain.items() if k in declined)
    undecided = {k: n for k, n in domain.items()
                 if k not in known and k not in declined}

    def pct(x):
        return (100 * x / domain_total) if domain_total else 0

    print(f"lexicon : {len(terms)} classified, {len(declined)} declined")
    print(f"corpus  : {len(domain):,} distinct non-stopword terms, "
          f"{domain_total:,} occurrences")
    print(f"decided : {pct(n_classified + n_declined):5.1f}%  "
          f"({n_classified + n_declined:,} occurrences)")
    print(f"  classified {pct(n_classified):5.1f}%   declined {pct(n_declined):5.1f}%")
    print(f"remaining: {len(undecided):,} terms undecided, "
          f"worth {pct(sum(undecided.values())):.1f}%")

    if missing:
        print(f"\nunclassified terms occurring {args.min_count}+ times "
              f"({len(missing)}):", file=sys.stderr)
        for n, key in missing[:40]:
            example = min((w for w in counts if stem(w) == key), key=len, default=key)
            print(f"  {n:5d}  {example}", file=sys.stderr)
        if len(missing) > 40:
            print(f"  ... and {len(missing) - 40} more", file=sys.stderr)
        print("\nClassify each one, or decline it with a reason.", file=sys.stderr)

    for p in problems:
        print(f"LEXICON FAIL: {p}", file=sys.stderr)

    if problems or missing:
        return 1
    print("lexicon OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
