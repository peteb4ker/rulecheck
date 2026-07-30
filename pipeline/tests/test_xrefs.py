from rulecheck_pipeline.model import Section
from rulecheck_pipeline.xrefs import detect_xrefs


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


def test_reference_scoped_to_another_document_is_not_a_local_xref():
    """"section 1 of appendix A ... in the Play! Pokemon VG Rules and Formats
    handbook" points at a different document. Matching the bare "section 1"
    mapped it to this document's section 1, sending a judge to an unrelated
    rule. A wrong pointer is worse than no pointer."""
    sections = [
        sec("pen-1", "1", ""),
        sec("pen-2", "2", ""),
        sec("pen-5.6.2", "5.6.2",
            "A Pokemon appears in section 1 of appendix A (Manual Team Checking) "
            "in the Play! Pokemon VG Rules and Formats handbook, and also in "
            "section 2 of Appendix A."),
    ]
    assert detect_xrefs(sections) == []


def test_a_genuine_local_reference_is_still_detected():
    sections = [
        sec("pen-1", "1", ""),
        sec("pen-4", "4", "Apply the tiers in section 1."),
    ]
    assert detect_xrefs(sections) == [("pen-4", "pen-1")]


def test_a_section_heading_on_its_own_line_is_not_a_reference():
    """The penalty guidelines appendix is internally divided by lines reading
    exactly "Section 1" and "Section 2". Those are its own headings, not
    references to the document's sections 1 and 2, and treating them as
    references pointed judges at unrelated rules."""
    sections = [
        sec("pen-1", "1", ""),
        sec("pen-2", "2", ""),
        sec("pen-Appendix A", "Appendix A",
            "Known examples of illegal manipulation.\n"
            "Section 1\n"
            "Any competitor found to have such a team has committed an error.\n"
            "Section 2\n"
            "Any competitor found to have one of these has committed an error."),
    ]
    assert detect_xrefs(sections) == []


def test_a_reference_wrapped_onto_a_new_line_is_still_detected():
    """Guards the fix above: a heading is a line that is *only* the reference.
    A wrapped line beginning with a reference still carries prose after it."""
    sections = [
        sec("pen-1", "1", ""),
        sec("pen-4", "4", "The penalty tiers are described in\nsection 1 of this document."),
    ]
    assert detect_xrefs(sections) == [("pen-4", "pen-1")]
