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

from rulecheck_pipeline import shingles
from rulecheck_pipeline.model import load_document
from rulecheck_pipeline.rewrites import is_skip, load_rewrites, validate_entry

# Defined in shingles, because the fingerprints must be built from n-grams of
# exactly this size. Two constants drifted apart silently before this.
OVERLAP_TOKENS = shingles.SHINGLE_TOKENS

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


def check_rewrites(content_dir: Path, rewrites_dir: Path, release: bool = False,
                   full_content_dir: Path | None = None) -> list[str]:
    """Validate the rewrite layer.

    Runs in two modes. With the full parse artifact present (local work, and
    any release) every check runs against real source text. With only the
    committed index (CI, and any clone without the PDFs) the source text does
    not exist, so the overlap tripwire runs against one-way fingerprints
    instead — same question, no prose in the repository.
    """
    errors: list[str] = []

    sections: dict[str, dict] = {}
    for path in sorted(Path(content_dir).glob("*.json")):
        _, secs = load_document(path)
        for sec in secs:
            sections[sec.id] = {"body": sec.body, "chars": sec.body_chars,
                                "tier_doc": sec.doc_id}
    if full_content_dir and Path(full_content_dir).is_dir():
        for path in sorted(Path(full_content_dir).glob("*.json")):
            for sec in load_document(path)[1]:
                if sec.id in sections and sec.body:
                    sections[sec.id]["body"] = sec.body

    prints: dict[str, set[str]] = {}
    fingerprint_dir = Path(content_dir) / "fingerprints"
    if fingerprint_dir.is_dir():
        for path in sorted(fingerprint_dir.glob("*.json")):
            prints.update(shingles.load(path))

    have_text = any(s["body"] for s in sections.values())
    if release and not have_text:
        errors.append(
            "release verification needs the full parse artifact (verbatim source "
            "text) to check declared quotes exactly — run `just parse` first"
        )

    # Coverage follows BODIES, not tree position: containers can carry real
    # prose (e.g. an overview above its child sections) and that text must
    # not ship verbatim. Empty-bodied sections need no entry. The index keeps
    # the length so this still works without the text itself.
    needs_entry = {sid for sid, s in sections.items() if s["chars"]}

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

        body = sections[sid]["body"]
        source_norm = _normalize(body)
        fields = _text_fields(entry)
        fields_norm = [_normalize(f) for f in fields]

        # With text: exact n-grams. Without: the committed fingerprints of the
        # same n-grams. Identical question, one of them just cannot be read.
        source_marks = (_ngrams(_tokens(body), OVERLAP_TOKENS) if body
                        else prints.get(sid, set()))

        def marks(text: str) -> set:
            return (_ngrams(_tokens(text), OVERLAP_TOKENS) if body
                    else shingles.fingerprints(text))

        allowed = set()
        for quote in entry.get("quotes", []):
            if body:
                if _normalize(quote) not in source_norm:
                    errors.append(f'{sid}: quote "{quote}" not found in source text')
            elif len(_tokens(quote)) >= OVERLAP_TOKENS and not (
                    marks(quote) and marks(quote) <= source_marks):
                errors.append(
                    f'{sid}: quote "{quote}" does not match the source fingerprints '
                    f"(run `just parse` to verify quotes against real text)"
                )
            if not any(_normalize(quote) in f for f in fields_norm):
                errors.append(f'{sid}: quote "{quote}" unused in entry text')
            allowed |= marks(quote)

        for field in fields:
            for gram in marks(field):
                if gram in source_marks and gram not in allowed:
                    detail = (f'("{" ".join(gram[:6])} …") ' if body else "")
                    errors.append(
                        f"{sid}: undeclared {OVERLAP_TOKENS}-token overlap with source "
                        f"{detail}— paraphrase or declare a quote"
                    )
                    break  # one report per field is enough

        if release and entry.get("tier") == "judge" and entry.get("review", "pending") != "reviewed":
            errors.append(f"{sid}: judge-tier entry not reviewed (release gate)")

    for sid in sorted(needs_entry - set(entries)):
        message = f"{sid}: no rewrite entry (coverage gap)"
        errors.append(message if release else f"warning: {message}")

    return errors
