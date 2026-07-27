"""Rewrite-layer entries: authored structured content, one entry per leaf
section, validated against a small archetype schema family.

The structure IS the shipped paraphrase (see the structured-rulebase spec);
`content/` remains the machine-extracted verbatim reference.
"""

from __future__ import annotations

import json
from pathlib import Path

COMMON_REQUIRED = ("archetype", "tier")
COMMON_OPTIONAL = ("review", "quotes", "see_also")

ARCHETYPES: dict[str, dict[str, tuple[str, ...]]] = {
    "mechanic": {"required": ("summary",),
                 "optional": ("state", "branch", "ends_when", "effects")},
    "procedure": {"required": ("summary", "steps"), "optional": ()},
    "penalty": {"required": ("summary", "infraction", "base_penalty"),
                "optional": ("examples", "upgrade_conditions", "handling")},
    "definition": {"required": ("terms",), "optional": ()},
    "note": {"required": ("summary", "paragraphs"), "optional": ()},
}

TIERS = {"judge", "standard"}
REVIEWS = {"pending", "reviewed"}


class RewriteError(Exception):
    pass


def _non_empty_list(errors: list[str], sid: str, entry: dict, field: str) -> list:
    value = entry.get(field)
    if field in entry and (not isinstance(value, list) or not value):
        errors.append(f"{sid}: {field} must be a non-empty list")
        return []
    return value or []


def validate_entry(section_id: str, entry: dict) -> list[str]:
    errors: list[str] = []
    sid = section_id

    archetype = entry.get("archetype")
    if archetype not in ARCHETYPES:
        return [f"{sid}: unknown archetype {archetype!r}"]
    spec = ARCHETYPES[archetype]

    for field in COMMON_REQUIRED + spec["required"]:
        if field not in entry:
            errors.append(f"{sid}: missing required field {field}")
    known = set(COMMON_REQUIRED) | set(COMMON_OPTIONAL) | set(spec["required"]) | set(spec["optional"])
    for field in sorted(set(entry) - known):
        errors.append(f"{sid}: unknown field {field} for archetype {archetype}")

    if entry.get("tier") not in TIERS:
        errors.append(f"{sid}: tier must be one of {sorted(TIERS)}")
    if entry.get("review", "pending") not in REVIEWS:
        errors.append(f"{sid}: review must be one of {sorted(REVIEWS)}")

    for field in ("quotes", "see_also"):
        _non_empty_list(errors, sid, entry, field)

    if archetype == "procedure" or "steps" in entry:
        for i, step in enumerate(_non_empty_list(errors, sid, entry, "steps")):
            if not isinstance(step, dict) or "action" not in step:
                errors.append(f"{sid}: steps[{i}] missing action")
    if archetype == "definition" or "terms" in entry:
        for i, term in enumerate(_non_empty_list(errors, sid, entry, "terms")):
            if not isinstance(term, dict) or "term" not in term or "meaning" not in term:
                errors.append(f"{sid}: terms[{i}] needs term and meaning")
    if archetype == "note" or "paragraphs" in entry:
        _non_empty_list(errors, sid, entry, "paragraphs")
    if archetype == "penalty" or "base_penalty" in entry:
        for i, row in enumerate(_non_empty_list(errors, sid, entry, "base_penalty")):
            if not isinstance(row, dict) or "tier" not in row or "penalty" not in row:
                errors.append(f"{sid}: base_penalty[{i}] needs tier and penalty")
            elif set(row) - {"tier", "penalty", "examples", "note"}:
                errors.append(f"{sid}: base_penalty[{i}] has unknown keys")
        _non_empty_list(errors, sid, entry, "examples")
        _non_empty_list(errors, sid, entry, "upgrade_conditions")
        _non_empty_list(errors, sid, entry, "handling")
    if archetype == "mechanic":
        branch = entry.get("branch")
        if branch is not None:
            if not isinstance(branch, dict) or "when" not in branch:
                errors.append(f"{sid}: branch needs when")
            options = branch.get("options") if isinstance(branch, dict) else None
            if not options:
                errors.append(f"{sid}: branch needs non-empty options")
            else:
                for i, opt in enumerate(options):
                    if not isinstance(opt, dict) or "condition" not in opt or "outcome" not in opt:
                        errors.append(f"{sid}: branch options[{i}] needs condition and outcome")
        if "effects" in entry:
            effects = entry["effects"]
            if not isinstance(effects, dict) or not effects:
                errors.append(f"{sid}: effects must be a non-empty mapping")
        for field in ("state", "ends_when"):
            _non_empty_list(errors, sid, entry, field)

    return errors


def load_rewrites(rewrites_dir: Path) -> dict[str, dict]:
    """Union of {section_id: entry} across every rewrites/*.json."""
    merged: dict[str, dict] = {}
    for path in sorted(Path(rewrites_dir).glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise RewriteError(f"{path.stem}: malformed JSON ({exc})") from exc
        for section_id, entry in data.items():
            if section_id in merged:
                raise RewriteError(f"duplicate rewrite entry for {section_id}")
            merged[section_id] = entry
    return merged
