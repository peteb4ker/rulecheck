"""Deterministic flattening of rewrite entries into searchable body text.

The flattened text is what ships in `sections.body` (phase 1): the app and
FTS index are unchanged while the shipped content becomes the authored
structure. Field order is fixed per archetype; output is newline-joined
with no trailing whitespace.
"""

from __future__ import annotations


def flatten_entry(entry: dict) -> str:
    lines: list[str] = []
    archetype = entry["archetype"]

    if summary := entry.get("summary"):
        lines.append(summary)

    if archetype == "mechanic":
        lines.extend(entry.get("state", []))
        if branch := entry.get("branch"):
            lines.append(f"When {branch['when']}:")
            for opt in branch["options"]:
                line = f"- {opt['condition']}: {opt['outcome']}"
                if detail := opt.get("detail"):
                    line += f" — {detail}"
                lines.append(line)
        for label, value in entry.get("effects", {}).items():
            lines.append(f"{label}: {value}")
        for item in entry.get("ends_when", []):
            lines.append(f"Ends when: {item}")

    elif archetype == "procedure":
        for i, step in enumerate(entry["steps"], 1):
            line = f"{i}. "
            if actor := step.get("actor"):
                line += f"{actor}: "
            line += step["action"]
            if note := step.get("note"):
                line += f" — {note}"
            lines.append(line)

    elif archetype == "penalty":
        lines.append(f"Infraction: {entry['infraction']}")
        for line in entry.get("handling", []):
            lines.append(f"Handling: {line}")
        for example in entry.get("examples", []):
            lines.append(f"Example: {example}")
        for row in entry["base_penalty"]:
            line = f"Penalty ({row['tier']}): {row['penalty']}"
            if note := row.get("note"):
                line += f" — {note}"
            lines.append(line)
            for example in row.get("examples", []):
                lines.append(f"  e.g. {example}")
        for cond in entry.get("upgrade_conditions", []):
            lines.append(f"Upgrades: {cond}")

    elif archetype == "definition":
        for term in entry["terms"]:
            lines.append(f"{term['term']}: {term['meaning']}")

    elif archetype == "note":
        lines.extend(entry["paragraphs"])

    return "\n".join(lines)
