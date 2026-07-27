import json

import pytest

from benchside_pipeline.rewrites import (
    RewriteError,
    load_rewrites,
    validate_entry,
)


def valid(archetype):
    base = {"archetype": archetype, "tier": "standard"}
    payload = {
        "mechanic": {"summary": "A short original summary.",
                     "state": ["Cannot attack"],
                     "branch": {"when": "Between turns",
                                "options": [{"condition": "Heads", "outcome": "Condition ends"}]},
                     "ends_when": ["It evolves"],
                     "effects": {"Attack": "Blocked"}},
        "procedure": {"summary": "How setup works.",
                      "steps": [{"action": "Shuffle the deck"}]},
        "penalty": {"summary": "Marked cards.", "infraction": "Marked sleeves",
                    "base_penalty": [{"tier": "Tier 1", "penalty": "Warning"}],
                    "examples": ["Worn corner"], "upgrade_conditions": ["Pattern of wear"]},
        "definition": {"terms": [{"term": "Bench", "meaning": "Where reserve cards sit."}]},
        "note": {"summary": "Why penalties exist.", "paragraphs": ["Education over punishment."]},
    }[archetype]
    return {**base, **payload}


@pytest.mark.parametrize("archetype", ["mechanic", "procedure", "penalty", "definition", "note"])
def test_valid_entries_validate_clean(archetype):
    assert validate_entry("fix-1", valid(archetype)) == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda e: e.update(archetype="saga"), "archetype"),
    (lambda e: e.pop("summary"), "summary"),
    (lambda e: e.update(tier="casual"), "tier"),
    (lambda e: e.update(review="maybe"), "review"),
    (lambda e: e.update(extra_field=1), "extra_field"),
])
def test_mechanic_rule_violations(mutate, needle):
    entry = valid("mechanic")
    mutate(entry)
    errors = validate_entry("fix-1", entry)
    assert errors and any(needle in err for err in errors)


@pytest.mark.parametrize("archetype,mutate,needle", [
    ("procedure", lambda e: e.update(steps=[]), "steps"),
    ("procedure", lambda e: e.update(steps=[{"note": "no action"}]), "action"),
    ("definition", lambda e: e.update(terms=[]), "terms"),
    ("definition", lambda e: e.update(terms=[{"term": "X"}]), "meaning"),
    ("note", lambda e: e.update(paragraphs=[]), "paragraphs"),
    ("penalty", lambda e: e.update(base_penalty=[]), "base_penalty"),
    ("penalty", lambda e: e.update(base_penalty=[{"tier": "T1"}]), "penalty"),
    ("mechanic", lambda e: e.update(branch={"when": "x", "options": []}), "options"),
    ("mechanic", lambda e: e.update(branch={"when": "x", "options": [{"condition": "c"}]}), "outcome"),
    ("mechanic", lambda e: e.update(effects={}), "effects"),
])
def test_archetype_specific_violations(archetype, mutate, needle):
    entry = valid(archetype)
    mutate(entry)
    errors = validate_entry("fix-1", entry)
    assert errors and any(needle in err for err in errors)


def test_load_rewrites_round_trip(tmp_path):
    (tmp_path / "doc-a.json").write_text(json.dumps({"a-1": valid("note")}))
    (tmp_path / "doc-b.json").write_text(json.dumps({"b-1": valid("mechanic")}))
    loaded = load_rewrites(tmp_path)
    assert set(loaded) == {"a-1", "b-1"}
    assert loaded["a-1"]["archetype"] == "note"


def test_load_rewrites_duplicate_ids_raise(tmp_path):
    (tmp_path / "doc-a.json").write_text(json.dumps({"a-1": valid("note")}))
    (tmp_path / "doc-b.json").write_text(json.dumps({"a-1": valid("note")}))
    with pytest.raises(RewriteError, match="a-1"):
        load_rewrites(tmp_path)


def test_load_rewrites_malformed_json_raises(tmp_path):
    (tmp_path / "doc-a.json").write_text("{not json")
    with pytest.raises(RewriteError, match="doc-a"):
        load_rewrites(tmp_path)


def test_penalty_row_unknown_key_rejected():
    entry = valid("penalty")
    entry["base_penalty"] = [{"tier": "T", "penalty": "P", "bogus": 1}]
    assert any("unknown keys" in e for e in validate_entry("fix-1", entry))


def test_penalty_handling_optional():
    entry = valid("penalty")
    entry["handling"] = ["Assess the pattern"]
    assert validate_entry("fix-1", entry) == []
