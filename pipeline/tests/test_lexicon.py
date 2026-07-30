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
    assert any("category must be one of" in e for e in errors)


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
