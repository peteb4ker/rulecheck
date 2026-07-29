from __future__ import annotations

import sqlite3
from pathlib import Path


def verify_db(db_path: Path) -> list[str]:
    errors: list[str] = []
    con = sqlite3.connect(db_path)
    try:
        for (doc_id,) in con.execute(
            "SELECT d.id FROM documents d "
            "LEFT JOIN sections s ON s.doc_id = d.id "
            "GROUP BY d.id HAVING COUNT(s.id) = 0"
        ):
            errors.append(f"document {doc_id}: no sections")
        for (sec_id,) in con.execute(
            "SELECT s.id FROM sections s "
            "WHERE TRIM(s.body) = '' AND NOT EXISTS "
            "(SELECT 1 FROM sections c WHERE c.parent_id = s.id)"
        ):
            errors.append(f"section {sec_id}: leaf with empty body")
        for from_id, to_id in con.execute(
            "SELECT x.from_id, x.to_id FROM xrefs x "
            "LEFT JOIN sections s ON s.id = x.to_id WHERE s.id IS NULL"
        ):
            errors.append(f"xref {from_id} -> {to_id}: target missing")
        for (parent_id,) in con.execute(
            "SELECT DISTINCT s.parent_id FROM sections s "
            "LEFT JOIN sections p ON p.id = s.parent_id "
            "WHERE s.parent_id IS NOT NULL AND p.id IS NULL"
        ):
            errors.append(f"parent {parent_id}: missing")
        try:
            con.execute(
                "INSERT INTO sections_fts(sections_fts, rank) VALUES('integrity-check', 1)"
            )
        except sqlite3.DatabaseError as exc:
            # An external-content FTS index that has drifted from its content
            # table reports itself as corruption (SQLITE_CORRUPT_VTAB). Any
            # other DatabaseError — a missing table, a file that is not our
            # build artifact — is a different fault, and calling it an FTS
            # desync would send the reader after the wrong bug. `getattr`
            # because errors raised by the sqlite3 module itself rather than
            # by SQLite (ProgrammingError, say) carry no error name at all —
            # those are not desyncs either, so they re-raise.
            if not getattr(exc, "sqlite_errorname", "").startswith("SQLITE_CORRUPT"):
                raise
            errors.append("fts index out of sync with sections")
    finally:
        con.close()
    return errors
