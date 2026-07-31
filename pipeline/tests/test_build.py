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
    "documents": ["id", "prefix", "title", "version", "published", "url", "sort_order"],
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


# --- glyph annotation (spec: 2026-07-31-glyph-rendering-design.md) ---

GLYPH_ENTRY = {
    "archetype": "mechanic", "tier": "standard",
    "summary": "Asleep stops a Pokemon acting.",
    "state": ["No attacking", "Rotated counterclockwise"],
    "branch": {"when": "Pokemon Checkup",
               "options": [{"condition": "Heads", "outcome": "Wakes up"},
                           {"condition": "Tails", "outcome": "Still Asleep"}]},
}
PLAIN_ENTRY = {"archetype": "note", "tier": "standard",
               "summary": "Nothing structured here.", "paragraphs": ["p"]}


def _glyph_fixture(tmp_path, entry, with_lexicon=True):
    """A one-section corpus, its rewrite entry, and optionally a lexicon."""
    from rulecheck_pipeline.model import Section, SourceDoc, dump_index

    source = SourceDoc(id="fix", prefix="fix", title="Fixture", version="1",
                       published="2026-01-01", url="https://example.com/f.pdf",
                       file="f.pdf", heading_rules=[])
    sections = [Section(id="fix-1", doc_id="fix", parent_id=None, number="1",
                        title="One", breadcrumb="Fixture", order=0, body="Body.")]
    content = tmp_path / "content"
    dump_index(source, sections, content / "fix.json")

    rewrites = tmp_path / "rewrites"
    rewrites.mkdir()
    (rewrites / "fix.json").write_text(json.dumps({"fix-1": entry}))

    if with_lexicon:
        lex = content / "lexicon"
        lex.mkdir(parents=True)
        (lex / "l.json").write_text(json.dumps({"terms": [
            {"term": "asleep", "category": "state", "gloss": "g",
             "glyph": True, "glyph_render": {"symbol": "moon.zzz"}},
            {"term": "blocked", "category": "modifier", "gloss": "g",
             "glyph": True, "glyph_render": {"symbol": "nosign"},
             "glyph_triggers": ["no attacking"]},
            {"term": "tails", "category": "state", "gloss": "g",
             "glyph": True, "glyph_render": {"chip": "TAILS", "tint": "accent"}},
        ], "declined": []}))
    return content, rewrites


def _structure_of(db_path, sid="fix-1"):
    con = sqlite3.connect(db_path)
    row = con.execute("select structure from sections where id = ?", (sid,)).fetchone()
    con.close()
    return json.loads(row[0]) if row and row[0] else None


def test_glyph_arrays_align_with_their_field(tmp_path):
    content, rewrites = _glyph_fixture(tmp_path, GLYPH_ENTRY)
    build_db(content, tmp_path / "out.db", rewrites_dir=rewrites)
    s = _structure_of(tmp_path / "out.db")
    assert len(s["state_glyphs"]) == len(GLYPH_ENTRY["state"])
    assert len(s["branch_glyphs"]) == len(GLYPH_ENTRY["branch"]["options"])


def test_a_row_with_no_glyph_gets_null_not_a_gap(tmp_path):
    """A gap would slide every later glyph onto the wrong row."""
    content, rewrites = _glyph_fixture(tmp_path, GLYPH_ENTRY)
    build_db(content, tmp_path / "out.db", rewrites_dir=rewrites)
    assert _structure_of(tmp_path / "out.db")["state_glyphs"] == ["blocked", None]


def test_the_rarer_concept_wins_a_tie(tmp_path):
    """Needs occurrence counts computed from the corpus. Without them the tie
    breaks alphabetically and "Tails, Still Asleep" draws the Asleep glyph,
    because "asleep" sorts before "tails"."""
    content, rewrites = _glyph_fixture(tmp_path, GLYPH_ENTRY)
    build_db(content, tmp_path / "out.db", rewrites_dir=rewrites)
    assert _structure_of(tmp_path / "out.db")["branch_glyphs"][1] == "tails"


def test_an_entry_with_no_structured_fields_gets_no_arrays(tmp_path):
    content, rewrites = _glyph_fixture(tmp_path, PLAIN_ENTRY)
    build_db(content, tmp_path / "out.db", rewrites_dir=rewrites)
    s = _structure_of(tmp_path / "out.db")
    assert not any(k.endswith("_glyphs") for k in s)


def test_building_without_a_lexicon_still_works(tmp_path):
    """A fresh clone, or any build predating the lexicon, must not fail."""
    content, rewrites = _glyph_fixture(tmp_path, GLYPH_ENTRY, with_lexicon=False)
    build_db(content, tmp_path / "out.db", rewrites_dir=rewrites)
    s = _structure_of(tmp_path / "out.db")
    assert not any(k.endswith("_glyphs") for k in s)


def test_the_authored_files_are_never_written_back(tmp_path):
    """rewrites/ is hand-authored. Annotation happens on the way into the
    database and nowhere else."""
    content, rewrites = _glyph_fixture(tmp_path, GLYPH_ENTRY)
    before = (rewrites / "fix.json").read_text()
    build_db(content, tmp_path / "out.db", rewrites_dir=rewrites)
    assert (rewrites / "fix.json").read_text() == before


def test_building_twice_produces_identical_structure(tmp_path):
    content, rewrites = _glyph_fixture(tmp_path, GLYPH_ENTRY)
    build_db(content, tmp_path / "a.db", rewrites_dir=rewrites)
    build_db(content, tmp_path / "b.db", rewrites_dir=rewrites)
    assert _structure_of(tmp_path / "a.db") == _structure_of(tmp_path / "b.db")
