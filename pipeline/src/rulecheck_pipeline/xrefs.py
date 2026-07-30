from __future__ import annotations

import re

from rulecheck_pipeline.model import Section

# A reference qualified by "of appendix ..." belongs to a different document
# (the penalty guidelines point at the VG Rules and Formats handbook this way).
# Matching the bare "section 1" sent readers to this document's section 1
# instead, which is a wrong pointer rather than a missing one.
XREF_RE = re.compile(
    r"\b[Ss]ection\s+(\d+(?:\.\d+)*)(?!\s+of\s+[Aa]ppendix)"
)


def _is_heading_line(body: str, match: re.Match) -> bool:
    """True when the match is the whole line, which makes it a heading.

    The penalty guidelines appendix divides itself with lines reading exactly
    "Section 1" and "Section 2". Those name parts of the appendix rather than
    pointing at the document's sections 1 and 2. Comparing against the whole
    line rather than testing for the start of one keeps a genuine reference
    that happens to be wrapped onto a new line.
    """
    start = body.rfind("\n", 0, match.start()) + 1
    end = body.find("\n", match.end())
    line = body[start:end if end != -1 else len(body)]
    return line.strip() == match.group(0).strip()


def detect_xrefs(sections: list[Section]) -> list[tuple[str, str]]:
    by_number = {(s.doc_id, s.number): s.id for s in sections}
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for s in sections:
        for m in XREF_RE.finditer(s.body):
            if _is_heading_line(s.body, m):
                continue
            target = by_number.get((s.doc_id, m.group(1)))
            if target is None or target == s.id:
                continue
            pair = (s.id, target)
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs
