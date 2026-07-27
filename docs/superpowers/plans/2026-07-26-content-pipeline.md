# Benchside Content Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python pipeline that turns official Pokemon TCG rules PDFs into a single verified SQLite+FTS5 database (`build/benchside.db`) that the Benchside iOS app will bundle.

**Architecture:** Four stages — ingest (sources.yaml manifest describing each PDF), parse (PDF → section tree → committed JSON in `content/`), build (JSON → SQLite with FTS5), verify (fail on empty sections, duplicate IDs, broken cross-references). Parsing is generic and driven by per-document heading regexes in the manifest, so new/revised documents are a manifest edit, not a code change.

**Tech Stack:** Python 3.12+, pdfplumber (PDF text extraction), PyYAML (manifest), sqlite3 (stdlib), pytest + reportlab (tests/fixture PDFs).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-26-benchside-design.md`
- Body text is **verbatim** from source documents (rewrite decision deferred to the Research Gate; pipeline is identical either way).
- Section IDs are stable, human-readable: `<prefix>-<number>` (e.g. `trh-5.2`).
- Source PDFs are **never committed** (`sources/*.pdf` git-ignored); `sources.yaml` and parsed `content/*.json` **are** committed.
- The built DB (`build/`) is a build product, git-ignored.
- FTS5 index over title + body; title weighted higher **at query time** via `bm25(sections_fts, 10.0, 1.0)`.
- All pipeline code lives under `pipeline/`; run commands from `pipeline/` with the venv active unless a step says otherwise.

---

### Task 1: Scaffold + manifest loading

**Files:**
- Create: `pipeline/pyproject.toml`
- Create: `pipeline/src/benchside_pipeline/__init__.py`
- Create: `pipeline/src/benchside_pipeline/model.py` (only `SourceDoc` this task)
- Create: `pipeline/src/benchside_pipeline/manifest.py`
- Create: `sources/sources.yaml` (placeholder with one fixture entry)
- Modify: `.gitignore` (repo root)
- Test: `pipeline/tests/test_manifest.py`

**Interfaces:**
- Produces: `SourceDoc` dataclass with fields `id: str, prefix: str, title: str, version: str, published: str, url: str, file: str, heading_rules: list[str]`; `load_manifest(path: Path) -> list[SourceDoc]` raising `ManifestError` on missing fields or duplicate `id`/`prefix`.

- [ ] **Step 1: Create project scaffold**

`pipeline/pyproject.toml`:

```toml
[project]
name = "benchside-pipeline"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pdfplumber>=0.11", "PyYAML>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "reportlab>=4.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

`pipeline/src/benchside_pipeline/__init__.py`: empty file.

Append to repo-root `.gitignore`:

```
sources/*.pdf
build/
```

Set up the environment:

```bash
cd pipeline && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'
```

Expected: install succeeds.

- [ ] **Step 2: Write the failing test**

`pipeline/tests/test_manifest.py`:

```python
from pathlib import Path

import pytest

from benchside_pipeline.manifest import ManifestError, load_manifest

VALID = """
documents:
  - id: fixture-doc
    prefix: fix
    title: "Fixture Rules Document"
    version: "1.0"
    published: "2026-01-01"
    url: "https://example.com/fixture.pdf"
    file: "fixture.pdf"
    heading_rules:
      - '^(\\d+)\\.\\s+(.+)$'
      - '^(\\d+\\.\\d+)\\s+(.+)$'
"""


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "sources.yaml"
    p.write_text(text)
    return p


def test_load_valid_manifest(tmp_path):
    docs = load_manifest(write(tmp_path, VALID))
    assert len(docs) == 1
    d = docs[0]
    assert d.id == "fixture-doc"
    assert d.prefix == "fix"
    assert d.heading_rules[0] == r"^(\d+)\.\s+(.+)$"


def test_missing_field_raises(tmp_path):
    bad = VALID.replace('    version: "1.0"\n', "")
    with pytest.raises(ManifestError, match="version"):
        load_manifest(write(tmp_path, bad))


def test_duplicate_prefix_raises(tmp_path):
    doubled = VALID + VALID.replace("documents:\n", "").replace(
        "id: fixture-doc", "id: other-doc"
    )
    with pytest.raises(ManifestError, match="prefix"):
        load_manifest(write(tmp_path, doubled))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_manifest.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError` or `ImportError` (manifest module doesn't exist).

- [ ] **Step 4: Write minimal implementation**

`pipeline/src/benchside_pipeline/model.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


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
```

`pipeline/src/benchside_pipeline/manifest.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml

from benchside_pipeline.model import SourceDoc

REQUIRED = ("id", "prefix", "title", "version", "published", "url", "file", "heading_rules")


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
        docs.append(SourceDoc(**{k: entry[k] for k in REQUIRED}))
    for field in ("id", "prefix"):
        values = [getattr(d, field) for d in docs]
        dupes = {v for v in values if values.count(v) > 1}
        if dupes:
            raise ManifestError(f"duplicate {field}: {', '.join(sorted(dupes))}")
    return docs
```

`sources/sources.yaml` (placeholder until Task 9 registers real documents):

```yaml
documents: []
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_manifest.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add ../.gitignore ../sources/sources.yaml pyproject.toml src tests
git commit -m "feat(pipeline): scaffold + sources.yaml manifest loading"
```

---

### Task 2: Section model + content JSON round-trip

**Files:**
- Modify: `pipeline/src/benchside_pipeline/model.py`
- Test: `pipeline/tests/test_model.py`

**Interfaces:**
- Consumes: `SourceDoc` (Task 1).
- Produces: `Section` dataclass with fields `id: str, doc_id: str, parent_id: str | None, number: str, title: str, body: str, breadcrumb: str, order: int`; `dump_document(source: SourceDoc, sections: list[Section], path: Path) -> None` and `load_document(path: Path) -> tuple[SourceDoc, list[Section]]` (JSON, human-diffable, keys sorted, indent 2).

- [ ] **Step 1: Write the failing test**

`pipeline/tests/test_model.py`:

```python
from benchside_pipeline.model import Section, SourceDoc, dump_document, load_document

SOURCE = SourceDoc(
    id="fixture-doc", prefix="fix", title="Fixture Rules Document",
    version="1.0", published="2026-01-01", url="https://example.com/fixture.pdf",
    file="fixture.pdf", heading_rules=[r"^(\d+)\.\s+(.+)$"],
)

SECTIONS = [
    Section(id="fix-1", doc_id="fixture-doc", parent_id=None, number="1",
            title="Setup", body="Shuffle your deck.", breadcrumb="Fixture Rules Document",
            order=0),
    Section(id="fix-1.1", doc_id="fixture-doc", parent_id="fix-1", number="1.1",
            title="Prizes", body="Set aside 6 prize cards.",
            breadcrumb="Fixture Rules Document › Setup", order=1),
]


def test_round_trip(tmp_path):
    path = tmp_path / "fixture-doc.json"
    dump_document(SOURCE, SECTIONS, path)
    source2, sections2 = load_document(path)
    assert source2 == SOURCE
    assert sections2 == SECTIONS


def test_json_is_stable_and_readable(tmp_path):
    path = tmp_path / "fixture-doc.json"
    dump_document(SOURCE, SECTIONS, path)
    text = path.read_text()
    assert '"id": "fix-1"' in text          # indent + sorted keys → diffable
    dump_document(SOURCE, SECTIONS, path)   # writing twice is byte-identical
    assert path.read_text() == text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_model.py -v`
Expected: FAIL with `ImportError` (`Section`, `dump_document`, `load_document` not defined).

- [ ] **Step 3: Write minimal implementation**

Append to `pipeline/src/benchside_pipeline/model.py`:

```python
import dataclasses
import json
from pathlib import Path


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
```

(Add `import dataclasses`, `import json`, and `from pathlib import Path` at the top of the file with the existing imports.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_model.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(pipeline): Section model + content JSON round-trip"
```

---

### Task 3: Heading classification

**Files:**
- Create: `pipeline/src/benchside_pipeline/headings.py`
- Test: `pipeline/tests/test_headings.py`

**Interfaces:**
- Produces: `Heading` dataclass `(level: int, number: str, title: str)`; `classify_line(line: str, heading_rules: list[str]) -> Heading | None`. Rule index i (0-based) ⇒ level i+1. Group 1 of each regex = section number, group 2 = title.

- [ ] **Step 1: Write the failing test**

`pipeline/tests/test_headings.py`:

```python
from benchside_pipeline.headings import Heading, classify_line

RULES = [r"^(\d+)\.\s+(.+)$", r"^(\d+\.\d+)\s+(.+)$"]


def test_level_one_heading():
    assert classify_line("3. Special Conditions", RULES) == Heading(1, "3", "Special Conditions")


def test_level_two_heading():
    assert classify_line("3.2 Asleep", RULES) == Heading(2, "3.2", "Asleep")


def test_body_line_is_not_heading():
    assert classify_line("Flip a coin. If heads, the Pokemon wakes up.", RULES) is None


def test_leading_whitespace_tolerated():
    assert classify_line("  3.2 Asleep ", RULES) == Heading(2, "3.2", "Asleep")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_headings.py -v`
Expected: FAIL with `ModuleNotFoundError: benchside_pipeline.headings`.

- [ ] **Step 3: Write minimal implementation**

`pipeline/src/benchside_pipeline/headings.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Heading:
    level: int
    number: str
    title: str


def classify_line(line: str, heading_rules: list[str]) -> Heading | None:
    stripped = line.strip()
    for i, rule in enumerate(heading_rules):
        m = re.match(rule, stripped)
        if m:
            return Heading(level=i + 1, number=m.group(1), title=m.group(2).strip())
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_headings.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(pipeline): heading classification from manifest regex rules"
```

---

### Task 4: PDF extraction + section tree building

**Files:**
- Create: `pipeline/src/benchside_pipeline/parse.py`
- Create: `pipeline/tests/conftest.py`
- Test: `pipeline/tests/test_parse.py`

**Interfaces:**
- Consumes: `SourceDoc`, `Section` (Tasks 1–2), `classify_line` (Task 3).
- Produces: `extract_lines(pdf_path: Path) -> list[str]`; `build_tree(lines: list[str], source: SourceDoc) -> list[Section]`; `parse_pdf(pdf_path: Path, source: SourceDoc) -> list[Section]` (= extract + build). Sections come back in document order; `order` is the list index; breadcrumb is `doc title › ancestor titles` joined with ` › `.

- [ ] **Step 1: Write the fixture-PDF helper**

`pipeline/tests/conftest.py`:

```python
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas


def make_pdf(path: Path, lines: list[str]) -> Path:
    c = canvas.Canvas(str(path))
    y = 800
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
        if y < 72:
            c.showPage()
            y = 800
    c.save()
    return path


FIXTURE_LINES = [
    "1. Setup",
    "Shuffle your deck and draw 7 cards.",
    "1.1 Prizes",
    "Set aside 6 prize cards. See section 3.2 for conditions during setup.",
    "2. Turn Structure",
    "Players alternate turns.",
    "3. Special Conditions",
    "Conditions affect Active Pokemon only.",
    "3.2 Asleep",
    "Flip a coin between turns. If heads, the Pokemon wakes up.",
]


@pytest.fixture
def fixture_pdf(tmp_path):
    return make_pdf(tmp_path / "fixture.pdf", FIXTURE_LINES)


@pytest.fixture
def fixture_source():
    from benchside_pipeline.model import SourceDoc

    return SourceDoc(
        id="fixture-doc", prefix="fix", title="Fixture Rules Document",
        version="1.0", published="2026-01-01", url="https://example.com/fixture.pdf",
        file="fixture.pdf",
        heading_rules=[r"^(\d+)\.\s+(.+)$", r"^(\d+\.\d+)\s+(.+)$"],
    )
```

- [ ] **Step 2: Write the failing test**

`pipeline/tests/test_parse.py`:

```python
from benchside_pipeline.parse import build_tree, extract_lines, parse_pdf


def test_extract_lines(fixture_pdf):
    lines = extract_lines(fixture_pdf)
    assert "1. Setup" in [l.strip() for l in lines]
    assert any("wakes up" in l for l in lines)


def test_tree_structure(fixture_pdf, fixture_source):
    sections = parse_pdf(fixture_pdf, fixture_source)
    ids = [s.id for s in sections]
    assert ids == ["fix-1", "fix-1.1", "fix-2", "fix-3", "fix-3.2"]
    by_id = {s.id: s for s in sections}
    assert by_id["fix-1.1"].parent_id == "fix-1"
    assert by_id["fix-3.2"].parent_id == "fix-3"
    assert by_id["fix-2"].parent_id is None
    assert by_id["fix-3.2"].title == "Asleep"
    assert "wakes up" in by_id["fix-3.2"].body
    assert by_id["fix-3.2"].breadcrumb == "Fixture Rules Document › Special Conditions"
    assert [s.order for s in sections] == [0, 1, 2, 3, 4]


def test_sibling_replaces_sibling(fixture_source):
    lines = ["1. Alpha", "body a", "2. Beta", "body b"]
    sections = build_tree(lines, fixture_source)
    assert [s.id for s in sections] == ["fix-1", "fix-2"]
    assert sections[1].parent_id is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_parse.py -v`
Expected: FAIL with `ModuleNotFoundError: benchside_pipeline.parse`.

- [ ] **Step 4: Write minimal implementation**

`pipeline/src/benchside_pipeline/parse.py`:

```python
from __future__ import annotations

from pathlib import Path

import pdfplumber

from benchside_pipeline.headings import classify_line
from benchside_pipeline.model import Section, SourceDoc


def extract_lines(pdf_path: Path) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(text.splitlines())
    return lines


def build_tree(lines: list[str], source: SourceDoc) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, Section]] = []
    body: list[str] = []

    def flush() -> None:
        if stack and body:
            sec = stack[-1][1]
            text = "\n".join(body).strip()
            sec.body = f"{sec.body}\n{text}".strip() if sec.body else text
        body.clear()

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        heading = classify_line(line, source.heading_rules)
        if heading is None:
            body.append(line)
            continue
        flush()
        while stack and stack[-1][0] >= heading.level:
            stack.pop()
        parent = stack[-1][1] if stack else None
        crumb = " › ".join([source.title] + [s.title for _, s in stack])
        sec = Section(
            id=f"{source.prefix}-{heading.number}",
            doc_id=source.id,
            parent_id=parent.id if parent else None,
            number=heading.number,
            title=heading.title,
            body="",
            breadcrumb=crumb,
            order=len(sections),
        )
        sections.append(sec)
        stack.append((heading.level, sec))
    flush()
    return sections


def parse_pdf(pdf_path: Path, source: SourceDoc) -> list[Section]:
    return build_tree(extract_lines(pdf_path), source)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_parse.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat(pipeline): PDF extraction and section tree building"
```

---

### Task 5: Cross-reference detection

**Files:**
- Create: `pipeline/src/benchside_pipeline/xrefs.py`
- Test: `pipeline/tests/test_xrefs.py`

**Interfaces:**
- Consumes: `Section` (Task 2).
- Produces: `detect_xrefs(sections: list[Section]) -> list[tuple[str, str]]` — `(from_id, to_id)` pairs, same-document only, deduped, self-references excluded, mentions of section numbers that don't exist ignored. Pattern matched in body text: `section 3.2` / `Section 3.2`.

- [ ] **Step 1: Write the failing test**

`pipeline/tests/test_xrefs.py`:

```python
from benchside_pipeline.model import Section
from benchside_pipeline.xrefs import detect_xrefs


def sec(id, number, body, doc_id="fixture-doc"):
    return Section(id=id, doc_id=doc_id, parent_id=None, number=number,
                   title=f"S{number}", body=body, breadcrumb="", order=0)


def test_detects_reference():
    sections = [
        sec("fix-1.1", "1.1", "See section 3.2 for conditions."),
        sec("fix-3.2", "3.2", "Flip a coin."),
    ]
    assert detect_xrefs(sections) == [("fix-1.1", "fix-3.2")]


def test_ignores_missing_target_and_self():
    sections = [sec("fix-1", "1", "See section 9.9. Also see Section 1 itself.")]
    assert detect_xrefs(sections) == []


def test_dedupes():
    sections = [
        sec("fix-1", "1", "See section 2. Again, see section 2."),
        sec("fix-2", "2", "body"),
    ]
    assert detect_xrefs(sections) == [("fix-1", "fix-2")]


def test_same_document_only():
    sections = [
        sec("fix-1", "1", "See section 2.", doc_id="doc-a"),
        sec("oth-2", "2", "body", doc_id="doc-b"),
    ]
    assert detect_xrefs(sections) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_xrefs.py -v`
Expected: FAIL with `ModuleNotFoundError: benchside_pipeline.xrefs`.

- [ ] **Step 3: Write minimal implementation**

`pipeline/src/benchside_pipeline/xrefs.py`:

```python
from __future__ import annotations

import re

from benchside_pipeline.model import Section

XREF_RE = re.compile(r"[Ss]ection\s+(\d+(?:\.\d+)*)")


def detect_xrefs(sections: list[Section]) -> list[tuple[str, str]]:
    by_number = {(s.doc_id, s.number): s.id for s in sections}
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for s in sections:
        for m in XREF_RE.finditer(s.body):
            target = by_number.get((s.doc_id, m.group(1)))
            if target is None or target == s.id:
                continue
            pair = (s.id, target)
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_xrefs.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(pipeline): same-document cross-reference detection"
```

---

### Task 6: SQLite build with FTS5

**Files:**
- Create: `pipeline/src/benchside_pipeline/build.py`
- Test: `pipeline/tests/test_build.py`

**Interfaces:**
- Consumes: `load_document` (Task 2), `detect_xrefs` (Task 5).
- Produces: `SCHEMA: str`; `build_db(content_dir: Path, out_path: Path) -> None` — reads every `*.json` in `content_dir` (sorted by filename), writes a fresh SQLite DB. Tables: `documents(id, prefix, title, version, published, url)`, `sections(id, doc_id, parent_id, number, title, body, breadcrumb, sort_order)`, `xrefs(from_id, to_id)`, and FTS5 `sections_fts(title, body)` with `content='sections'`. This schema is the contract the iOS app's `RulesRepository` builds against.

- [ ] **Step 1: Write the failing test**

`pipeline/tests/test_build.py`:

```python
import sqlite3

from benchside_pipeline.build import build_db
from benchside_pipeline.model import dump_document
from benchside_pipeline.parse import parse_pdf


def test_build_db(fixture_pdf, fixture_source, tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")

    db_path = tmp_path / "benchside.db"
    build_db(content_dir, db_path)

    con = sqlite3.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM sections").fetchone()[0] == 5
    assert con.execute(
        "SELECT COUNT(*) FROM sections_fts WHERE sections_fts MATCH 'asleep'"
    ).fetchone()[0] == 1
    # title weighting: 'asleep' in a title outranks it in a body
    row = con.execute(
        """
        SELECT s.id FROM sections_fts f JOIN sections s ON s.rowid = f.rowid
        WHERE sections_fts MATCH 'asleep'
        ORDER BY bm25(sections_fts, 10.0, 1.0) LIMIT 1
        """
    ).fetchone()
    assert row[0] == "fix-3.2"
    assert con.execute("SELECT from_id, to_id FROM xrefs").fetchall() == [
        ("fix-1.1", "fix-3.2")
    ]
    con.close()


def test_rebuild_is_fresh(fixture_pdf, fixture_source, tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")
    db_path = tmp_path / "benchside.db"
    build_db(content_dir, db_path)
    build_db(content_dir, db_path)  # second build must not duplicate rows
    con = sqlite3.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM sections").fetchone()[0] == 5
    con.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_build.py -v`
Expected: FAIL with `ModuleNotFoundError: benchside_pipeline.build`.

- [ ] **Step 3: Write minimal implementation**

`pipeline/src/benchside_pipeline/build.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

from benchside_pipeline.model import load_document
from benchside_pipeline.xrefs import detect_xrefs

SCHEMA = """
CREATE TABLE documents(
  id TEXT PRIMARY KEY,
  prefix TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  version TEXT NOT NULL,
  published TEXT NOT NULL,
  url TEXT NOT NULL
);
CREATE TABLE sections(
  id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL REFERENCES documents(id),
  parent_id TEXT REFERENCES sections(id),
  number TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  breadcrumb TEXT NOT NULL,
  sort_order INTEGER NOT NULL
);
CREATE TABLE xrefs(
  from_id TEXT NOT NULL REFERENCES sections(id),
  to_id TEXT NOT NULL REFERENCES sections(id),
  PRIMARY KEY (from_id, to_id)
);
CREATE VIRTUAL TABLE sections_fts USING fts5(
  title, body, content='sections', content_rowid='rowid'
);
"""


def build_db(content_dir: Path, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.unlink(missing_ok=True)
    con = sqlite3.connect(out_path)
    try:
        con.executescript(SCHEMA)
        for json_path in sorted(Path(content_dir).glob("*.json")):
            source, sections = load_document(json_path)
            con.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
                (source.id, source.prefix, source.title, source.version,
                 source.published, source.url),
            )
            con.executemany(
                "INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(s.id, s.doc_id, s.parent_id, s.number, s.title, s.body,
                  s.breadcrumb, s.order) for s in sections],
            )
            con.executemany(
                "INSERT INTO xrefs VALUES (?, ?)", detect_xrefs(sections)
            )
        con.execute(
            "INSERT INTO sections_fts(rowid, title, body) "
            "SELECT rowid, title, body FROM sections"
        )
        con.commit()
    finally:
        con.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_build.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(pipeline): SQLite+FTS5 build from content JSON"
```

---

### Task 7: Verify step

**Files:**
- Create: `pipeline/src/benchside_pipeline/verify.py`
- Test: `pipeline/tests/test_verify.py`

**Interfaces:**
- Consumes: DB produced by `build_db` (Task 6).
- Produces: `verify_db(db_path: Path) -> list[str]` — empty list means OK. Checks: (1) every document has ≥1 section; (2) no **leaf** section (no children) with empty body; (3) every `xrefs.to_id` exists in `sections`; (4) `sections_fts` row count equals `sections` row count; (5) every `parent_id` exists.

- [ ] **Step 1: Write the failing test**

`pipeline/tests/test_verify.py`:

```python
import sqlite3

from benchside_pipeline.build import build_db
from benchside_pipeline.model import dump_document
from benchside_pipeline.parse import parse_pdf
from benchside_pipeline.verify import verify_db


def make_db(fixture_pdf, fixture_source, tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")
    db_path = tmp_path / "benchside.db"
    build_db(content_dir, db_path)
    return db_path


def test_clean_db_verifies(fixture_pdf, fixture_source, tmp_path):
    assert verify_db(make_db(fixture_pdf, fixture_source, tmp_path)) == []


def test_empty_leaf_body_fails(fixture_pdf, fixture_source, tmp_path):
    db_path = make_db(fixture_pdf, fixture_source, tmp_path)
    con = sqlite3.connect(db_path)
    con.execute("UPDATE sections SET body = '' WHERE id = 'fix-3.2'")
    con.commit(); con.close()
    errors = verify_db(db_path)
    assert any("fix-3.2" in e and "empty body" in e for e in errors)


def test_broken_xref_fails(fixture_pdf, fixture_source, tmp_path):
    db_path = make_db(fixture_pdf, fixture_source, tmp_path)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute("UPDATE xrefs SET to_id = 'fix-9.9'")
    con.commit(); con.close()
    errors = verify_db(db_path)
    assert any("fix-9.9" in e and "xref" in e for e in errors)


def test_fts_count_mismatch_fails(fixture_pdf, fixture_source, tmp_path):
    db_path = make_db(fixture_pdf, fixture_source, tmp_path)
    con = sqlite3.connect(db_path)
    con.execute("INSERT INTO sections_fts(title, body) VALUES ('extra', 'row')")
    con.commit(); con.close()
    errors = verify_db(db_path)
    assert any("fts" in e.lower() for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_verify.py -v`
Expected: FAIL with `ModuleNotFoundError: benchside_pipeline.verify`.

- [ ] **Step 3: Write minimal implementation**

`pipeline/src/benchside_pipeline/verify.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path


def verify_db(db_path: Path) -> list[str]:
    errors: list[str] = []
    con = sqlite3.connect(db_path)
    try:
        for (doc_id,) in con.execute(
            "SELECT d.id FROM documents d "
            "LEFT JOIN sections s ON s.doc_id = d.id "
            "GROUP BY d.id HAVING COUNT(s.id) = 0"
        ):
            errors.append(f"document {doc_id}: no sections")
        for (sec_id,) in con.execute(
            "SELECT s.id FROM sections s "
            "WHERE TRIM(s.body) = '' AND NOT EXISTS "
            "(SELECT 1 FROM sections c WHERE c.parent_id = s.id)"
        ):
            errors.append(f"section {sec_id}: leaf with empty body")
        for from_id, to_id in con.execute(
            "SELECT x.from_id, x.to_id FROM xrefs x "
            "LEFT JOIN sections s ON s.id = x.to_id WHERE s.id IS NULL"
        ):
            errors.append(f"xref {from_id} -> {to_id}: target missing")
        for (parent_id,) in con.execute(
            "SELECT DISTINCT s.parent_id FROM sections s "
            "LEFT JOIN sections p ON p.id = s.parent_id "
            "WHERE s.parent_id IS NOT NULL AND p.id IS NULL"
        ):
            errors.append(f"parent {parent_id}: missing")
        n_sections = con.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
        n_fts = con.execute("SELECT COUNT(*) FROM sections_fts").fetchone()[0]
        if n_sections != n_fts:
            errors.append(f"fts row count {n_fts} != sections {n_sections}")
    finally:
        con.close()
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_verify.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(pipeline): verify step for built database"
```

---

### Task 8: CLI wiring

**Files:**
- Create: `pipeline/src/benchside_pipeline/__main__.py`
- Test: `pipeline/tests/test_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: `python -m benchside_pipeline <parse|build|verify|all> [--root PATH]`. `--root` defaults to the repo root (two levels up from the package, i.e. `Path(__file__).parents[3]` won't work from site-packages — resolve from CWD instead: default `Path.cwd().parent` when run from `pipeline/`, overridable). Paths derived from root: `sources/sources.yaml`, `sources/<file>`, `content/`, `build/benchside.db`. `parse` writes one JSON per manifest document; `build` writes the DB; `verify` prints errors and exits 1 if any; `all` = parse, build, verify. Exposes `main(argv: list[str] | None = None) -> int` for testing.

- [ ] **Step 1: Write the failing test**

`pipeline/tests/test_cli.py`:

```python
import shutil

from benchside_pipeline.__main__ import main


def make_repo(tmp_path, fixture_pdf):
    root = tmp_path / "repo"
    (root / "sources").mkdir(parents=True)
    (root / "content").mkdir()
    shutil.copy(fixture_pdf, root / "sources" / "fixture.pdf")
    (root / "sources" / "sources.yaml").write_text(
        """
documents:
  - id: fixture-doc
    prefix: fix
    title: "Fixture Rules Document"
    version: "1.0"
    published: "2026-01-01"
    url: "https://example.com/fixture.pdf"
    file: "fixture.pdf"
    heading_rules:
      - '^(\\d+)\\.\\s+(.+)$'
      - '^(\\d+\\.\\d+)\\s+(.+)$'
"""
    )
    return root


def test_all_pipeline(tmp_path, fixture_pdf):
    root = make_repo(tmp_path, fixture_pdf)
    assert main(["all", "--root", str(root)]) == 0
    assert (root / "content" / "fixture-doc.json").exists()
    assert (root / "build" / "benchside.db").exists()


def test_verify_failure_exit_code(tmp_path, fixture_pdf):
    root = make_repo(tmp_path, fixture_pdf)
    assert main(["parse", "--root", str(root)]) == 0
    # sabotage: blank a leaf body in the content JSON
    p = root / "content" / "fixture-doc.json"
    p.write_text(p.read_text().replace(
        "Flip a coin between turns. If heads, the Pokemon wakes up.", ""))
    assert main(["build", "--root", str(root)]) == 0
    assert main(["verify", "--root", str(root)]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: benchside_pipeline.__main__`.

- [ ] **Step 3: Write minimal implementation**

`pipeline/src/benchside_pipeline/__main__.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from benchside_pipeline.build import build_db
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="benchside_pipeline")
    parser.add_argument("command", choices=["parse", "build", "verify", "all"])
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
    rc = cmd_parse(root)
    if rc == 0:
        rc = cmd_build(root)
    if rc == 0:
        rc = cmd_verify(root)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v` then the whole suite `pytest -v`
Expected: 2 passed; full suite green.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat(pipeline): CLI with parse/build/verify/all commands"
```

---

### Task 9: Ingest the real documents

This task is exploratory by nature — real TPCi PDFs have layouts we haven't
seen. The loop is: register → dump → tune heading rules → verify. Code changes
should not be needed; if a document defeats regex-on-lines parsing entirely,
stop and surface the problem rather than hacking the parser.

**Files:**
- Modify: `sources/sources.yaml`
- Create: `content/<doc-id>.json` (one per document, via the pipeline)
- Download into: `sources/*.pdf` (git-ignored)

**Interfaces:**
- Consumes: the full CLI (Task 8).
- Produces: committed `content/*.json` for: the core TCG rulebook, the Play! Pokemon tournament rules handbook, and the penalty guidelines; a `build/benchside.db` that passes `verify`.

- [ ] **Step 1: Locate and download the current official PDFs**

Find the current documents at https://www.pokemon.com/us/play-pokemon/about/tournaments-rules-and-resources (rulebook also ships inside product inserts; use the site's PDF). Save into `sources/` with short names, e.g.:

```bash
# from repo root; exact URLs must be taken from the page above at execution time
curl -L -o sources/tcg-rules.pdf "<rulebook pdf url>"
curl -L -o sources/tournament-rules.pdf "<tournament rules handbook pdf url>"
curl -L -o sources/penalty-guidelines.pdf "<penalty guidelines pdf url>"
```

Confirm each file opens and note title, version, and publication date from the cover page.

- [ ] **Step 2: Register each document in sources.yaml**

Template (fill real titles/versions/dates/URLs from Step 1; heading_rules start as the standard numbered pattern and get tuned in Step 3):

```yaml
documents:
  - id: tcg-rules
    prefix: tcg
    title: "<exact cover title>"
    version: "<version or revision date on the document>"
    published: "<YYYY-MM-DD>"
    url: "<origin url>"
    file: "tcg-rules.pdf"
    heading_rules:
      - '^(\d+)\.\s+(.+)$'
      - '^(\d+\.\d+)\s+(.+)$'
      - '^(\d+\.\d+\.\d+)\s+(.+)$'
  - id: tournament-rules
    prefix: trh
    # ... same shape
  - id: penalty-guidelines
    prefix: pen
    # ... same shape
```

- [ ] **Step 3: Iterate until parse output is correct**

For each document, dump what the extractor sees, then tune that document's `heading_rules` until the tree matches the PDF's table of contents:

```bash
cd pipeline && source .venv/bin/activate
python -c "
from benchside_pipeline.parse import extract_lines
for l in extract_lines('../sources/tournament-rules.pdf')[:120]:
    print(repr(l))
"
python -m benchside_pipeline parse --root ..
```

Inspect each `content/*.json`: section count plausible? Titles match the ToC? Bodies non-empty? Repeat per document. Watch for: page headers/footers polluting bodies (add a cleanup regex to that doc's entry ONLY if it appears — if needed, extend `SourceDoc` with an optional `strip_lines: list[str]` field, filtered in `build_tree`, with a unit test).

- [ ] **Step 4: Build and verify**

```bash
python -m benchside_pipeline all --root ..
```

Expected: `verify OK`. Fix content issues by tuning the manifest, not by editing JSON by hand.

- [ ] **Step 5: Commit**

```bash
cd .. && git add sources/sources.yaml content/
git commit -m "feat(content): ingest rulebook, tournament rules, penalty guidelines"
```

---

### Task 10: Persona acceptance queries (DB-level)

The spec's two acceptance anchors, run against the real database. These are
the pipeline's definition of done; the same queries later back the app's
search tests.

**Files:**
- Test: `pipeline/tests/test_personas.py`

**Interfaces:**
- Consumes: `build/benchside.db` (Task 9). Test auto-skips if the DB hasn't been built, so CI without real sources stays green.

- [ ] **Step 1: Write the test**

`pipeline/tests/test_personas.py`:

```python
import sqlite3
from pathlib import Path

import pytest

DB = Path(__file__).resolve().parents[2] / "build" / "benchside.db"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="real DB not built")


def top_hit(query: str, doc_id: str | None = None) -> tuple[str, str]:
    con = sqlite3.connect(DB)
    sql = (
        "SELECT s.id, s.title, s.doc_id FROM sections_fts f "
        "JOIN sections s ON s.rowid = f.rowid "
        "WHERE sections_fts MATCH ? "
        "ORDER BY bm25(sections_fts, 10.0, 1.0) LIMIT 5"
    )
    rows = con.execute(sql, (query,)).fetchall()
    con.close()
    assert rows, f"no hits for {query!r}"
    return rows[0][0], rows[0][2]


def test_player_asleep():
    sec_id, doc_id = top_hit("asleep")
    assert doc_id == "tcg-rules"
    # exact id depends on the current rulebook numbering; the title row must
    # be the Asleep special-condition section — assert via title:
    con = sqlite3.connect(DB)
    title = con.execute("SELECT title FROM sections WHERE id = ?", (sec_id,)).fetchone()[0]
    con.close()
    assert "asleep" in title.lower()


def test_judge_deck_check():
    sec_id, doc_id = top_hit("deck check")
    assert doc_id in ("tournament-rules", "penalty-guidelines")
    con = sqlite3.connect(DB)
    title = con.execute("SELECT title FROM sections WHERE id = ?", (sec_id,)).fetchone()[0]
    con.close()
    assert "deck check" in title.lower()
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_personas.py -v`
Expected: 2 passed (or skipped if Task 9's DB is absent — must pass on the real DB before this plan is done).

If a persona test fails on ranking, tune is limited to: (a) heading_rules producing better titles, (b) the bm25 weights — and any weight change must be mirrored in the app plan's repository queries.

- [ ] **Step 3: Commit**

```bash
git add tests
git commit -m "test(pipeline): persona acceptance queries against real DB"
```

---

## Definition of Done

- `pytest -v` green in `pipeline/` (all tasks).
- `python -m benchside_pipeline all --root ..` prints `verify OK` on real documents.
- `content/*.json` committed for all three documents; no PDFs or DB in git.
- Persona tests pass against the real DB.
