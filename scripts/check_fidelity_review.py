#!/usr/bin/env python3
"""Buddy validator for the fidelity-review skill.

A skill produces judgement; this script proves the state that judgement
claims to have produced. It answers, deterministically:

  1. Does every shipped entry have a recorded review verdict?
  2. Is any verdict STALE — recorded against an older version of the entry?
     (This is the load-bearing check: without it, editing an entry after
     review silently launders unreviewed content through a passing gate.)
  3. Are there open high-severity findings nobody has taken?
  4. Are there orphan verdicts for entries that no longer exist?

Skipped entries need no review — they ship nothing.

A high-severity finding has two ways to clear the review gate, and the
difference matters. `resolved` means the entry was corrected. `acknowledged`
with an `owner` means the reviewer is handing the defect to someone else and
is not going to touch the content.

That second state exists because the first one, alone, quietly destroys the
independence the review is for. A reviewer who finds a serious problem and
must show a green gate has only one move left: fix the entry, then sign off
on its own writing. The reviewer reports; the author fixes. An acknowledged
finding still blocks a release, because handing a defect over does not make
it go away.

Usage: check_fidelity_review.py [--root PATH] [--strict] [--doc NAME]
       --strict fails on missing verdicts and on acknowledged-but-unfixed
       findings (release gate); by default those are warnings so review can
       proceed document by document.
       --doc scopes everything to one rewrites file, so reviewing one
       document does not print a pending line for every entry in the others.
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


def load_json_dir(path: Path, doc: str | None = None) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    if not path.is_dir():
        return merged
    for file in sorted(path.glob("*.json")):
        if doc is not None and file.stem != doc:
            continue
        merged.update(json.loads(file.read_text()))
    return merged


def check(root: Path, strict: bool = False,
          doc: str | None = None) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    if doc is not None and not (root / "rewrites" / f"{doc}.json").is_file():
        # Silence is the danger here: an unmatched filter would review an
        # empty set and report a clean pass over nothing at all.
        available = sorted(p.stem for p in (root / "rewrites").glob("*.json"))
        return ([f"no such document {doc!r} — rewrites holds {available}"], [])

    entries = load_json_dir(root / "rewrites", doc)
    verdicts = load_json_dir(root / "validation", doc)
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

            resolved = bool(finding.get("resolved"))
            acknowledged = bool(finding.get("acknowledged"))
            note = finding.get("note", "")

            if resolved and acknowledged:
                errors.append(
                    f"{sid}: findings[{i}] is both resolved and acknowledged — "
                    f"either the entry was corrected or it was handed on, not both")
            elif acknowledged and not str(finding.get("owner", "")).strip():
                errors.append(
                    f"{sid}: findings[{i}] is acknowledged but needs an owner "
                    f"naming who picks it up")
            elif finding.get("severity") == "high" and not resolved:
                if acknowledged:
                    # Open, owned, and still a defect: fine mid-review, never
                    # fine to ship.
                    message = (f"{sid}: high-severity finding awaiting the author "
                               f"({finding.get('owner')}) — {note}")
                    (errors if strict else warnings).append(message)
                else:
                    errors.append(
                        f"{sid}: unresolved high-severity finding — {note}. "
                        f"Fix it and set resolved, or hand it on with "
                        f"acknowledged and an owner")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_fidelity_review")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true",
                        help="fail on missing verdicts and handed-off findings "
                             "(release gate)")
    parser.add_argument("--doc", help="scope to one rewrites file, by stem "
                                      "(e.g. --doc tcg-rules)")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    errors, warnings = check(root, strict=args.strict, doc=args.doc)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"FIDELITY FAIL: {e}", file=sys.stderr)

    if errors:
        return 1
    # Count what was reviewed directly. Deriving it as shipped minus warnings
    # was right only while every warning meant a missing verdict; a handed-off
    # finding is a warning on an entry that *was* reviewed, and would have
    # silently undercounted progress.
    entries = load_json_dir(root / "rewrites", args.doc)
    verdicts = load_json_dir(root / "validation", args.doc)
    shipped = {sid for sid, e in entries.items() if "skip" not in e}
    reviewed = len(shipped & set(verdicts))
    pending = len(shipped) - reviewed
    scope = f" [{args.doc}]" if args.doc else ""
    print(f"fidelity review OK{scope} ({reviewed}/{len(shipped)} entries reviewed"
          + (f", {pending} pending)" if pending else ")"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
