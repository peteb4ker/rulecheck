from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from rulecheck_pipeline.flatten import flatten_entry
from rulecheck_pipeline.model import load_document
from rulecheck_pipeline.rewrites import is_skip, load_rewrites
from rulecheck_pipeline.xrefs import detect_xrefs

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
  sort_order INTEGER NOT NULL,
  -- The authored entry as JSON. FTS indexes the flattened `body`; the app
  -- renders this. NULL for sections still shipping verbatim reference text.
  structure TEXT
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


def build_db(content_dir: Path, out_path: Path, rewrites_dir: Path | None = None,
             full_content_dir: Path | None = None) -> None:
    """Build the shipped DB from the authored structure.

    A section with a rewrite entry ships the flattened structured content.
    A section without one has no shippable text: the committed index carries
    no prose, so there is nothing to fall back to and build refuses rather
    than shipping an empty row.

    `full_content_dir` is the local parse artifact (`build/content/`). When it
    is present its verbatim bodies are used for unauthored sections, which is
    what makes `just all` work mid-migration. It never exists in CI, so there
    the no-verbatim guarantee is structural rather than a matter of trust.
    """
    rewrites = load_rewrites(rewrites_dir) if rewrites_dir and Path(rewrites_dir).is_dir() else {}
    bodies: dict[str, str] = {}
    if full_content_dir and Path(full_content_dir).is_dir():
        for path in sorted(Path(full_content_dir).glob("*.json")):
            for section in load_document(path)[1]:
                if section.body:
                    bodies[section.id] = section.body
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.unlink(missing_ok=True)
    con = sqlite3.connect(out_path)
    try:
        # SQLite ignores declared REFERENCES unless the connection asks for
        # them, per connection and off by default. Without this the schema's
        # constraints are documentation; with it a broken tree fails the build
        # instead of shipping. Must precede any transaction to take effect.
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA)
        for json_path in sorted(Path(content_dir).glob("*.json")):
            source, sections = load_document(json_path)
            con.execute(
                "INSERT INTO documents(id, prefix, title, version, published, url) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (source.id, source.prefix, source.title, source.version,
                 source.published, source.url),
            )
            # Skipped sections never reach the app at all — not as structure,
            # and emphatically not as verbatim source text.
            shipped = [s for s in sections
                       if not (s.id in rewrites and is_skip(rewrites[s.id]))]
            # Prose with nowhere to get its text from: no entry, no body in
            # this artifact, none in the local parse output either.
            unauthored = [s.id for s in shipped
                          if s.id not in rewrites and s.body_chars
                          and not s.body and s.id not in bodies]
            if unauthored:
                raise ValueError(
                    "cannot build: these sections carry prose but have no rewrite entry, "
                    "and the repository holds no verbatim text to fall back on — "
                    f"author them or run `just parse`: {', '.join(sorted(unauthored)[:5])}"
                )
            con.executemany(
                "INSERT INTO sections(id, doc_id, parent_id, number, title, body, "
                "breadcrumb, sort_order, structure) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(s.id, s.doc_id, s.parent_id, s.number, s.title,
                  flatten_entry(rewrites[s.id]) if s.id in rewrites
                  else bodies.get(s.id, s.body),
                  s.breadcrumb, s.order,
                  json.dumps(rewrites[s.id], sort_keys=True, ensure_ascii=False)
                  if s.id in rewrites else None) for s in shipped],
            )
            shipped_ids = {s.id for s in shipped}
            con.executemany(
                "INSERT INTO xrefs(from_id, to_id) VALUES (?, ?)",
                [(f, t) for f, t in detect_xrefs(sections)
                 if f in shipped_ids and t in shipped_ids],
            )
        con.execute(
            "INSERT INTO sections_fts(rowid, title, body) "
            "SELECT rowid, title, body FROM sections"
        )
        con.commit()
    finally:
        con.close()
