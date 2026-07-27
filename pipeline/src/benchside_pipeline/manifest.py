from __future__ import annotations

import sys
from pathlib import Path

import yaml

from benchside_pipeline.model import SourceDoc

REQUIRED = ("id", "prefix", "title", "version", "published", "url", "file", "heading_rules")
OPTIONAL = ("strip_lines", "sha256", "layout")
KNOWN = set(REQUIRED) | set(OPTIONAL)


class ManifestError(Exception):
    pass


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
        fields = {k: entry[k] for k in REQUIRED}
        fields.update({k: entry[k] for k in OPTIONAL if k in entry})
        docs.append(SourceDoc(**fields))
    for field in ("id", "prefix"):
        values = [getattr(d, field) for d in docs]
        dupes = {v for v in values if values.count(v) > 1}
        if dupes:
            raise ManifestError(f"duplicate {field}: {', '.join(sorted(dupes))}")
    return docs
