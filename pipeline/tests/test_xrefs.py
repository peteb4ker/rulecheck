from benchside_pipeline.model import Section
from benchside_pipeline.xrefs import detect_xrefs


def sec(id, number, body, doc_id="fixture-doc"):
    return Section(id=id, doc_id=doc_id, parent_id=None, number=number,
                   title=f"S{number}", body=body, breadcrumb="", order=0)


def test_detects_reference():
    sections = [
        sec("fix-1.1", "1.1", "See section 3.2 for conditions."),
        sec("fix-3.2", "3.2", "Flip a coin."),
    ]
    assert detect_xrefs(sections) == [("fix-1.1", "fix-3.2")]


def test_ignores_missing_target_and_self():
    sections = [sec("fix-1", "1", "See section 9.9. Also see Section 1 itself.")]
    assert detect_xrefs(sections) == []


def test_dedupes():
    sections = [
        sec("fix-1", "1", "See section 2. Again, see section 2."),
        sec("fix-2", "2", "body"),
    ]
    assert detect_xrefs(sections) == [("fix-1", "fix-2")]


def test_same_document_only():
    sections = [
        sec("fix-1", "1", "See section 2.", doc_id="doc-a"),
        sec("oth-2", "2", "body", doc_id="doc-b"),
    ]
    assert detect_xrefs(sections) == []


def test_ignores_substring_matches():
    sections = [
        sec("fix-1", "1", "See Subsection 3.2 and the intersection 3.2 case."),
        sec("fix-3.2", "3.2", "body"),
    ]
    assert detect_xrefs(sections) == []
