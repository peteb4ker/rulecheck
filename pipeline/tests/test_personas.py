import re
import sqlite3
from pathlib import Path

import pytest

DB = Path(__file__).resolve().parents[2] / "build" / "rulecheck.db"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="real DB not built")


def fts_match(raw: str) -> str:
    """Port of the app's QuerySanitizer.ftsMatch.

    The app never sends raw text to FTS5: it lowercases, splits on
    non-alphanumerics, and emits each token as a quoted prefix match. These
    DB-level persona gates must use the same expression as the Swift ones, or
    the two can disagree about ranking and neither notices (#21).
    """
    tokens = [t for t in re.split(r"[^a-z0-9]+", raw.lower()) if t]
    return " ".join(f'"{t}"*' for t in tokens)


def top_hits(query: str, docs: tuple[str, ...] | None = None) -> list[tuple[str, ...]]:
    con = sqlite3.connect(DB)
    doc_filter = ""
    params: list = [fts_match(query)]
    if docs:
        doc_filter = f"AND s.doc_id IN ({','.join('?' * len(docs))}) "
        params.extend(docs)
    rows = con.execute(
        "SELECT s.id, s.doc_id, s.number, s.title, s.body FROM sections_fts f "
        "JOIN sections s ON s.rowid = f.rowid "
        "WHERE sections_fts MATCH ? "
        + doc_filter
        + "ORDER BY bm25(sections_fts, 10.0, 1.0) LIMIT 5",
        params,
    ).fetchall()
    con.close()
    assert rows, f"no hits for {query!r}"
    return rows


def test_fts_match_mirrors_the_app_sanitizer():
    assert fts_match("deck check") == '"deck"* "check"*'
    assert fts_match("Asleep") == '"asleep"*'
    assert fts_match("hyphen-word, punctuation!") == '"hyphen"* "word"* "punctuation"*'


def test_player_asleep():
    # Player persona: default All scope; the Asleep mechanic is the top hit.
    sec_id, doc_id, number, title, body = top_hits("asleep")[0]
    assert doc_id == "tcg-rules"
    assert "asleep" in title.lower()


def test_judge_deck_check():
    # Judge persona: queries under the app's Tournament scope (spec, personas
    # section). All-scope ranking is dominated by rulebook body-frequency
    # noise; the scope filter is the design's answer to that tension.
    #
    # Mirrors PersonaAcceptanceTests.testJudgeDeckCheckTopHit: no section in
    # the corpus is titled "Deck Check", so the gate is "a citable
    # tournament-doc section that actually concerns deck checks". Under prefix
    # semantics that is the handbook's 4.3.1 Legality Checks.
    sec_id, doc_id, number, title, body = top_hits(
        "deck check", docs=("tournament-rules", "penalty-guidelines")
    )[0]
    assert doc_id in ("tournament-rules", "penalty-guidelines")
    assert number and number[0].isdigit()  # citable by section number
    text = f"{title} {body}".lower()
    assert "deck" in text and "check" in text, f"top hit unrelated to deck checks: {sec_id}"


def test_asleep_blocks_attacking_and_retreating():
    """A content guarantee, checked where content changes actually run.

    This lived in the app's RulesRepositoryTests, which asserted the Asleep
    effects were exactly ["Abilities", "Attack", "Retreat"]. Removing the
    "Abilities" row — an invention the source never supports — broke that
    test, and CI never noticed, because the app job is skipped on
    content-only changes. The comment justifying that skip said content
    changes "can only move search ranking", which this disproved.

    Asserting it here costs nothing: the pipeline job runs on Linux and runs
    on every content change by definition.
    """
    import json
    con = sqlite3.connect(DB)
    row = con.execute(
        "select structure from sections where id = 'tcg-Asleep'").fetchone()
    effects = json.loads(row[0])["effects"]
    assert effects.get("Attack") == "Blocked"
    assert effects.get("Retreat") == "Blocked"
    assert "Abilities" not in effects, (
        "the source never says Abilities stay usable while Asleep, and the "
        "corpus glossary says most Poké-Powers switch off under a Special "
        "Condition")
