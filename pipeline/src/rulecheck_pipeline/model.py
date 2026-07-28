from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceDoc:
    id: str
    prefix: str
    title: str
    version: str
    published: str
    url: str
    file: str
    heading_rules: list[str]
    strip_lines: list[str] = dataclasses.field(default_factory=list)
    sha256: str | None = None
    layout: bool = False


@dataclass
class Section:
    id: str
    doc_id: str
    parent_id: str | None
    number: str
    title: str
    body: str
    breadcrumb: str
    order: int


def dump_document(source: SourceDoc, sections: list[Section], path: Path) -> None:
    payload = {
        "document": dataclasses.asdict(source),
        "sections": [dataclasses.asdict(s) for s in sections],
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def load_document(path: Path) -> tuple[SourceDoc, list[Section]]:
    payload = json.loads(Path(path).read_text())
    return (
        SourceDoc(**payload["document"]),
        [Section(**s) for s in payload["sections"]],
    )
