import sqlite3

from rulecheck_pipeline.build import build_db
from rulecheck_pipeline.model import dump_document
from rulecheck_pipeline.parse import parse_pdf


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
