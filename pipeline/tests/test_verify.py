import sqlite3

import pytest

from rulecheck_pipeline.build import build_db
from rulecheck_pipeline.model import dump_document
from rulecheck_pipeline.parse import parse_pdf
from rulecheck_pipeline.verify import verify_db


def make_db(fixture_pdf, fixture_source, tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    sections = parse_pdf(fixture_pdf, fixture_source)
    dump_document(fixture_source, sections, content_dir / "fixture-doc.json")
    db_path = tmp_path / "rulecheck.db"
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


def test_unrelated_db_error_is_not_reported_as_fts_desync(fixture_pdf, fixture_source, tmp_path):
    """The integrity-check probe reports a desynced index as SQLITE_CORRUPT_VTAB.
    A missing table is a different failure — a file that is not our artifact —
    and must not be dressed up as a content problem verify can report on."""
    db_path = make_db(fixture_pdf, fixture_source, tmp_path)
    con = sqlite3.connect(db_path)
    con.execute("DROP TABLE sections_fts")
    con.commit(); con.close()
    with pytest.raises(sqlite3.OperationalError, match="sections_fts"):
        verify_db(db_path)


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
        "INSERT INTO documents(id, prefix, title, version, published, url, sort_order) "
        "VALUES ('empty-doc', 'emp', 'Empty Doc', '1.0', '2026-01-01', "
        "'https://example.com/e.pdf', 99)"
    )
    con.commit(); con.close()
    errors = verify_db(db_path)
    assert any("empty-doc" in e and "no sections" in e for e in errors)
