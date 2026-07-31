from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from rulecheck_pipeline import glyphs
from rulecheck_pipeline.flatten import flatten_entry
from rulecheck_pipeline.model import load_document
from rulecheck_pipeline.rewrites import is_skip, load_rewrites
from rulecheck_pipeline.model import load_xrefs
from rulecheck_pipeline.xrefs import detect_xrefs

SCHEMA = """
CREATE TABLE documents(
  id TEXT PRIMARY KEY,
  prefix TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  version TEXT NOT NULL,
  published TEXT NOT NULL,
  url TEXT NOT NULL,
  -- Position in sources.yaml. The browse screen orders by this so a player
  -- meets the game rules first, not whichever title sorts first.
  sort_order INTEGER NOT NULL
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


def _structure_json(entry: dict, glyph_index: list[dict]) -> str:
    """The authored entry plus its derived glyphs, as it ships.

    The glyphs are added here and nowhere else. `rewrites/` is hand-authored
    and never written back to, so a rebuild always regenerates them and they
    cannot drift from the lexicon.
    """
    payload = dict(entry)
    if glyph_index:
        payload.update(glyphs.annotate(entry, glyph_index))
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _glyph_index(lexicon_dir: Path, rewrites: dict) -> list[dict]:
    """The glyph matcher's index, or empty when there is no lexicon.

    A fresh clone, or any build predating the lexicon, must still produce a
    database. No lexicon means no glyphs, not a failure.

    Occurrence counts come from the authored corpus and matter more than they
    look: they break ties inside a category toward the rarer concept. Without
    them the row "Tails, Still Asleep" draws the Asleep glyph, because
    "asleep" sorts before "tails" and the tie falls back to the term itself.
    """
    if not lexicon_dir.is_dir():
        return []

    terms: list[dict] = []
    for path in sorted(lexicon_dir.glob("*.json")):
        terms.extend(json.loads(path.read_text()).get("terms", []))
    if not terms:
        return []

    texts: list[str] = []

    def walk(value):
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                texts.append(key)
                walk(item)

    for entry in rewrites.values():
        if not is_skip(entry):
            walk(entry)

    corpus = glyphs.stems(" ".join(texts))
    counts: dict[str, int] = {}
    for term in terms:
        key = glyphs.stems(term["term"])
        counts[term["term"]] = (
            sum(1 for i in range(len(corpus) - len(key) + 1)
                if corpus[i:i + len(key)] == key) if key else 0)

    return glyphs.build_index(terms, counts)


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
    glyph_index = _glyph_index(Path(content_dir) / "lexicon", rewrites)
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
                "INSERT INTO documents(id, prefix, title, version, published, url, "
                "sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (source.id, source.prefix, source.title, source.version,
                 source.published, source.url, source.order),
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
                  _structure_json(rewrites[s.id], glyph_index)
                  if s.id in rewrites else None) for s in shipped],
            )
            shipped_ids = {s.id for s in shipped}
            # Recorded at parse time, when the body text still existed. Only
            # fall back to detecting them here when the file records none,
            # which is the full artifact rather than the committed index.
            recorded = load_xrefs(json_path)
            xref_pairs = detect_xrefs(sections) if recorded is None else recorded
            con.executemany(
                "INSERT INTO xrefs(from_id, to_id) VALUES (?, ?)",
                [(f, t) for f, t in xref_pairs
                 if f in shipped_ids and t in shipped_ids],
            )
        con.execute(
            "INSERT INTO sections_fts(rowid, title, body) "
            "SELECT rowid, title, body FROM sections"
        )
        con.commit()
    finally:
        con.close()
