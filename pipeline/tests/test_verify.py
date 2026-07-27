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
    con.execute("DELETE FROM sections WHERE id = 'fix-2'")
    con.commit(); con.close()
    errors = verify_db(db_path)
    assert any("fts" in e.lower() for e in errors)


def test_orphan_parent_fails(fixture_pdf, fixture_source, tmp_path):
    db_path = make_db(fixture_pdf, fixture_source, tmp_path)
    con = sqlite3.connect(db_path)
    con.execute("UPDATE sections SET parent_id = 'fix-9.9' WHERE id = 'fix-3.2'")
    con.commit(); con.close()
    errors = verify_db(db_path)
    assert any("fix-9.9" in e and "parent" in e for e in errors)


def test_document_without_sections_fails(fixture_pdf, fixture_source, tmp_path):
    db_path = make_db(fixture_pdf, fixture_source, tmp_path)
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO documents VALUES "
        "('empty-doc', 'emp', 'Empty Doc', '1.0', '2026-01-01', 'https://example.com/e.pdf')"
    )
    con.commit(); con.close()
    errors = verify_db(db_path)
    assert any("empty-doc" in e and "no sections" in e for e in errors)
