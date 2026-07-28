import sqlite3
from pathlib import Path

import pytest

DB = Path(__file__).resolve().parents[2] / "build" / "rulecheck.db"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="real DB not built")


def top_hits(query: str, docs: tuple[str, ...] | None = None) -> list[tuple[str, str, str, str]]:
    con = sqlite3.connect(DB)
    doc_filter = ""
    params: list = [query]
    if docs:
        doc_filter = f"AND s.doc_id IN ({','.join('?' * len(docs))}) "
        params.extend(docs)
    rows = con.execute(
        "SELECT s.id, s.doc_id, s.number, s.title FROM sections_fts f "
        "JOIN sections s ON s.rowid = f.rowid "
        "WHERE sections_fts MATCH ? "
        + doc_filter
        + "ORDER BY bm25(sections_fts, 10.0, 1.0) LIMIT 5",
        params,
    ).fetchall()
    con.close()
    assert rows, f"no hits for {query!r}"
    return rows


def test_player_asleep():
    # Player persona: default All scope; the Asleep mechanic is the top hit.
    sec_id, doc_id, number, title = top_hits("asleep")[0]
    assert doc_id == "tcg-rules"
    assert "asleep" in title.lower()


def test_judge_deck_check():
    # Judge persona: queries under the app's Tournament scope (spec, personas
    # section). All-scope ranking is dominated by rulebook body-frequency
    # noise; the scope filter is the design's answer to that tension.
    sec_id, doc_id, number, title = top_hits(
        "deck check", docs=("tournament-rules", "penalty-guidelines")
    )[0]
    assert doc_id in ("tournament-rules", "penalty-guidelines")
    assert number and number[0].isdigit()  # citable by section number
    assert "deck" in title.lower()
