"""Tests for the corroboration search.

The questions here are the ones the pilot review of the game rules actually
asked, which is why this script exists.
"""

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "corroborate.py"
spec = importlib.util.spec_from_file_location("corroborate", SCRIPT)
corr = importlib.util.module_from_spec(spec)
sys.modules["corroborate"] = corr
spec.loader.exec_module(corr)


def make_root(tmp_path, source=None, entries=None):
    (tmp_path / "rewrites").mkdir()
    (tmp_path / "rewrites" / "doc.json").write_text(json.dumps(entries or {}))
    if source is not None:
        full = tmp_path / "build" / "content"
        full.mkdir(parents=True)
        sections = [{"id": sid, "body": body} for sid, body in source.items()]
        (full / "doc.json").write_text(json.dumps({"sections": sections}))
    return tmp_path


def test_it_finds_a_claim_supported_somewhere_else_in_the_source(tmp_path):
    """The reviewer's most common question. The entry under review does not
    say the discard pile is public; another section does."""
    root = make_root(tmp_path, source={
        "zones": "Your discard pile sits beside your deck.",
        "glossary": "The discard pile is kept face up and either player may look at it.",
    })
    hits = corr.search(*corr.build_index(root)[:1], ["discard", "face", "up"])
    assert [h["section"] for h in hits] == ["glossary"]


def test_inflections_match_so_a_search_is_not_defeated_by_a_plural(tmp_path):
    """grep for "damage counter" misses "damage counters", which is how a
    real corroboration gets missed and a good entry gets flagged."""
    root = make_root(tmp_path, source={"s": "Place two damage counters on it."})
    hits = corr.search(*corr.build_index(root)[:1], ["damage", "counter"])
    assert [h["section"] for h in hits] == ["s"]


def test_a_claim_only_we_make_is_reported_as_ours_alone(tmp_path):
    """This is what INVENTION looks like from the outside: our text says it,
    no source section does."""
    root = make_root(tmp_path,
                     source={"s": "A Pokemon that is Asleep cannot attack."},
                     entries={"s": {"summary": "Abilities still work while Asleep."}})
    index, _ = corr.build_index(root)
    hits = corr.search(index, ["abilities", "asleep"])
    assert len(hits) == 1
    # Both mention Asleep. Only our entry mentions Abilities, and that word
    # is the whole claim.
    assert "ability" in hits[0]["authored"]
    assert "ability" not in hits[0]["source"]


def test_requiring_every_word_excludes_a_partial_match(tmp_path):
    root = make_root(tmp_path, source={"a": "mulligan rules", "b": "mulligan"})
    index, _ = corr.build_index(root)
    assert [h["section"] for h in corr.search(index, ["mulligan", "rules"])] == ["a"]


def test_any_mode_returns_partial_matches_too(tmp_path):
    root = make_root(tmp_path, source={"a": "mulligan rules", "b": "mulligan"})
    index, _ = corr.build_index(root)
    hits = corr.search(index, ["mulligan", "rules"], match_all=False)
    assert {h["section"] for h in hits} == {"a", "b"}


def test_the_best_match_comes_first(tmp_path):
    root = make_root(tmp_path, source={"weak": "mulligan", "strong": "mulligan rules"})
    index, _ = corr.build_index(root)
    hits = corr.search(index, ["mulligan", "rules"], match_all=False)
    assert hits[0]["section"] == "strong"


def test_a_skipped_entry_is_not_searched(tmp_path):
    """A skipped entry ships nothing, so it cannot corroborate anything."""
    root = make_root(tmp_path, entries={"s": {"skip": "index page"},
                                        "t": {"summary": "mulligan"}})
    index, _ = corr.build_index(root)
    assert [h["section"] for h in corr.search(index, ["mulligan"])] == ["t"]


def test_it_still_works_without_the_parse_artifact(tmp_path):
    """The PDFs are git-ignored, so a fresh clone has no source text. Search
    our own entries rather than failing."""
    root = make_root(tmp_path, entries={"s": {"summary": "Take a mulligan."}})
    index, have_source = corr.build_index(root)
    assert have_source is False
    assert [h["section"] for h in corr.search(index, ["mulligan"])] == ["s"]


def test_citation_fields_are_not_searched_as_prose(tmp_path):
    """see_also holds section ids, not statements. Counting them as text
    would report a section as corroborating a claim it only links to."""
    root = make_root(tmp_path, entries={"s": {"summary": "Nothing here.",
                                              "see_also": ["tcg-mulligan"]}})
    index, _ = corr.build_index(root)
    assert corr.search(index, ["mulligan"]) == []


def test_words_scattered_far_apart_are_not_one_statement(tmp_path):
    """Both reviewers hit this. A section can run to 100,000 characters, so
    words a page apart share the section and nothing else, and the tool
    reported that as a match."""
    far = "alpha " + ("filler " * 300) + "omega"
    root = make_root(tmp_path, source={"long": far, "tight": "alpha omega"})
    index, _ = corr.build_index(root)
    assert [h["section"] for h in corr.search(index, ["alpha", "omega"])] == ["tight"]


def test_a_wide_enough_window_still_finds_the_scattered_case(tmp_path):
    far = "alpha " + ("filler " * 300) + "omega"
    root = make_root(tmp_path, source={"long": far})
    index, _ = corr.build_index(root)
    assert corr.search(index, ["alpha", "omega"], window=None)
    assert corr.search(index, ["alpha", "omega"], window=400)


def test_the_closest_match_ranks_first(tmp_path):
    root = make_root(tmp_path, source={
        "loose": "alpha " + ("filler " * 20) + "omega",
        "tight": "alpha omega",
    })
    index, _ = corr.build_index(root)
    hits = corr.search(index, ["alpha", "omega"], window=100)
    assert [h["section"] for h in hits] == ["tight", "loose"]


def test_it_quotes_the_text_that_matched(tmp_path):
    """"This section mentions those words" is not an answer. The reviewer
    needs the sentence to judge it."""
    root = make_root(tmp_path, source={
        "s": "Filler before. A competitor causes their system to lose power. Filler after."})
    index, _ = corr.build_index(root)
    hit = corr.search(index, ["competitor", "causes", "power"])[0]
    assert "causes their system to lose power" in hit["quote"]
    assert hit["quote_from"] == "source"


def test_the_quote_says_which_side_it_came_from(tmp_path):
    root = make_root(tmp_path, entries={"s": {"summary": "Take a mulligan now."}})
    index, _ = corr.build_index(root)
    hit = corr.search(index, ["mulligan"])[0]
    assert hit["quote_from"] == "authored"


def test_tightest_window_finds_the_smallest_span(tmp_path):
    marks = corr.stems_with_offsets("alpha gap gap omega alpha omega")
    span, _, _ = corr.tightest_window(marks, {"alpha", "omega"})
    assert span == 2, "the later, closer pair should win"
