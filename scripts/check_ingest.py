#!/usr/bin/env python3
"""Buddy validator for the ingest-document skill.

Proves that committed `content/*.json` is genuinely reproducible from the
source PDFs plus the manifest — i.e. that nobody hand-edited generated
content, and that a manifest change didn't silently reshape the corpus.

Re-parses every registered document and diffs the section structure (ids,
order, titles) against what is committed. Bodies are compared by hash so a
whitespace-level extraction difference is reported precisely rather than
dumping thousands of lines.

Requires the source PDFs present in sources/ (they are git-ignored — run
`just download` or place them manually first).

Usage: check_ingest.py [--root PATH] [--structure-only]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline" / "src"))

from benchside_pipeline.manifest import load_manifest  # noqa: E402
from benchside_pipeline.model import load_document  # noqa: E402
from benchside_pipeline.parse import parse_pdf  # noqa: E402


def body_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def check(root: Path, structure_only: bool = False) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "sources" / "sources.yaml"
    if not manifest_path.is_file():
        return [f"no manifest at {manifest_path}"]

    for source in load_manifest(manifest_path):
        content_path = root / "content" / f"{source.id}.json"
        pdf_path = root / "sources" / source.file

        if not content_path.is_file():
            errors.append(f"{source.id}: no committed content at {content_path}")
            continue
        if not pdf_path.is_file():
            errors.append(
                f"{source.id}: source PDF missing ({pdf_path.name}) — "
                "run `just download` or place it manually"
            )
            continue

        _, committed = load_document(content_path)
        reparsed = parse_pdf(pdf_path, source)

        committed_ids = [s.id for s in committed]
        reparsed_ids = [s.id for s in reparsed]
        if committed_ids != reparsed_ids:
            only_committed = sorted(set(committed_ids) - set(reparsed_ids))
            only_reparsed = sorted(set(reparsed_ids) - set(committed_ids))
            if only_committed:
                errors.append(
                    f"{source.id}: {len(only_committed)} section(s) in committed content "
                    f"but not in a fresh parse (e.g. {only_committed[:3]})"
                )
            if only_reparsed:
                errors.append(
                    f"{source.id}: {len(only_reparsed)} section(s) appear in a fresh parse "
                    f"but are not committed (e.g. {only_reparsed[:3]})"
                )
            if not only_committed and not only_reparsed:
                errors.append(f"{source.id}: section ORDER differs between committed and fresh parse")
            continue

        for old, new in zip(committed, reparsed):
            if old.title != new.title:
                errors.append(f"{old.id}: title differs (committed {old.title!r}, fresh {new.title!r})")
            if not structure_only and body_hash(old.body) != body_hash(new.body):
                errors.append(
                    f"{old.id}: body differs (committed {body_hash(old.body)}, "
                    f"fresh {body_hash(new.body)}) — content/ is generated; "
                    "re-run `just parse` instead of editing it"
                )

        print(f"{source.id}: {len(reparsed)} sections reproduce exactly")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_ingest")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--structure-only", action="store_true",
                        help="compare ids/order/titles but not body text")
    args = parser.parse_args(argv)

    errors = check(args.root.resolve(), structure_only=args.structure_only)
    for e in errors:
        print(f"INGEST FAIL: {e}", file=sys.stderr)
    if errors:
        return 1
    print("ingest OK — committed content reproduces from sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
