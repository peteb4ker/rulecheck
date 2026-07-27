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
            return Heading(level=i + 1, number=m.group(1), title=m.group(2).strip())
    return None
