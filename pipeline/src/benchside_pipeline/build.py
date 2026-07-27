from __future__ import annotations

import sqlite3
from pathlib import Path

from benchside_pipeline.flatten import flatten_entry
from benchside_pipeline.model import load_document
from benchside_pipeline.rewrites import load_rewrites
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


def build_db(content_dir: Path, out_path: Path, rewrites_dir: Path | None = None) -> None:
    """Build the shipped DB. When a section has a rewrite entry, its body is
    the flattened structured content (phase 1 of the structured rulebase);
    sections without entries keep verbatim text — verify owns the coverage
    gate, not build."""
    rewrites = load_rewrites(rewrites_dir) if rewrites_dir and Path(rewrites_dir).is_dir() else {}
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
                [(s.id, s.doc_id, s.parent_id, s.number, s.title,
                  flatten_entry(rewrites[s.id]) if s.id in rewrites else s.body,
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
