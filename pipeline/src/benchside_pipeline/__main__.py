from __future__ import annotations

import argparse
import sys
from pathlib import Path

from collections import Counter

from benchside_pipeline.build import build_db
from benchside_pipeline.content_check import check_rewrites
from benchside_pipeline.download import download_doc
from benchside_pipeline.manifest import load_manifest
from benchside_pipeline.model import dump_document, load_document
from benchside_pipeline.parse import parse_pdf
from benchside_pipeline.rewrites import is_skip, load_rewrites
from benchside_pipeline.verify import verify_db


def cmd_parse(root: Path) -> int:
    content_dir = root / "content"
    content_dir.mkdir(exist_ok=True)
    for source in load_manifest(root / "sources" / "sources.yaml"):
        pdf_path = root / "sources" / source.file
        sections = parse_pdf(pdf_path, source)
        out = content_dir / f"{source.id}.json"
        dump_document(source, sections, out)
        print(f"parsed {source.id}: {len(sections)} sections -> {out}")
    return 0


def cmd_build(root: Path) -> int:
    db_path = root / "build" / "benchside.db"
    build_db(root / "content", db_path, rewrites_dir=root / "rewrites")
    print(f"built {db_path}")
    return 0


def cmd_verify(root: Path, release: bool = False) -> int:
    errors = verify_db(root / "build" / "benchside.db")
    if (root / "rewrites").is_dir():
        errors.extend(check_rewrites(root / "content", root / "rewrites", release=release))
    warnings = [e for e in errors if e.startswith("warning:")]
    errors = [e for e in errors if not e.startswith("warning:")]
    for w in warnings:
        print(w, file=sys.stderr)
    for e in errors:
        print(f"VERIFY FAIL: {e}", file=sys.stderr)
    if not errors:
        print(f"verify OK ({len(warnings)} warnings)" if warnings else "verify OK")
    return 1 if errors else 0


def cmd_content_status(root: Path) -> int:
    entries = load_rewrites(root / "rewrites") if (root / "rewrites").is_dir() else {}
    for path in sorted((root / "content").glob("*.json")):
        source, sections = load_document(path)
        leaves = [s.id for s in sections if s.body.strip()]
        covered = [sid for sid in leaves if sid in entries]
        authored = [sid for sid in covered if not is_skip(entries[sid])]
        skipped = [sid for sid in covered if is_skip(entries[sid])]
        archetypes = Counter(entries[sid]["archetype"] for sid in authored)
        reviewed = sum(1 for sid in authored if entries[sid].get("review") == "reviewed")
        pct = 100 * len(covered) // len(leaves) if leaves else 100
        mix = " ".join(f"{k}={v}" for k, v in sorted(archetypes.items())) or "-"
        skip_note = f" | skipped {len(skipped)}" if skipped else ""
        print(f"{source.id}: {len(covered)}/{len(leaves)} leaves ({pct}%) | {mix}{skip_note} | reviewed {reviewed}/{len(authored) or 1}")
    return 0


def cmd_download(root: Path) -> int:
    dest = root / "sources"
    changed = failures = 0
    for source in load_manifest(root / "sources" / "sources.yaml"):
        try:
            result = download_doc(source, dest)
        except OSError as exc:
            print(f"ERROR: {source.id}: download failed from {source.url}: {exc}",
                  file=sys.stderr)
            failures += 1
            continue
        if result.status == "ok":
            print(f"{source.id}: ok ({result.sha256[:12]}…)")
        elif result.status == "new":
            print(f"{source.id}: downloaded; no recorded hash. Add to sources.yaml:")
            print(f'  sha256: "{result.sha256}"')
        else:
            changed += 1
            print(
                f"WARNING: {source.id}: upstream document changed "
                f"(recorded {source.sha256}, fetched {result.sha256}).\n"
                f"  TPCi revised this document — re-ingest and cut an app release.",
                file=sys.stderr,
            )
    return 1 if (changed or failures) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="benchside_pipeline")
    parser.add_argument("command",
                        choices=["parse", "build", "verify", "download", "content-status", "all"])
    parser.add_argument("--root", type=Path, default=Path.cwd().parent,
                        help="repo root (default: parent of CWD, i.e. run from pipeline/)")
    parser.add_argument("--release", action="store_true",
                        help="verify: escalate coverage/review warnings to errors")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "parse":
        return cmd_parse(root)
    if args.command == "build":
        return cmd_build(root)
    if args.command == "verify":
        return cmd_verify(root, release=args.release)
    if args.command == "download":
        return cmd_download(root)
    if args.command == "content-status":
        return cmd_content_status(root)
    rc = cmd_parse(root)
    if rc == 0:
        rc = cmd_build(root)
    if rc == 0:
        rc = cmd_verify(root, release=args.release)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
