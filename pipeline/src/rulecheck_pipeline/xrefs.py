from __future__ import annotations

import re

from rulecheck_pipeline.model import Section

XREF_RE = re.compile(r"\b[Ss]ection\s+(\d+(?:\.\d+)*)")


def detect_xrefs(sections: list[Section]) -> list[tuple[str, str]]:
    by_number = {(s.doc_id, s.number): s.id for s in sections}
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for s in sections:
        for m in XREF_RE.finditer(s.body):
            target = by_number.get((s.doc_id, m.group(1)))
            if target is None or target == s.id:
                continue
            pair = (s.id, target)
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs
