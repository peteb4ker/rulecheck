#!/usr/bin/env python3
"""Buddy validator for the fidelity-review skill.

A skill produces judgement; this script proves the state that judgement
claims to have produced. It answers, deterministically:

  1. Does every shipped entry have a recorded review verdict?
  2. Is any verdict STALE — recorded against an older version of the entry?
     (This is the load-bearing check: without it, editing an entry after
     review silently launders unreviewed content through a passing gate.)
  3. Are there unresolved high-severity findings?
  4. Are there orphan verdicts for entries that no longer exist?

Skipped entries need no review — they ship nothing.

Usage: check_fidelity_review.py [--root PATH] [--strict]
       --strict also fails on missing verdicts (release gate); by default
       missing verdicts are reported as warnings so authoring can proceed
       document by document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

VALID_VERDICTS = {"clean", "findings"}
VALID_CLASSES = {"DRIFT", "OMISSION", "INVENTION"}
VALID_SEVERITIES = {"high", "low"}


def entry_hash(entry: dict) -> str:
    """Stable hash of an entry: canonical JSON, sorted keys, no whitespace drift."""
    canonical = json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_json_dir(path: Path) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    if not path.is_dir():
        return merged
    for file in sorted(path.glob("*.json")):
        merged.update(json.loads(file.read_text()))
    return merged


def check(root: Path, strict: bool = False) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    entries = load_json_dir(root / "rewrites")
    verdicts = load_json_dir(root / "validation")
    shipped = {sid: e for sid, e in entries.items() if "skip" not in e}

    for sid in sorted(set(verdicts) - set(entries)):
        errors.append(f"{sid}: verdict for an entry that does not exist")

    for sid in sorted(set(verdicts) & set(entries)):
        if "skip" in entries[sid]:
            errors.append(f"{sid}: verdict recorded for a skipped entry")

    for sid, entry in sorted(shipped.items()):
        record = verdicts.get(sid)
        if record is None:
            message = f"{sid}: no fidelity verdict recorded"
            (errors if strict else warnings).append(message)
            continue

        recorded_hash = record.get("entry_sha256")
        actual_hash = entry_hash(entry)
        if recorded_hash != actual_hash:
            errors.append(
                f"{sid}: verdict is STALE — entry changed since review "
                f"(recorded {str(recorded_hash)[:12]}…, now {actual_hash[:12]}…)"
            )

        verdict = record.get("verdict")
        if verdict not in VALID_VERDICTS:
            errors.append(f"{sid}: verdict must be one of {sorted(VALID_VERDICTS)}")

        findings = record.get("findings", [])
        if not isinstance(findings, list):
            errors.append(f"{sid}: findings must be a list")
            continue
        if verdict == "clean" and findings:
            errors.append(f"{sid}: verdict 'clean' but findings recorded")
        if verdict == "findings" and not findings:
            errors.append(f"{sid}: verdict 'findings' but none recorded")

        for i, finding in enumerate(findings):
            if not isinstance(finding, dict):
                errors.append(f"{sid}: findings[{i}] must be an object")
                continue
            if finding.get("class") not in VALID_CLASSES:
                errors.append(f"{sid}: findings[{i}] class must be one of {sorted(VALID_CLASSES)}")
            if finding.get("severity") not in VALID_SEVERITIES:
                errors.append(f"{sid}: findings[{i}] severity must be high or low")
            if not str(finding.get("note", "")).strip():
                errors.append(f"{sid}: findings[{i}] needs a note")
            if finding.get("severity") == "high" and not finding.get("resolved"):
                errors.append(f"{sid}: unresolved high-severity finding — {finding.get('note', '')}")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_fidelity_review")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true",
                        help="fail on missing verdicts (release gate)")
    args = parser.parse_args(argv)

    errors, warnings = check(args.root.resolve(), strict=args.strict)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"FIDELITY FAIL: {e}", file=sys.stderr)

    if errors:
        return 1
    entries = load_json_dir(args.root / "rewrites")
    shipped = sum(1 for e in entries.values() if "skip" not in e)
    reviewed = shipped - len(warnings)
    print(f"fidelity review OK ({reviewed}/{shipped} entries reviewed"
          + (f", {len(warnings)} pending)" if warnings else ")"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
