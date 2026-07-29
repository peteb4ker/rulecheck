from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from pathlib import Path


def _body_chars(body: str) -> int:
    """Whitespace-normalized length. Coverage asks "does this section carry
    prose", and a body of blank lines does not."""
    return len(re.sub(r"\s+", " ", body).strip())


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
    breadcrumb: str
    order: int
    # Verbatim source text. Present in the full parse artifact under `build/`,
    # absent from the committed index — that asymmetry is the whole point of
    # keeping copyrighted prose out of the repository.
    body: str = ""
    # Length of the body that produced this entry. Survives into the index so
    # coverage still knows which sections carry prose, and so the build can
    # refuse to ship a section whose text it no longer has.
    body_chars: int = 0

    def __post_init__(self) -> None:
        # Covers Sections built with their body in hand. The parser appends
        # body text afterwards, so `_payload` recomputes at write time — both
        # are needed, neither alone is enough.
        if self.body and not self.body_chars:
            self.body_chars = _body_chars(self.body)

def _payload(source: SourceDoc, sections: list[Section], *, bodies: bool) -> dict:
    rows = []
    for section in sections:
        row = dataclasses.asdict(section)
        # Derived at write time, not construction: the parser appends body
        # text after building the Section, so anything computed earlier
        # would record zero for every section.
        if section.body:
            row["body_chars"] = _body_chars(section.body)
        if not bodies:
            row.pop("body")
        rows.append(row)
    return {"document": dataclasses.asdict(source), "sections": rows}


def _write(payload: dict, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def dump_document(source: SourceDoc, sections: list[Section], path: Path) -> None:
    """The full artifact, verbatim bodies included. Build output, never committed."""
    _write(_payload(source, sections, bodies=True), path)


def dump_index(source: SourceDoc, sections: list[Section], path: Path) -> None:
    """The committed record: structure, citations and body lengths, no prose.

    Everything here already ships inside the app — section numbers, titles and
    breadcrumbs are how a rule is cited — so committing it exposes nothing the
    App Store build does not.
    """
    _write(_payload(source, sections, bodies=False), path)


def load_document(path: Path) -> tuple[SourceDoc, list[Section]]:
    payload = json.loads(Path(path).read_text())
    return (
        SourceDoc(**payload["document"]),
        [Section(**s) for s in payload["sections"]],
    )


def has_bodies(sections: list[Section]) -> bool:
    """True when this artifact carries verbatim text — i.e. it is the full
    parse output rather than the committed index."""
    return any(s.body for s in sections)
