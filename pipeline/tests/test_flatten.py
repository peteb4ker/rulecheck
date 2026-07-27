from benchside_pipeline.flatten import flatten_entry


def test_mechanic_golden():
    entry = {
        "archetype": "mechanic", "tier": "standard",
        "summary": "An Asleep card is turned sideways and cannot act.",
        "state": ["Cannot attack", "Cannot retreat"],
        "branch": {"when": "Between turns",
                   "options": [
                       {"condition": "Heads", "outcome": "No longer Asleep",
                        "detail": "Turn the card upright."},
                       {"condition": "Tails", "outcome": "Stays Asleep"},
                   ]},
        "effects": {"Attack": "Blocked", "Abilities": "Still work"},
        "ends_when": ["It evolves", "It leaves the Active spot"],
    }
    assert flatten_entry(entry) == (
        "An Asleep card is turned sideways and cannot act.\n"
        "Cannot attack\n"
        "Cannot retreat\n"
        "When Between turns:\n"
        "- Heads: No longer Asleep — Turn the card upright.\n"
        "- Tails: Stays Asleep\n"
        "Attack: Blocked\n"
        "Abilities: Still work\n"
        "Ends when: It evolves\n"
        "Ends when: It leaves the Active spot"
    )


def test_procedure_golden():
    entry = {"archetype": "procedure", "tier": "judge",
             "summary": "Deck checks verify legality.",
             "steps": [{"actor": "Judge", "action": "Collect the deck"},
                       {"action": "Count the cards", "note": "60 exactly"}]}
    assert flatten_entry(entry) == (
        "Deck checks verify legality.\n"
        "1. Judge: Collect the deck\n"
        "2. Count the cards — 60 exactly"
    )


def test_penalty_golden():
    entry = {"archetype": "penalty", "tier": "judge",
             "summary": "Marked cards are a legality problem.",
             "infraction": "Marked cards",
             "examples": ["Worn sleeve corner"],
             "base_penalty": [{"tier": "Minor", "penalty": "Warning"}],
             "upgrade_conditions": ["Deliberate pattern"]}
    assert flatten_entry(entry) == (
        "Marked cards are a legality problem.\n"
        "Infraction: Marked cards\n"
        "Example: Worn sleeve corner\n"
        "Penalty (Minor): Warning\n"
        "Upgrades: Deliberate pattern"
    )


def test_definition_golden():
    entry = {"archetype": "definition", "tier": "standard",
             "terms": [{"term": "Bench", "meaning": "Reserve row."}]}
    assert flatten_entry(entry) == "Bench: Reserve row."


def test_note_golden():
    entry = {"archetype": "note", "tier": "standard",
             "summary": "Why penalties exist.",
             "paragraphs": ["Education over punishment.", "Consistency matters."]}
    assert flatten_entry(entry) == (
        "Why penalties exist.\n"
        "Education over punishment.\n"
        "Consistency matters."
    )


def test_minimal_mechanic_no_empty_sections():
    entry = {"archetype": "mechanic", "tier": "standard", "summary": "Just a summary."}
    assert flatten_entry(entry) == "Just a summary."


def test_deterministic():
    entry = {"archetype": "definition", "tier": "standard",
             "terms": [{"term": "A", "meaning": "B"}]}
    assert flatten_entry(entry) == flatten_entry(entry)


def test_penalty_tiered_examples_and_handling():
    entry = {"archetype": "penalty", "tier": "judge",
             "summary": "S.", "infraction": "I.",
             "handling": ["Fix the list first"],
             "base_penalty": [
                 {"tier": "Minor", "penalty": "Warning",
                  "examples": ["Worn sleeves"], "note": "no proxy needed"}]}
    assert flatten_entry(entry) == (
        "S.\nInfraction: I.\nHandling: Fix the list first\n"
        "Penalty (Minor): Warning — no proxy needed\n  e.g. Worn sleeves"
    )
