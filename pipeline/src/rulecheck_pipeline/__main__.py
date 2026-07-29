from __future__ import annotations

import argparse
import sys
from pathlib import Path

from collections import Counter

from rulecheck_pipeline.build import build_db
from rulecheck_pipeline.content_check import check_rewrites
from rulecheck_pipeline.download import download_doc
from rulecheck_pipeline.manifest import load_manifest
from rulecheck_pipeline import shingles
from rulecheck_pipeline.model import dump_document, dump_index, load_document
from rulecheck_pipeline.parse import parse_pdf
from rulecheck_pipeline.rewrites import is_skip, load_rewrites
from rulecheck_pipeline.verify import verify_db


def cmd_parse(root: Path) -> int:
    content_dir = root / "content"
    content_dir.mkdir(exist_ok=True)
    sources = load_manifest(root / "sources" / "sources.yaml")

    # PDFs are git-ignored, so a fresh clone has the manifest and none of the
    # documents. Check every one up front: a reader should see instructions,
    # not a pdfplumber traceback from whichever file happened to be first.
    missing = [s for s in sources if not (root / "sources" / s.file).is_file()]
    if missing:
        for source in missing:
            print(
                f"ERROR: {source.id}: sources/{source.file} not found — "
                f"run 'just download' first (or download manually; see README)",
                file=sys.stderr,
            )
        return 1

    # Three artifacts per document, and the split is deliberate:
    #   build/content/<id>.json     full verbatim text — git-ignored
    #   content/<id>.json           structure and citations only — committed
    #   content/fingerprints/<id>.json  one-way fingerprints — committed
    # The repository never holds the prose; the checks that need it either run
    # against the local build artifact or against the fingerprints.
    full_dir = root / "build" / "content"
    for source in sources:
        pdf_path = root / "sources" / source.file
        sections = parse_pdf(pdf_path, source)
        dump_document(source, sections, full_dir / f"{source.id}.json")
        index = content_dir / f"{source.id}.json"
        dump_index(source, sections, index)
        shingles.dump(sections, content_dir / "fingerprints" / f"{source.id}.json")
        print(f"parsed {source.id}: {len(sections)} sections -> {index} (+ fingerprints)")
    return 0


def cmd_build(root: Path) -> int:
    db_path = root / "build" / "rulecheck.db"
    try:
        build_db(root / "content", db_path, rewrites_dir=root / "rewrites",
                 full_content_dir=root / "build" / "content")
    except ValueError as exc:
        # Refusing to ship is a real outcome, not a crash — say so plainly.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"built {db_path}")
    return 0


def cmd_verify(root: Path, release: bool = False) -> int:
    errors = verify_db(root / "build" / "rulecheck.db")
    if (root / "rewrites").is_dir():
        errors.extend(check_rewrites(root / "content", root / "rewrites", release=release,
                                     full_content_dir=root / "build" / "content"))
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
        leaves = [s.id for s in sections if s.body_chars]
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
    parser = argparse.ArgumentParser(prog="rulecheck_pipeline")
    parser.add_argument("command",
                        choices=["parse", "build", "verify", "download", "content-status", "all"])
    parser.add_argument("--root", type=Path, default=Path.cwd().parent,
                        help="repo root (default: parent of CWD, i.e. run from pipeline/)")
    parser.add_argument("--release", action="store_true",
                        help="verify: escalate coverage/review warnings to errors")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    # --root defaults to the parent of the CWD, which is right only when the
    # command is run from pipeline/. Get it wrong and the commands used to
    # mkdir content/ and build/ into a stranger's directory before failing on
    # a FileNotFoundError. The committed manifest is the marker for "this is
    # the repository", so check it once, up front, for every command.
    manifest = root / "sources" / "sources.yaml"
    if not manifest.is_file():
        print(
            f"ERROR: --root {root} is not the repository root: "
            f"sources/sources.yaml not found there.\n"
            f"  Run from pipeline/ (--root defaults to its parent), "
            f"or pass --root <path to the repo>.",
            file=sys.stderr,
        )
        return 2

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
