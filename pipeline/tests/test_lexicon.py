"""Every family here is taken from the real corpus, with its real counts, so
these tests fail if the stemmer stops matching the text we actually ship."""

import pytest

from rulecheck_pipeline.lexicon import same_term, stem, validate


@pytest.mark.parametrize("family", [
    ["evolve", "evolves", "evolved", "evolving"],
    ["flip", "flips", "flipped", "flipping"],
    ["attack", "attacks", "attacked", "attacking"],
    ["attach", "attaches", "attached", "attaching"],
    ["damage", "damages", "damaged"],
    ["shuffle", "shuffles", "shuffled", "shuffling"],
    ["knock", "knocks", "knocked", "knocking"],
    ["discard", "discards", "discarded", "discarding"],
    ["play", "plays", "played", "playing"],
    ["draw", "draws", "drawing"],
    ["card", "cards"],
    ["counter", "counters"],
])
def test_inflections_of_one_word_share_a_stem(family):
    stems = {stem(w) for w in family}
    assert len(stems) == 1, f"{family} split across stems {stems}"


@pytest.mark.parametrize("action,derived", [
    ("attack", "attacker"),    # an action and the one performing it
    ("attach", "attachment"),  # an action and the thing attached
    ("play", "player"),        # an action and the person
    ("rotate", "rotation"),    # an action and the noun for it
    ("evolve", "evolution"),   # the action and the card type
])
def test_derived_words_are_kept_separate(action, derived):
    """These look related and are genuinely different words. Merging them
    would fold an entity into an action and lose an icon."""
    assert not same_term(action, derived), f"{derived} must not collapse into {action}"


def test_words_that_merely_look_alike_stay_apart():
    """attack and attach share four leading characters. A prefix-based
    grouping merges them, which is why this uses suffix stripping."""
    assert not same_term("attack", "attach")
    assert not same_term("deal", "deck")


def test_short_words_are_not_stemmed_into_nothing():
    for w in ("is", "as", "its", "has"):
        assert len(stem(w)) >= 2, f"{w} was stemmed away"


def test_double_consonants_are_reduced_only_when_inflected():
    assert stem("flipped") == stem("flip")
    assert stem("class") == "class", "ss is not a plural"


def test_validate_rejects_a_variant_that_is_a_different_word():
    errors = validate([{"term": "attack", "category": "action", "gloss": "g",
                        "variants": ["attacker"]}])
    assert any("different word" in e for e in errors)


def test_validate_rejects_an_unknown_category():
    errors = validate([{"term": "bench", "category": "place", "gloss": "g"}])
    assert any("must be one of" in e for e in errors)


def test_a_term_may_hold_more_than_one_sense():
    """"attack" is a thing printed on a card about 25 times in the game rules
    and something a player does about 8 times. Forcing one category makes a
    parallel classifier pick arbitrarily and two batches disagree."""
    assert validate([{
        "term": "attack", "category": ["entity", "action"],
        "gloss": "A printed attack, and the act of using one.",
        "variants": ["attacks", "attacked", "attacking"],
    }]) == []


def test_validate_rejects_a_bad_category_inside_a_list():
    errors = validate([{"term": "attack", "category": ["action", "place"],
                        "gloss": "g"}])
    assert any("must be one of" in e for e in errors)


def test_validate_rejects_a_repeated_category():
    errors = validate([{"term": "attack", "category": ["action", "action"],
                        "gloss": "g"}])
    assert any("repeats a category" in e for e in errors)


def test_validate_requires_at_least_one_category():
    errors = validate([{"term": "attack", "gloss": "g"}])
    assert any("needs a category" in e for e in errors)


def test_validate_requires_a_gloss():
    errors = validate([{"term": "bench", "category": "entity", "gloss": "  "}])
    assert any("needs a gloss" in e for e in errors)


def test_validate_flags_two_entries_that_share_a_stem():
    errors = validate([
        {"term": "evolve", "category": "action", "gloss": "g"},
        {"term": "evolves", "category": "action", "gloss": "g"},
    ])
    assert any("shares a stem" in e for e in errors)


def test_validate_accepts_a_well_formed_entry():
    assert validate([{
        "term": "evolve", "category": "action",
        "gloss": "Place an Evolution card onto the Pokemon it evolves from.",
        "variants": ["evolves", "evolved", "evolving"],
    }]) == []


def test_extract_groups_inflections_under_one_candidate():
    from rulecheck_pipeline.lexicon import extract
    got = extract(["Evolving a Pokemon evolves it. It evolved once, and evolves again."])
    evolve = next(c for c in got if c["stem"] == "evolv")
    assert evolve["count"] == 4
    assert set(evolve["forms"]) == {"evolving", "evolves", "evolved"}
    assert evolve["lemma"] == "evolves", "the most frequent spelling represents the group"


def test_extract_keeps_derived_words_as_their_own_candidates():
    from rulecheck_pipeline.lexicon import extract
    got = {c["stem"]: c for c in extract(["The attacker attacks. Attacking attacks again."])}
    assert "attack" in got and "attacker" in got
    assert got["attack"]["count"] == 3
    assert got["attacker"]["count"] == 1


def test_extract_is_deterministic_for_the_same_input():
    from rulecheck_pipeline.lexicon import extract
    texts = ["Shuffle your deck and draw a card.", "Draw two cards, then shuffle."]
    assert extract(texts) == extract(texts)


def test_extract_respects_a_minimum_count():
    from rulecheck_pipeline.lexicon import extract
    texts = ["retreat retreat retreat", "mulligan"]
    stems = {c["stem"] for c in extract(texts, min_count=2)}
    assert "retreat" in stems and "mulligan" not in stems


def test_tokenize_does_not_manufacture_a_stray_s():
    """A possessive and a "(s)" plural each left a bare "s" behind, which
    became the third most frequent candidate in the real corpus."""
    from rulecheck_pipeline.lexicon import tokenize
    assert "s" not in tokenize("the card's name")
    assert "s" not in tokenize("draw two card(s)")
    assert tokenize("draw two card(s)") == ["draw", "two", "cards"]
    # Single letters are dropped too. No domain term is one character, and
    # "a" and "I" would otherwise top the frequency list.
    assert tokenize("a card's name") == ["card", "name"]


def test_extract_finds_multi_word_terms():
    """damage counter, Special Condition and Pokemon Checkup are entities the
    single-token extractor could never propose, so an agent following the
    skill would classify "damage" and "counter" and never create the term."""
    from rulecheck_pipeline.lexicon import extract
    texts = ["Add a damage counter.", "Remove two damage counters.",
             "Place damage counters on it."]
    got = {c["stem"]: c for c in extract(texts, min_count=2, max_words=2)}
    assert "damag counter" in got, "multi-word term not proposed"
    assert got["damag counter"]["count"] == 3
    assert got["damag counter"]["words"] == 2


def test_multi_word_extraction_ignores_grams_cut_mid_sentence():
    from rulecheck_pipeline.lexicon import extract
    texts = ["Add a damage counter to it.", "Add a damage counter to it."]
    stems = {c["stem"] for c in extract(texts, min_count=2, max_words=2)}
    assert "damag counter" in stems
    assert not any(g.startswith("to ") or g.endswith(" to") for g in stems), \
        "a phrase must not begin or end on a function word"


def test_stem_phrase_agrees_across_inflections():
    from rulecheck_pipeline.lexicon import stem_phrase
    assert stem_phrase("damage counter") == stem_phrase("damage counters")
    assert stem_phrase("Special Condition") == stem_phrase("special conditions")


def test_a_phrase_does_not_span_punctuation():
    """"round(s), single elimination" merged into "rounds single", which is
    not a term and which dominated the first multi-word run."""
    from rulecheck_pipeline.lexicon import extract
    texts = ["three rounds, single elimination follows"] * 3
    stems = {c["stem"] for c in extract(texts, min_count=2, max_words=2)}
    assert "singl elimination" in stems
    assert "round singl" not in stems, "a phrase crossed a comma"


def test_phrase_stem_is_stable_for_a_multi_word_variant():
    """A multi-word variant is a phrase, not a token, so checking it against
    single-word counts always reported it as never occurring."""
    from rulecheck_pipeline.lexicon import stem_phrase
    assert stem_phrase("damage counters") == stem_phrase("damage counter")
    assert stem_phrase("Prize cards") == stem_phrase("prize card")


@pytest.mark.parametrize("singular,plural", [
    ("penalty", "penalties"),
    ("ability", "abilities"),
    ("apply", "applies"),
    ("deny", "denies"),
])
def test_y_pluralises_as_ies_and_still_groups(singular, plural):
    """English turns a final "y" into "ies". Stripping the plural left an "i"
    that never matched the singular, so one concept became two terms in two
    different frequency bands. Both classifiers hit this independently."""
    assert same_term(singular, plural), f"{singular}/{plural} split"


def test_structural_signal_finds_what_frequency_misses():
    """Frequency ranks "Knock Out" at 2544, below the floor, because the words
    are rarely written. It is the single most load-bearing term in the effects
    tables. Structure sees that; prose counting cannot."""
    from rulecheck_pipeline.lexicon import structural_candidates
    sections = [{"id": "tcg-Asleep", "title": "Asleep"}]
    entries = {"tcg-Asleep": {"archetype": "mechanic", "tier": "standard",
                              "summary": "s",
                              "state": ["No attacking"],
                              "effects": {"Attack": "Blocked"},
                              "branch": {"when": "Pokemon Checkup",
                                         "options": [{"condition": "Heads",
                                                      "outcome": "Wakes up"}]}}}
    got = {c["term"]: c for c in structural_candidates(sections, entries)}
    assert "Asleep" in got and "Blocked" in got and "Heads" in got
    assert "Pokemon Checkup" in got
    assert got["Asleep"]["sources"] == ["section title"]


def test_a_section_title_outweighs_a_passing_mention():
    from rulecheck_pipeline.lexicon import structural_candidates
    sections = [{"id": "x", "title": "Asleep"}]
    entries = {"x": {"archetype": "mechanic", "tier": "standard", "summary": "s",
                     "steps": [{"actor": "Referee", "action": "a"}]}}
    got = {c["term"]: c["weight"] for c in structural_candidates(sections, entries)}
    assert got["Asleep"] > got["Referee"]


def test_long_section_titles_still_surface_their_concept():
    """The rulebook heads the mulligan rule "Full details of taking a
    mulligan". A four-word cap dropped it, losing a rule of the game."""
    from rulecheck_pipeline.lexicon import structural_candidates
    sections = [{"id": "m", "title": "Full details of taking a mulligan"}]
    got = [c["term"] for c in structural_candidates(sections, {})]
    assert "Full details of taking a mulligan" in got


def test_prose_sentences_in_structured_fields_are_not_concepts():
    from rulecheck_pipeline.lexicon import structural_candidates
    entries = {"x": {"archetype": "mechanic", "tier": "standard", "summary": "s",
                     "state": ["This is a long sentence describing behaviour at length"]}}
    assert structural_candidates([], entries) == []


# --- glyph decisions (spec: 2026-07-31-glyph-rendering-design.md) ---

def term(**kw):
    base = {"term": "Asleep", "category": "state", "gloss": "A Special Condition."}
    base.update(kw)
    return base


def test_a_term_with_no_glyph_key_is_valid():
    """Absent means no glyph. Classifying a term must never silently create
    an obligation to source an icon for it."""
    assert validate([term()]) == []


def test_glyph_must_be_a_boolean():
    errors = validate([term(glyph="yes", glyph_render={"symbol": "moon.zzz"})])
    assert any("must be true or false" in e for e in errors)


def test_a_glyph_bearing_term_needs_a_rendering():
    errors = validate([term(glyph=True)])
    assert any("needs a glyph_render" in e for e in errors)


def test_a_held_out_term_must_say_why():
    """A false without a reason is indistinguishable from never having
    considered the concept at all."""
    errors = validate([term(term="attack", category="action", glyph=False)])
    assert any("needs a glyph_note" in e for e in errors)


def test_a_held_out_term_with_a_reason_is_valid():
    assert validate([term(term="attack", category="action", glyph=False,
                          glyph_note="Renders 49 times; too common to carry meaning.")]) == []


def test_a_glyph_render_must_be_a_symbol_or_a_chip():
    errors = validate([term(glyph=True, glyph_render={})])
    assert any("either a symbol or a chip" in e for e in errors)


def test_a_glyph_render_cannot_be_both():
    errors = validate([term(glyph=True,
                            glyph_render={"symbol": "moon.zzz", "chip": "ASLEEP"})])
    assert any("either a symbol or a chip" in e for e in errors)


def test_a_symbol_render_is_valid():
    assert validate([term(glyph=True, glyph_render={"symbol": "moon.zzz"})]) == []


def test_a_chip_render_is_valid():
    """The chip is the backstop for any concept no picture states clearly."""
    assert validate([term(term="Ability", category="entity", glyph=True,
                          glyph_render={"chip": "ABILITY", "tint": "negative"})]) == []


def test_a_chip_needs_text():
    errors = validate([term(glyph=True, glyph_render={"chip": "  ", "tint": "accent"})])
    assert any("chip needs text" in e for e in errors)


def test_a_chip_needs_a_tint():
    errors = validate([term(glyph=True, glyph_render={"chip": "ABILITY"})])
    assert any("chip needs a tint" in e for e in errors)


def test_glyph_triggers_must_be_non_empty_strings():
    errors = validate([term(glyph=True, glyph_render={"symbol": "nosign"},
                            glyph_triggers=["no attacking", "  "])])
    assert any("glyph_triggers" in e for e in errors)


def test_glyph_triggers_are_valid_on_a_glyph_bearing_term():
    assert validate([term(term="blocked", category="modifier", gloss="g", glyph=True,
                          glyph_render={"symbol": "nosign"},
                          glyph_triggers=["no attacking", "cannot retreat"])]) == []


def test_a_held_out_term_cannot_carry_triggers():
    """A concept with no glyph has nothing for a trigger to render."""
    errors = validate([term(term="attack", category="action", glyph=False,
                            glyph_note="too common",
                            glyph_triggers=["declares an attack"])])
    assert any("cannot carry glyph_triggers" in e for e in errors)


def test_a_glyph_render_without_the_boolean_is_an_error():
    """The boolean is the decision; the render is how it looks. A render with
    no decision behind it would never be picked up by the matcher."""
    errors = validate([term(glyph_render={"symbol": "moon.zzz"})])
    assert any("glyph_render but no glyph" in e for e in errors)
