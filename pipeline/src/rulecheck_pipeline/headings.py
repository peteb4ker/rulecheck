from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Heading:
    level: int
    number: str
    title: str


def classify_line(line: str, heading_rules: list[str]) -> Heading | None:
    stripped = line.strip()
    for i, rule in enumerate(heading_rules):
        m = re.match(rule, stripped)
        if m:
            # Some headings are a number and nothing else, such as the bare
            # "Appendix A" in the penalty guidelines. Fall back to the number
            # so the section is still titled and still citable.
            title = (m.group(2) or "").strip() or m.group(1)
            return Heading(level=i + 1, number=m.group(1), title=title)
    return None
