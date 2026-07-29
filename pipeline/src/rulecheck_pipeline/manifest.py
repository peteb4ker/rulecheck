from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from rulecheck_pipeline.model import SourceDoc

REQUIRED = ("id", "prefix", "title", "version", "published", "url", "file", "heading_rules")
OPTIONAL = ("strip_lines", "sha256", "layout")
KNOWN = set(REQUIRED) | set(OPTIONAL)


class ManifestError(Exception):
    pass


def _validate_heading_rules(doc_id: str, rules: object) -> None:
    """Heading rules are hand-tuned per document, so they get checked here
    rather than at first use. `classify_line` reads group(1) as the section
    number and group(2) as its title; a rule that does not compile, or that
    is short a group, otherwise surfaces mid-tuning as a bare re.error or
    IndexError against whichever PDF line happened to reach it first.
    """
    if not isinstance(rules, list) or not rules:
        raise ManifestError(f"{doc_id}: heading_rules must be a non-empty list")
    for i, rule in enumerate(rules):
        try:
            compiled = re.compile(rule)
        except (re.error, TypeError) as exc:
            raise ManifestError(
                f"{doc_id}: heading_rules[{i}] is not a valid regex: {rule!r} ({exc})"
            ) from exc
        if compiled.groups < 2:
            raise ManifestError(
                f"{doc_id}: heading_rules[{i}] needs 2 capture groups "
                f"(number, title), found {compiled.groups}: {rule!r}"
            )


def load_manifest(path: Path) -> list[SourceDoc]:
    data = yaml.safe_load(Path(path).read_text())
    entries = (data or {}).get("documents")
    if not entries:
        raise ManifestError("manifest has no documents")
    docs: list[SourceDoc] = []
    for entry in entries:
        missing = [k for k in REQUIRED if k not in entry]
        if missing:
            raise ManifestError(f"document entry missing fields: {', '.join(missing)}")
        unknown = sorted(set(entry) - KNOWN)
        if unknown:
            print(
                f"warning: {entry['id']}: unknown manifest keys ignored: {', '.join(unknown)}",
                file=sys.stderr,
            )
        _validate_heading_rules(entry["id"], entry["heading_rules"])
        fields = {k: entry[k] for k in REQUIRED}
        fields.update({k: entry[k] for k in OPTIONAL if k in entry})
        docs.append(SourceDoc(**fields))
    for field in ("id", "prefix"):
        values = [getattr(d, field) for d in docs]
        dupes = {v for v in values if values.count(v) > 1}
        if dupes:
            raise ManifestError(f"duplicate {field}: {', '.join(sorted(dupes))}")
    return docs
