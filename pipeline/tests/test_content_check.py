import json

import pytest

from rulecheck_pipeline.content_check import OVERLAP_TOKENS, check_rewrites
from rulecheck_pipeline.model import Section, SourceDoc, dump_document

SOURCE_BODY = (
    "An Active card that is Asleep is turned sideways. It cannot attack or "
    "retreat. Between turns its controller flips a coin; on heads the "
    "condition ends and the card is turned upright again."
)


def make_content(tmp_path, bodies: bool = True):
    """The committed index, with or without prose.

    `bodies=False` is what CI actually sees: the repository ships no verbatim
    text, only structure and one-way fingerprints. Several checks take a
    different path there, so the difference has to be testable.
    """
    content = tmp_path / "content"
    content.mkdir()
    source = SourceDoc(
        id="fixture-doc", prefix="fix", title="Fixture Rules", version="1.0",
        published="2026-01-01", url="https://example.com/f.pdf", file="f.pdf",
        heading_rules=[r"^(\d+)\.\s+(.+)$"],
    )
    sections = [
        Section(id="fix-1", doc_id="fixture-doc", parent_id=None, number="1",
                title="Conditions", body="", breadcrumb="Fixture Rules", order=0),
        Section(id="fix-1.1", doc_id="fixture-doc", parent_id="fix-1", number="1.1",
                title="Asleep", body=SOURCE_BODY,
                breadcrumb="Fixture Rules › Conditions", order=1),
        Section(id="fix-2", doc_id="fixture-doc", parent_id=None, number="2",
                title="Other", body="Some other rule text entirely.",
                breadcrumb="Fixture Rules", order=2),
    ]
    if bodies:
        dump_document(source, sections, content / "fixture-doc.json")
    else:
        from rulecheck_pipeline import shingles
        from rulecheck_pipeline.model import dump_index
        dump_index(source, sections, content / "fixture-doc.json")
        shingles.dump(sections, content / "fingerprints" / "fixture-doc.json")
    return content


def write_rewrites(tmp_path, entries):
    rewrites = tmp_path / "rewrites"
    rewrites.mkdir(exist_ok=True)
    (rewrites / "fixture-doc.json").write_text(json.dumps(entries))
    return rewrites


def entry(**overrides):
    base = {"archetype": "note", "tier": "standard",
            "summary": "A sideways card that skips its actions.",
            "paragraphs": ["Original wording that shares nothing substantial."]}
    base.update(overrides)
    return base


def test_clean_full_coverage_passes(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {"fix-1.1": entry(), "fix-2": entry()})
    assert check_rewrites(content, rewrites, release=True) == []


def test_coverage_gap_warns_then_errors_in_release(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {"fix-1.1": entry()})
    normal = check_rewrites(content, rewrites, release=False)
    assert any(m.startswith("warning:") and "fix-2" in m for m in normal)
    release = check_rewrites(content, rewrites, release=True)
    assert any(not m.startswith("warning:") and "fix-2" in m for m in release)


def test_entry_on_empty_body_section_is_error(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {"fix-1": entry(), "fix-1.1": entry(), "fix-2": entry()})
    assert any("fix-1:" in m and "no body" in m for m in check_rewrites(content, rewrites))


def test_container_with_body_requires_entry(tmp_path):
    """Containers carrying real prose need entries too (pilot finding)."""
    import json as _json
    content = make_content(tmp_path)
    doc = _json.loads((content / "fixture-doc.json").read_text())
    for sec in doc["sections"]:
        if sec["id"] == "fix-1":
            sec["body"] = "Overview prose that must not ship verbatim."
    (content / "fixture-doc.json").write_text(_json.dumps(doc))
    rewrites = write_rewrites(tmp_path, {"fix-1.1": entry(), "fix-2": entry()})
    release = check_rewrites(content, rewrites, release=True)
    assert any("fix-1:" in m and "coverage" in m for m in release)


def test_orphan_entry_is_error(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {"fix-9": entry(), "fix-1.1": entry(), "fix-2": entry()})
    assert any("fix-9" in m and "orphan" in m for m in check_rewrites(content, rewrites))


def test_missing_see_also_target(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(see_also=["fix-404"]), "fix-2": entry()})
    assert any("fix-404" in m for m in check_rewrites(content, rewrites))


def test_declared_quote_ok(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=['The rule says "cannot attack or retreat" here.'],
                         quotes=["cannot attack or retreat"]),
        "fix-2": entry()})
    assert check_rewrites(content, rewrites, release=True) == []


def test_quote_not_in_source_is_error(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=['It says "flip two coins" supposedly.'],
                         quotes=["flip two coins"]),
        "fix-2": entry()})
    assert any("flip two coins" in m and "source" in m for m in check_rewrites(content, rewrites))


def test_quote_unused_in_text_is_error(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(quotes=["cannot attack or retreat"]),
        "fix-2": entry()})
    assert any("unused" in m for m in check_rewrites(content, rewrites))


def lift(n: int) -> str:
    """The first n words of the fixture source, lifted verbatim.

    Derived from OVERLAP_TOKENS rather than written out. These two tests held
    hand-counted 13-word and 11-word strings, so raising the window made the
    first one stop testing anything.
    """
    return " ".join(SOURCE_BODY.split()[:n])


def test_an_undeclared_lift_the_length_of_the_window_is_an_error(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=[lift(OVERLAP_TOKENS)]), "fix-2": entry()})
    assert any("overlap" in m for m in check_rewrites(content, rewrites))


def test_a_lift_one_token_short_of_the_window_is_allowed(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=[lift(OVERLAP_TOKENS - 1)]), "fix-2": entry()})
    assert not any("overlap" in m for m in check_rewrites(content, rewrites))


def test_a_long_lift_is_allowed_once_declared_as_a_quote(tmp_path):
    """The escape hatch the Research Gate decided on and nothing ever used.
    Where the exact wording is the rule, the entry quotes it and says so."""
    content = make_content(tmp_path)
    quoted = lift(OVERLAP_TOKENS + 4)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=[quoted], quotes=[quoted]), "fix-2": entry()})
    assert not any("overlap" in m for m in check_rewrites(content, rewrites))


def test_judge_review_gate_release_only(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(tier="judge"), "fix-2": entry()})
    assert not any("review" in m for m in check_rewrites(content, rewrites, release=False)
                   if not m.startswith("warning:"))
    assert any("review" in m for m in check_rewrites(content, rewrites, release=True))


def test_invalid_entry_errors_propagate(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": {"archetype": "saga", "tier": "standard"}, "fix-2": entry()})
    assert any("archetype" in m for m in check_rewrites(content, rewrites))


def test_skip_satisfies_coverage(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(), "fix-2": {"skip": "colophon, no rules content"}})
    assert check_rewrites(content, rewrites, release=True) == []


def test_skip_on_missing_section_is_orphan(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(), "fix-2": entry(), "fix-99": {"skip": "gone"}})
    assert any("fix-99" in m and "orphan" in m for m in check_rewrites(content, rewrites))


def test_see_also_pointing_at_skipped_section_fails(tmp_path):
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(see_also=["fix-2"]),
        "fix-2": {"skip": "not shipped"}})
    assert any("fix-2" in m and "skipped" in m for m in check_rewrites(content, rewrites))


# --- issue #43: a short declared quote cannot be checked without the text ---

def test_a_short_quote_is_reported_as_unverifiable_without_the_text(tmp_path):
    """The silent hole. A quote below the fingerprint window cannot be
    checked at all in CI, because a run shorter than the window produces no
    shingle. An invented quote about a goldfish passed without a word."""
    content = make_content(tmp_path, bodies=False)
    quoted = "cannot attack"                      # 2 tokens, far below the window
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=[quoted], quotes=[quoted]), "fix-2": entry()})
    messages = check_rewrites(content, rewrites)
    assert any("cannot be verified" in m and "cannot attack" in m for m in messages)


def test_the_unverifiable_report_is_a_warning_not_an_error(tmp_path):
    """It must not fail an ordinary build. The quote may be perfectly good and
    the checker simply has no way to look."""
    content = make_content(tmp_path, bodies=False)
    quoted = "cannot attack"
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=[quoted], quotes=[quoted]), "fix-2": entry()})
    messages = check_rewrites(content, rewrites)
    unverifiable = [m for m in messages if "cannot be verified" in m]
    assert unverifiable and all(m.startswith("warning:") for m in unverifiable)


def test_an_unverifiable_quote_fails_a_release(tmp_path):
    """Shipping a quote nobody has checked against the source is exactly what
    the release gate is for."""
    content = make_content(tmp_path, bodies=False)
    quoted = "cannot attack"
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=[quoted], quotes=[quoted]), "fix-2": entry()})
    messages = check_rewrites(content, rewrites, release=True)
    assert any("cannot be verified" in m and not m.startswith("warning:")
               for m in messages)


def test_a_short_quote_is_checked_exactly_when_the_text_is_present(tmp_path):
    """Locally, with the PDFs, nothing changes: the quote is still verified
    against the real source and a false one still fails."""
    content = make_content(tmp_path)
    rewrites = write_rewrites(tmp_path, {
        "fix-1.1": entry(paragraphs=["it cannot fly"], quotes=["it cannot fly"]),
        "fix-2": entry()})
    assert any("not found in source text" in m for m in check_rewrites(content, rewrites))
