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
