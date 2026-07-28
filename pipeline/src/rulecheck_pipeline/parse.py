from __future__ import annotations

import re
import sys
from pathlib import Path

import pdfplumber

from rulecheck_pipeline.headings import classify_line
from rulecheck_pipeline.model import Section, SourceDoc


def extract_lines(pdf_path: Path, layout: bool = False) -> list[str]:
    """Extract text lines; layout=True uses pdfplumber's layout-aware
    mode, which preserves column geometry on multi-column pages."""
    lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=layout) or ""
            lines.extend(text.splitlines())
    return lines


def build_tree(lines: list[str], source: SourceDoc) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, Section]] = []
    body: list[str] = []
    seen_ids: set[str] = set()
    strip_res = [re.compile(p) for p in source.strip_lines]

    def flush() -> None:
        if stack and body:
            sec = stack[-1][1]
            text = "\n".join(body).strip()
            sec.body = f"{sec.body}\n{text}".strip() if sec.body else text
        body.clear()

    clean = [
        line for line in (raw.strip() for raw in lines)
        if line and not any(r.search(line) for r in strip_res)
    ]

    i = 0
    while i < len(clean):
        line = clean[i]
        heading = classify_line(line, source.heading_rules)
        if heading is not None:
            sec_id = f"{source.prefix}-{heading.number}"
            if sec_id in seen_ids:
                # Some real-world documents (e.g. a "Summary of Changes"
                # table) repeat an earlier heading's number verbatim as
                # plain body content — sometimes with the same title,
                # sometimes with a different one. Either way, the number
                # collides on id, so treat the second occurrence as body
                # text rather than crashing the build on a duplicate
                # primary key. This is matched on number only (not
                # number+title), so print a warning: a future document
                # that genuinely reuses a number for a distinct heading
                # would otherwise be silently absorbed into the wrong
                # section's body.
                print(
                    f'warning: {source.id}: duplicate heading id {sec_id} '
                    f'("{heading.title}") treated as body text',
                    file=sys.stderr,
                )
                heading = None
        if heading is None:
            body.append(line)
            i += 1
            continue
        # A PDF title that wraps loses its tail to the next line; the
        # known signature is a title ending in a comma. Join exactly one
        # continuation line, provided it isn't itself a heading.
        if (
            heading.title.endswith(",")
            and i + 1 < len(clean)
            and classify_line(clean[i + 1], source.heading_rules) is None
        ):
            heading.title = f"{heading.title} {clean[i + 1]}"
            i += 1
        flush()
        while stack and stack[-1][0] >= heading.level:
            stack.pop()
        parent = stack[-1][1] if stack else None
        crumb = " › ".join([source.title] + [s.title for _, s in stack])
        sec = Section(
            id=f"{source.prefix}-{heading.number}",
            doc_id=source.id,
            parent_id=parent.id if parent else None,
            number=heading.number,
            title=heading.title,
            body="",
            breadcrumb=crumb,
            order=len(sections),
        )
        sections.append(sec)
        seen_ids.add(sec.id)
        stack.append((heading.level, sec))
        i += 1
    flush()
    return sections


def parse_pdf(pdf_path: Path, source: SourceDoc) -> list[Section]:
    return build_tree(extract_lines(pdf_path, layout=source.layout), source)
