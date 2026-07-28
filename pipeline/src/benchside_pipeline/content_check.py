"""Verification of the rewrites layer against the verbatim content layer.

Rules (spec: structured-rulebase design):
  1. every entry validates against its archetype schema;
  2. every section with body text has an entry (warning normally, error in
     release); empty-bodied sections must not have entries;
  3. no orphan entries (ids missing from content);
  4. see_also targets exist (any document);
  5. declared quotes appear verbatim in the source section AND in the
     entry's own text (whitespace-normalized);
  6. no undeclared run of >= OVERLAP_TOKENS consecutive tokens shared
     between entry text and the source body (the paraphrase tripwire);
  7. release only: judge-tier entries must be reviewed;
  8. skip entries satisfy coverage but must name a real section, and nothing
     may see_also a skipped section (it does not exist in the app).
"""

from __future__ import annotations

import re
from pathlib import Path

from benchside_pipeline.model import load_document
from benchside_pipeline.rewrites import is_skip, load_rewrites, validate_entry

OVERLAP_TOKENS = 12

_SKIP_KEYS = {"archetype", "tier", "review", "see_also", "quotes"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


def _text_fields(entry: dict) -> list[str]:
    """Every free-text string in the entry (recursively), skipping metadata."""
    fields: list[str] = []

    def walk(value):
        if isinstance(value, str):
            fields.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)

    for key, value in entry.items():
        if key not in _SKIP_KEYS:
            walk(value)
    return fields


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def check_rewrites(content_dir: Path, rewrites_dir: Path, release: bool = False) -> list[str]:
    errors: list[str] = []

    sections: dict[str, dict] = {}
    for path in sorted(Path(content_dir).glob("*.json")):
        _, secs = load_document(path)
        for sec in secs:
            sections[sec.id] = {"body": sec.body, "tier_doc": sec.doc_id}
    # Coverage follows BODIES, not tree position: containers can carry real
    # prose (e.g. an overview above its child sections) and that text must
    # not ship verbatim. Empty-bodied sections need no entry.
    needs_entry = {sid for sid, s in sections.items() if _normalize(s["body"])}

    entries = load_rewrites(rewrites_dir)
    skipped = {sid for sid, e in entries.items() if is_skip(e)}

    for sid, entry in sorted(entries.items()):
        errors.extend(validate_entry(sid, entry))
        if sid not in sections:
            errors.append(f"{sid}: orphan rewrite entry (no such section in content)")
            continue
        if is_skip(entry):
            continue
        if sid not in needs_entry:
            errors.append(f"{sid}: rewrite entry on a section with no body text")
            continue

        for target in entry.get("see_also", []):
            if target not in sections:
                errors.append(f"{sid}: see_also target {target} does not exist")
            elif target in skipped:
                errors.append(f"{sid}: see_also target {target} is skipped (absent from the app)")

        source_norm = _normalize(sections[sid]["body"])
        source_tokens = _tokens(sections[sid]["body"])
        fields = _text_fields(entry)
        fields_norm = [_normalize(f) for f in fields]

        allowed: set[tuple[str, ...]] = set()
        for quote in entry.get("quotes", []):
            quote_norm = _normalize(quote)
            if quote_norm not in source_norm:
                errors.append(f'{sid}: quote "{quote}" not found in source text')
            if not any(quote_norm in f for f in fields_norm):
                errors.append(f'{sid}: quote "{quote}" unused in entry text')
            allowed |= _ngrams(_tokens(quote), OVERLAP_TOKENS)

        source_grams = _ngrams(source_tokens, OVERLAP_TOKENS)
        for field in fields:
            for gram in _ngrams(_tokens(field), OVERLAP_TOKENS):
                if gram in source_grams and gram not in allowed:
                    errors.append(
                        f"{sid}: undeclared {OVERLAP_TOKENS}-token overlap with source "
                        f'("{" ".join(gram[:6])} …") — paraphrase or declare a quote'
                    )
                    break  # one report per field is enough

        if release and entry.get("tier") == "judge" and entry.get("review", "pending") != "reviewed":
            errors.append(f"{sid}: judge-tier entry not reviewed (release gate)")

    for sid in sorted(needs_entry - set(entries)):
        message = f"{sid}: no rewrite entry (coverage gap)"
        errors.append(message if release else f"warning: {message}")

    return errors
