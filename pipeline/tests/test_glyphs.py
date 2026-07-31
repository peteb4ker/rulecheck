"""Tests for glyph matching.

Every case here is a row that really appears in the game rules, or a failure
mode that has already bitten this codebase once.
"""

import pytest

from rulecheck_pipeline import glyphs

TERMS = [
    {"term": "asleep", "category": "state", "gloss": "g",
     "glyph": True, "glyph_render": {"symbol": "moon.zzz"}},
    {"term": "blocked", "category": "modifier", "gloss": "g",
     "glyph": True, "glyph_render": {"symbol": "nosign"},
     "glyph_triggers": ["no attacking", "no retreating"]},
    {"term": "bench", "category": "entity", "gloss": "g", "glyph": "undecided"},
    {"term": "damage counter", "category": "entity", "gloss": "g",
     "glyph": "undecided"},
    {"term": "evolve", "category": "action", "gloss": "g", "glyph": False,
     "glyph_note": "too common"},
    {"term": "pokémon", "category": "entity", "gloss": "g", "glyph": False,
     "glyph_note": "too common"},
    {"term": "draw", "category": "action", "gloss": "g", "glyph": "undecided"},
    {"term": "attack", "category": ["entity", "action"], "gloss": "g",
     "glyph": False, "glyph_note": "too common"},
]


@pytest.fixture
def index():
    return glyphs.build_index(TERMS)


def test_a_row_naming_one_concept_gets_its_glyph(index):
    assert glyphs.glyph_for("Turned sideways while Asleep", index) == "asleep"


def test_inflections_reach_the_same_concept(index):
    """Reuses the lexicon stemmer rather than a second one, so "evolving" and
    "evolves" cannot drift apart from the rest of the pipeline."""
    assert glyphs.glyph_for("Draws a card", index) == "draw"
    assert glyphs.glyph_for("Drawing a card", index) == "draw"


def test_accents_fold(index):
    """"Pokémon" not matching "Pokemon" has bitten this codebase three times
    in analysis. It must not bite the shipped matcher."""
    assert glyphs.glyph_for("Pokemon is Asleep", index) == "asleep"
    assert glyphs.glyph_for("Pokémon is Asleep", index) == "asleep"


def test_a_row_naming_nothing_gets_no_glyph(index):
    assert glyphs.glyph_for("The player decides the order", index) is None


def test_a_held_out_concept_gets_no_glyph(index):
    """Classified, deliberately without a glyph. It must not fall through to
    something else either."""
    assert glyphs.glyph_for("Evolving a Pokemon", index) is None


def test_a_multi_word_concept_matches(index):
    assert glyphs.glyph_for("Place two damage counters", index) == "damage counter"


def test_an_undecided_concept_still_matches(index):
    """Undecided is a decision about the picture, not about whether the
    concept renders. It renders a chip."""
    assert glyphs.glyph_for("Put it on the Bench", index) == "bench"


def test_a_trigger_phrase_matches(index):
    """The reason blocked() can be deleted from the app. "No attacking" names
    no glyph-bearing term and still means blocked."""
    assert glyphs.glyph_for("No attacking", index) == "blocked"
    assert glyphs.glyph_for("No retreating", index) == "blocked"


def test_priority_prefers_the_state_over_the_object(index):
    """A row is about the state it describes; any object it mentions along
    the way is incidental."""
    assert glyphs.glyph_for("Asleep on the Bench", index) == "asleep"


def test_priority_prefers_the_modifier_over_the_object(index):
    assert glyphs.glyph_for("No attacking from the Bench", index) == "blocked"


def test_a_tie_inside_one_category_breaks_toward_the_rarer_concept():
    """A rarer term carries more information, so it wins."""
    terms = [
        {"term": "deck", "category": "entity", "gloss": "g", "glyph": "undecided"},
        {"term": "stadium", "category": "entity", "gloss": "g", "glyph": "undecided"},
    ]
    index = glyphs.build_index(terms, counts={"deck": 107, "stadium": 9})
    assert glyphs.glyph_for("Search your deck, then play a Stadium", index) == "stadium"


def test_a_term_with_two_categories_takes_the_higher_priority():
    terms = [
        {"term": "poisoned", "category": ["state", "entity"], "gloss": "g",
         "glyph": "undecided"},
        {"term": "bench", "category": "entity", "gloss": "g", "glyph": "undecided"},
    ]
    index = glyphs.build_index(terms)
    assert glyphs.glyph_for("Poisoned on the Bench", index) == "poisoned"


def test_matching_is_deterministic(index):
    row = "Asleep on the Bench with damage counters"
    assert len({glyphs.glyph_for(row, index) for _ in range(20)}) == 1


def test_an_empty_row_gets_no_glyph(index):
    assert glyphs.glyph_for("", index) is None
    assert glyphs.glyph_for("   ", index) is None


# --- annotating a whole entry ---

ENTRY = {
    "archetype": "mechanic", "tier": "standard",
    "summary": "Asleep stops a Pokemon acting.",
    "state": ["No attacking", "No retreating", "Turned sideways"],
    "effects": {"Attack": "Blocked", "Retreat": "Blocked"},
    "branch": {"when": "Pokemon Checkup",
               "options": [{"condition": "Heads", "outcome": "Wakes up"},
                           {"condition": "Tails", "outcome": "Still Asleep"}]},
}


def test_annotation_arrays_align_with_their_field(index):
    out = glyphs.annotate(ENTRY, index)
    assert len(out["state_glyphs"]) == len(ENTRY["state"])
    assert len(out["branch_glyphs"]) == len(ENTRY["branch"]["options"])


def test_a_row_with_no_glyph_gets_null_not_a_gap(index):
    """A gap would slide every later glyph onto the wrong row."""
    out = glyphs.annotate(ENTRY, index)
    assert out["state_glyphs"] == ["blocked", "blocked", None]


def test_free_prose_is_never_annotated(index):
    """Glyphs earn attention by being rare. A glyph beside every mention of a
    common word in a summary would make the page harder to read."""
    out = glyphs.annotate(ENTRY, index)
    assert "summary_glyphs" not in out


def test_an_entry_with_no_structured_fields_gets_no_arrays(index):
    out = glyphs.annotate({"archetype": "note", "tier": "standard",
                           "summary": "Asleep is a Special Condition."}, index)
    assert out == {}


def test_annotate_does_not_mutate_the_entry(index):
    """rewrites/ is hand-authored. Annotation happens on the way into the
    database and must never write back."""
    import copy
    before = copy.deepcopy(ENTRY)
    glyphs.annotate(ENTRY, index)
    assert ENTRY == before


def test_annotation_is_idempotent(index):
    assert glyphs.annotate(ENTRY, index) == glyphs.annotate(ENTRY, index)
