#!/usr/bin/env python3
"""Quantify how transformative the shipped content is.

Issue #7(b). The 12-token tripwire answers one question, yes or no: does any
entry reuse a run of source wording it did not declare? That is the floor. It
says nothing about how far above the floor we are, and "we have a tripwire and
it passes" is a weaker thing to show a lawyer than a distribution.

This measures three things and writes them where a reader can check them:

  Quote budget      declared quoted tokens against source tokens, per section
                    and corpus-wide. A section may sit inside the tripwire and
                    still quote half its source through declared quotes.

  Overlap profile   the longest shared token run per section, whether declared
                    or not. The tripwire fires at 12; this shows whether the
                    corpus sits at 3 or at 11.

  Compression       authored tokens against source tokens. Paraphrase that is
                    the same length as its source is a rewording; paraphrase
                    that is much shorter is a summary, which is the stronger
                    position.

Needs the full parse artifact, so run `just parse` first. Fingerprints cannot
answer these: measuring the longest shared run needs the tokens themselves.

Usage:  python3 scripts/transformation_report.py [--root DIR] [--json PATH]
Exit 1 if any section breaches a budget.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline" / "src"))
from rulecheck_pipeline.content_check import _text_fields, _tokens  # noqa: E402

# A section quoting more than this share of its source is leaning on the
# source rather than transforming it, even with every quote declared.
SECTION_QUOTE_BUDGET = 0.15
CORPUS_QUOTE_BUDGET = 0.05


def longest_shared_run(source: list[str], authored: list[str]) -> int:
    """Longest run of consecutive tokens appearing in both.

    Classic dynamic programming, one row at a time so a long section does not
    allocate a full matrix.
    """
    if not source or not authored:
        return 0
    previous = [0] * (len(authored) + 1)
    best = 0
    for s in source:
        current = [0] * (len(authored) + 1)
        for j, a in enumerate(authored, 1):
            if s == a:
                current[j] = previous[j - 1] + 1
                best = max(best, current[j])
        previous = current
    return best


def analyse(root: Path) -> dict:
    full_dir = root / "build" / "content"
    if not full_dir.is_dir():
        raise SystemExit(
            "no parse artifact at build/content — run `just parse` first. "
            "This report needs the source tokens; fingerprints cannot answer it."
        )

    sources: dict[str, str] = {}
    for path in sorted(full_dir.glob("*.json")):
        for section in json.loads(path.read_text())["sections"]:
            if section.get("body"):
                sources[section["id"]] = section["body"]

    entries: dict[str, dict] = {}
    for path in sorted((root / "rewrites").glob("*.json")):
        entries.update(json.loads(path.read_text()))

    rows = []
    for sid, entry in sorted(entries.items()):
        if "skip" in entry or sid not in sources:
            continue
        source_tokens = _tokens(sources[sid])
        if not source_tokens:
            continue
        authored_tokens = _tokens(" ".join(_text_fields(entry)))
        quoted = sum(len(_tokens(q)) for q in entry.get("quotes", []))
        rows.append({
            "section": sid,
            "source_tokens": len(source_tokens),
            "authored_tokens": len(authored_tokens),
            "quoted_tokens": quoted,
            "quote_share": quoted / len(source_tokens),
            "compression": len(authored_tokens) / len(source_tokens),
            "longest_shared_run": longest_shared_run(source_tokens, authored_tokens),
        })

    src_total = sum(r["source_tokens"] for r in rows)
    quoted_total = sum(r["quoted_tokens"] for r in rows)
    authored_total = sum(r["authored_tokens"] for r in rows)
    runs = sorted(r["longest_shared_run"] for r in rows)

    def pctile(p: float) -> int:
        return runs[min(int(len(runs) * p), len(runs) - 1)] if runs else 0

    return {
        "sections": len(rows),
        "source_tokens": src_total,
        "authored_tokens": authored_total,
        "quoted_tokens": quoted_total,
        "corpus_quote_share": quoted_total / src_total if src_total else 0,
        "corpus_compression": authored_total / src_total if src_total else 0,
        "longest_run_median": pctile(0.5),
        "longest_run_p95": pctile(0.95),
        "longest_run_max": max(runs) if runs else 0,
        "over_section_budget": [r["section"] for r in rows
                                if r["quote_share"] > SECTION_QUOTE_BUDGET],
        "rows": sorted(rows, key=lambda r: -r["longest_shared_run"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--json", type=Path, help="also write the full report here")
    args = ap.parse_args()

    report = analyse(args.root)

    print(f"sections measured : {report['sections']}")
    print(f"source tokens     : {report['source_tokens']:,}")
    print(f"authored tokens   : {report['authored_tokens']:,}  "
          f"({report['corpus_compression']:.0%} of source)")
    print(f"declared quotes   : {report['quoted_tokens']:,} tokens  "
          f"({report['corpus_quote_share']:.2%} of source, "
          f"budget {CORPUS_QUOTE_BUDGET:.0%})")
    print()
    print("longest shared token run per section (the tripwire fires at 12):")
    print(f"  median {report['longest_run_median']}   "
          f"95th {report['longest_run_p95']}   max {report['longest_run_max']}")
    print("  NOTE: the maximum is censored. The tripwire fails the build at 12,")
    print("  so nothing can exceed 11 and a maximum of 11 is evidence that the")
    print("  constraint binds, not that the content is transformative. Read the")
    print("  median and the 95th percentile instead.")

    worst = report["rows"][:5]
    if worst:
        print("\nsections closest to the tripwire:")
        for r in worst:
            print(f"  run {r['longest_shared_run']:3d}  "
                  f"quote {r['quote_share']:5.1%}  {r['section']}")

    problems = []
    if report["corpus_quote_share"] > CORPUS_QUOTE_BUDGET:
        problems.append(
            f"corpus quote share {report['corpus_quote_share']:.2%} exceeds "
            f"{CORPUS_QUOTE_BUDGET:.0%}")
    for sid in report["over_section_budget"]:
        problems.append(f"{sid}: quotes exceed {SECTION_QUOTE_BUDGET:.0%} of its source")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nfull report written to {args.json}")

    for p in problems:
        print(f"TRANSFORMATION FAIL: {p}", file=sys.stderr)
    if problems:
        return 1
    print("\ntransformation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
