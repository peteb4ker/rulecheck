import dataclasses

from benchside_pipeline.parse import build_tree, extract_lines, parse_pdf


def test_extract_lines(fixture_pdf):
    lines = extract_lines(fixture_pdf)
    assert "1. Setup" in [l.strip() for l in lines]
    assert any("wakes up" in l for l in lines)


def test_tree_structure(fixture_pdf, fixture_source):
    sections = parse_pdf(fixture_pdf, fixture_source)
    ids = [s.id for s in sections]
    assert ids == ["fix-1", "fix-1.1", "fix-2", "fix-3", "fix-3.2"]
    by_id = {s.id: s for s in sections}
    assert by_id["fix-1.1"].parent_id == "fix-1"
    assert by_id["fix-3.2"].parent_id == "fix-3"
    assert by_id["fix-2"].parent_id is None
    assert by_id["fix-3.2"].title == "Asleep"
    assert "wakes up" in by_id["fix-3.2"].body
    assert by_id["fix-3.2"].breadcrumb == "Fixture Rules Document › Special Conditions"
    assert [s.order for s in sections] == [0, 1, 2, 3, 4]


def test_sibling_replaces_sibling(fixture_source):
    lines = ["1. Alpha", "body a", "2. Beta", "body b"]
    sections = build_tree(lines, fixture_source)
    assert [s.id for s in sections] == ["fix-1", "fix-2"]
    assert sections[1].parent_id is None


def test_repeated_heading_number_becomes_body_text(fixture_source, capsys):
    # Some real documents (e.g. a "Summary of Changes" table) repeat an
    # earlier heading's number as plain content later on -- sometimes with
    # the same title, sometimes (as here) with a different one, e.g. a real
    # "1 Introduction & Using This Handbook" heading followed later by a
    # changelog row that just says "1. Using This Handbook". Either way the
    # second occurrence must not create a second section with the same id
    # (which would collide as a duplicate primary key at build time), and
    # because the guard matches on number only -- not number+title -- it
    # must warn so the suppression is auditable.
    lines = [
        "1. Alpha", "body a",
        "2. Beta", "body b",
        "1. Using This Handbook", "changelog note about Alpha",
    ]
    sections = build_tree(lines, fixture_source)
    assert [s.id for s in sections] == ["fix-1", "fix-2"]
    by_id = {s.id: s for s in sections}
    assert "changelog note about Alpha" in by_id["fix-2"].body

    err = capsys.readouterr().err
    assert "warning" in err
    assert "fix-1" in err
    assert "Using This Handbook" in err


def test_strip_lines_removes_matching_lines(fixture_source):
    source = dataclasses.replace(
        fixture_source, strip_lines=[r"^PAGE FOOTER \d+$"]
    )
    lines = [
        "1. Alpha", "body a", "PAGE FOOTER 1", "more body a",
        "2. Beta", "PAGE FOOTER 2", "body b",
    ]
    sections = build_tree(lines, source)
    by_id = {s.id: s for s in sections}
    assert "PAGE FOOTER" not in by_id["fix-1"].body
    assert "body a" in by_id["fix-1"].body
    assert "more body a" in by_id["fix-1"].body
