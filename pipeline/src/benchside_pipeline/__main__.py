from __future__ import annotations

import argparse
import sys
from pathlib import Path

from benchside_pipeline.build import build_db
from benchside_pipeline.download import download_doc
from benchside_pipeline.manifest import load_manifest
from benchside_pipeline.model import dump_document
from benchside_pipeline.parse import parse_pdf
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
    build_db(root / "content", db_path)
    print(f"built {db_path}")
    return 0


def cmd_verify(root: Path) -> int:
    errors = verify_db(root / "build" / "benchside.db")
    for e in errors:
        print(f"VERIFY FAIL: {e}", file=sys.stderr)
    if not errors:
        print("verify OK")
    return 1 if errors else 0


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
    parser.add_argument("command", choices=["parse", "build", "verify", "download", "all"])
    parser.add_argument("--root", type=Path, default=Path.cwd().parent,
                        help="repo root (default: parent of CWD, i.e. run from pipeline/)")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "parse":
        return cmd_parse(root)
    if args.command == "build":
        return cmd_build(root)
    if args.command == "verify":
        return cmd_verify(root)
    if args.command == "download":
        return cmd_download(root)
    rc = cmd_parse(root)
    if rc == 0:
        rc = cmd_build(root)
    if rc == 0:
        rc = cmd_verify(root)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
