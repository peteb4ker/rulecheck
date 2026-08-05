"""Tests for the lexicon buddy script's glyph checks.

The script's job is to catch what reading the lexicon cannot: a rendering
that names something absent from the corpus, or two concepts that would be
indistinguishable on screen.
"""

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_lexicon.py"
spec = importlib.util.spec_from_file_location("check_lexicon", SCRIPT)
cl = importlib.util.module_from_spec(spec)
sys.modules["check_lexicon"] = cl
spec.loader.exec_module(cl)


# The corpus these tests check triggers against, already stemmed the way the
# script stems it.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rulecheck_pipeline.lexicon import stem as _stem, tokenize as _tok  # noqa: E402

STEMS = [_stem(w) for w in _tok("A Pokemon that is asleep cannot attack or retreat.")]


def make_root(tmp_path, terms, corpus_text="A Pokemon that is asleep cannot attack."):
    (tmp_path / "content" / "lexicon").mkdir(parents=True)
    (tmp_path / "content" / "lexicon" / "l.json").write_text(
        json.dumps({"terms": terms, "declined": []}))
    (tmp_path / "rewrites").mkdir()
    (tmp_path / "rewrites" / "d.json").write_text(
        json.dumps({"s1": {"archetype": "mechanic", "tier": "standard",
                           "summary": corpus_text}}))
    return tmp_path


def test_a_trigger_that_never_occurs_is_an_error(tmp_path):
    """The same failure an invented term gets. A trigger naming a phrase the
    corpus never uses renders nothing and nobody would notice."""
    terms = [{"term": "asleep", "category": "state", "gloss": "g",
              "glyph": True, "glyph_render": {"symbol": "moon.zzz"},
              "glyph_triggers": ["turned sideways"]}]
    problems = cl.glyph_problems(terms, STEMS)
    assert any("turned sideways" in p and "never occurs" in p for p in problems)


def test_a_trigger_that_occurs_is_accepted(tmp_path):
    terms = [{"term": "asleep", "category": "state", "gloss": "g",
              "glyph": True, "glyph_render": {"symbol": "moon.zzz"},
              "glyph_triggers": ["cannot attack"]}]
    assert cl.glyph_problems(terms, STEMS) == []


def test_two_terms_sharing_a_symbol_is_an_error():
    """Two concepts drawing the same picture are indistinguishable on screen,
    which defeats the point of having a glyph at all."""
    terms = [
        {"term": "asleep", "category": "state", "gloss": "g",
         "glyph": True, "glyph_render": {"symbol": "moon.zzz"}},
        {"term": "confused", "category": "state", "gloss": "g",
         "glyph": True, "glyph_render": {"symbol": "moon.zzz"}},
    ]
    problems = cl.glyph_problems(terms, STEMS)
    assert any("moon.zzz" in p and "both" in p for p in problems)


def test_two_terms_may_share_a_chip_tint():
    """Tints are shared on purpose. A player should learn four colours, not
    thirty, so this must not be reported."""
    terms = [
        {"term": "heads", "category": "state", "gloss": "g",
         "glyph": True, "glyph_render": {"chip": "HEADS", "tint": "accent"}},
        {"term": "tails", "category": "state", "gloss": "g",
         "glyph": True, "glyph_render": {"chip": "TAILS", "tint": "accent"}},
    ]
    assert cl.glyph_problems(terms, STEMS) == []


def test_two_terms_sharing_chip_text_is_an_error():
    """Same reasoning as symbols: identical chips cannot be told apart."""
    terms = [
        {"term": "prize card", "category": "entity", "gloss": "g",
         "glyph": True, "glyph_render": {"chip": "PRIZE", "tint": "secondary"}},
        {"term": "prize", "category": "entity", "gloss": "g",
         "glyph": True, "glyph_render": {"chip": "PRIZE", "tint": "negative"}},
    ]
    problems = cl.glyph_problems(terms, STEMS)
    assert any("PRIZE" in p and "both" in p for p in problems)


def test_an_undecided_term_needs_no_checks():
    """Its chip is derived from its own term, so there is nothing to collide
    and nothing to verify."""
    terms = [{"term": "damage counter", "category": "entity", "gloss": "g",
              "glyph": "undecided"}]
    assert cl.glyph_problems(terms, STEMS) == []


def test_a_held_out_term_needs_no_checks():
    terms = [{"term": "attack", "category": "action", "gloss": "g",
              "glyph": False, "glyph_note": "too common"}]
    assert cl.glyph_problems(terms, STEMS) == []


def test_a_term_with_no_glyph_key_needs_no_checks():
    terms = [{"term": "bye", "category": "entity", "gloss": "g"}]
    assert cl.glyph_problems(terms, STEMS) == []


# --- what should actually fail a build ---

def test_agreement_and_coverage_are_different_questions():
    """The script answered two questions with one exit code.

    Agreement failures are defects: an invented term, a variant that never
    occurs, a trigger naming wording nobody writes. Coverage is a backlog,
    deliberately at 68%, and gating on it means the check fails on every
    build forever. A check that always fails is a check people ignore, so it
    could never be added to CI, which is how a content fix removed the
    corpus's last "attacked" while the lexicon still declared it.
    """
    assert cl.exit_code(problems=[], missing=[]) == 0
    assert cl.exit_code(problems=["asleep: appears nowhere"], missing=[]) == 1
    assert cl.exit_code(problems=[], missing=[(9, "shuffle")]) == 0, \
        "a coverage backlog must not fail the build"
    assert cl.exit_code(problems=[], missing=[(9, "shuffle")],
                        require_complete=True) == 1, \
        "asking for completeness explicitly must still be possible"
