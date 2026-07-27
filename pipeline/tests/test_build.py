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
