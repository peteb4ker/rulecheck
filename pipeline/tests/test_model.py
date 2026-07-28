from rulecheck_pipeline.model import Section, SourceDoc, dump_document, load_document

SOURCE = SourceDoc(
    id="fixture-doc", prefix="fix", title="Fixture Rules Document",
    version="1.0", published="2026-01-01", url="https://example.com/fixture.pdf",
    file="fixture.pdf", heading_rules=[r"^(\d+)\.\s+(.+)$"],
)

SECTIONS = [
    Section(id="fix-1", doc_id="fixture-doc", parent_id=None, number="1",
            title="Setup", body="Shuffle your deck.", breadcrumb="Fixture Rules Document",
            order=0),
    Section(id="fix-1.1", doc_id="fixture-doc", parent_id="fix-1", number="1.1",
            title="Prizes", body="Set aside 6 prize cards.",
            breadcrumb="Fixture Rules Document › Setup", order=1),
]


def test_round_trip(tmp_path):
    path = tmp_path / "fixture-doc.json"
    dump_document(SOURCE, SECTIONS, path)
    source2, sections2 = load_document(path)
    assert source2 == SOURCE
    assert sections2 == SECTIONS


def test_json_is_stable_and_readable(tmp_path):
    path = tmp_path / "fixture-doc.json"
    dump_document(SOURCE, SECTIONS, path)
    text = path.read_text()
    assert '"id": "fix-1"' in text          # indent + sorted keys → diffable
    dump_document(SOURCE, SECTIONS, path)   # writing twice is byte-identical
    assert path.read_text() == text
