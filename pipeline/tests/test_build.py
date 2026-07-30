import dataclasses
import json
import sqlite3

import pytest

from rulecheck_pipeline.build import build_db
from rulecheck_pipeline.model import dump_document
from rulecheck_pipeline.parse import parse_pdf

# The shipped schema is the contract with the iOS app. Column names and order
# are pinned here so a change to either is a deliberate edit to this list, made
# in the same PR as the app-side change (see CLAUDE.md).
EXPECTED_COLUMNS = {
    "documents": ["id", "prefix", "title", "version", "published", "url"],
    "sections": ["id", "doc_id", "parent_id", "number", "title", "body",
                 "breadcrumb", "sort_order", "structure"],
    "xrefs": ["from_id", "to_id"],
}


def test_build_db(fixture_pdf, fixture_source, tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")

    db_path = tmp_path / "rulecheck.db"
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
    db_path = tmp_path / "rulecheck.db"
    build_db(content_dir, db_path)
    build_db(content_dir, db_path)  # second build must not duplicate rows
    con = sqlite3.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM sections").fetchone()[0] == 5
    con.close()


def test_build_substitutes_flattened_rewrite_body(fixture_pdf, fixture_source, tmp_path):
    import json

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")

    rewrites_dir = tmp_path / "rewrites"
    rewrites_dir.mkdir()
    (rewrites_dir / "fixture-doc.json").write_text(json.dumps({
        "fix-3.2": {"archetype": "note", "tier": "standard",
                    "summary": "Structured summary.",
                    "paragraphs": ["Structured body line."]}}))

    db_path = tmp_path / "rulecheck.db"
    build_db(content_dir, db_path, rewrites_dir=rewrites_dir)
    con = sqlite3.connect(db_path)
    body = con.execute("SELECT body FROM sections WHERE id='fix-3.2'").fetchone()[0]
    other = con.execute("SELECT body FROM sections WHERE id='fix-1.1'").fetchone()[0]
    con.close()
    assert body == "Structured summary.\nStructured body line."
    assert "prize cards" in other  # untouched verbatim


def test_skipped_sections_are_excluded_from_db(fixture_pdf, fixture_source, tmp_path):
    import json

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")

    rewrites_dir = tmp_path / "rewrites"
    rewrites_dir.mkdir()
    (rewrites_dir / "fixture-doc.json").write_text(json.dumps({
        "fix-3.2": {"skip": "diagram furniture, never shipped"}}))

    db_path = tmp_path / "rulecheck.db"
    build_db(content_dir, db_path, rewrites_dir=rewrites_dir)
    con = sqlite3.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM sections WHERE id='fix-3.2'").fetchone()[0] == 0
    assert con.execute(
        "SELECT COUNT(*) FROM sections_fts WHERE sections_fts MATCH 'asleep'").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM sections").fetchone()[0] == 4
    con.close()


def test_structure_column_carries_the_authored_entry(fixture_pdf, fixture_source, tmp_path):
    import json

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")

    entry = {"archetype": "mechanic", "tier": "standard", "summary": "Structured.",
             "state": ["A fact"], "effects": {"Attack": "Blocked"}}
    rewrites_dir = tmp_path / "rewrites"
    rewrites_dir.mkdir()
    (rewrites_dir / "fixture-doc.json").write_text(json.dumps({"fix-3.2": entry}))

    db_path = tmp_path / "rulecheck.db"
    build_db(content_dir, db_path, rewrites_dir=rewrites_dir)
    con = sqlite3.connect(db_path)
    raw = con.execute("SELECT structure FROM sections WHERE id='fix-3.2'").fetchone()[0]
    assert json.loads(raw) == entry
    # sections without an entry carry no structure
    assert con.execute("SELECT structure FROM sections WHERE id='fix-1.1'").fetchone()[0] is None
    # the flattened text still drives search
    assert "Structured." in con.execute(
        "SELECT body FROM sections WHERE id='fix-3.2'").fetchone()[0]
    con.close()


def test_schema_column_names_and_order_are_the_contract(fixture_pdf, fixture_source, tmp_path):
    """Pins the iOS-facing shape. Naming the columns in the INSERT statements
    means a column can later be added without silently shifting values into
    the wrong ones — this test is what makes such a change visible."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    dump_document(fixture_source, parse_pdf(fixture_pdf, fixture_source),
                  content_dir / "fixture-doc.json")
    db_path = tmp_path / "rulecheck.db"
    build_db(content_dir, db_path)

    con = sqlite3.connect(db_path)
    for table, columns in EXPECTED_COLUMNS.items():
        actual = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
        assert actual == columns, f"{table} schema changed — update the app in the same PR"
    con.close()


def _write_content(content_dir, fixture_source, section):
    content_dir.mkdir()
    (content_dir / "fixture-doc.json").write_text(json.dumps({
        "document": dataclasses.asdict(fixture_source),
        "sections": [{"number": "1", "title": "Setup", "breadcrumb": "Setup",
                      "order": 0, "body": "Body text.", "body_chars": 10, **section}],
    }))


def test_build_rejects_a_dangling_parent_reference(fixture_source, tmp_path):
    """`sections.parent_id REFERENCES sections(id)` is only enforced when the
    connection asks for it. Without the pragma a broken tree lands in the
    shipped DB and only surfaces later — in verify, or in the app."""
    content_dir = tmp_path / "content"
    _write_content(content_dir, fixture_source, {
        "id": "fix-1.1", "doc_id": "fixture-doc", "parent_id": "fix-9.9"})
    with pytest.raises(sqlite3.IntegrityError):
        build_db(content_dir, tmp_path / "rulecheck.db")


def test_build_rejects_a_section_pointing_at_an_unknown_document(fixture_source, tmp_path):
    """Same pragma, the other declared reference: `sections.doc_id`."""
    content_dir = tmp_path / "content"
    _write_content(content_dir, fixture_source, {
        "id": "fix-1", "doc_id": "no-such-doc", "parent_id": None})
    with pytest.raises(sqlite3.IntegrityError):
        build_db(content_dir, tmp_path / "rulecheck.db")


def test_xrefs_survive_a_bodies_free_index(tmp_path):
    """Cross-references must reach the app even though the committed index
    carries no prose.

    Detection needs body text, and since the verbatim bodies left the
    repository the index has none. Detecting at build time therefore found
    nothing and shipped an empty xrefs table, silently killing the reader's
    "See also" section. Detection now happens at parse time, when the text is
    still in hand, and the resulting pairs travel in the index.
    """
    from rulecheck_pipeline.model import Section, SourceDoc, dump_index

    source = SourceDoc(id="fix", prefix="fix", title="Fixture", version="1",
                       published="2026-01-01", url="https://example.com/f.pdf",
                       file="f.pdf", heading_rules=[])
    sections = [
        Section(id="fix-1", doc_id="fix", parent_id=None, number="1",
                title="One", breadcrumb="Fixture", order=0,
                body="See section 2 for details."),
        Section(id="fix-2", doc_id="fix", parent_id=None, number="2",
                title="Two", breadcrumb="Fixture", order=1, body="Details."),
    ]
    content = tmp_path / "content"
    dump_index(source, sections, content / "fix.json", xrefs=[("fix-1", "fix-2")])

    # Both sections are authored, matching the real corpus. Without entries
    # the build correctly refuses, since the index carries no prose to ship.
    rewrites = tmp_path / "rewrites"
    rewrites.mkdir()
    (rewrites / "fix.json").write_text(json.dumps({
        sid: {"archetype": "note", "tier": "standard",
              "summary": "s", "paragraphs": ["p"]}
        for sid in ("fix-1", "fix-2")}))

    db = tmp_path / "out.db"
    build_db(content, db, rewrites_dir=rewrites)

    con = sqlite3.connect(db)
    rows = con.execute("SELECT from_id, to_id FROM xrefs").fetchall()
    con.close()
    assert rows == [("fix-1", "fix-2")], "xrefs lost between parse and build"
