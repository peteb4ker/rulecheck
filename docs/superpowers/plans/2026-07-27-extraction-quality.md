# Extraction Quality (Issue #8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix truncated wrapped section titles generically, and add a per-document layout-aware extraction flag with a one-cycle evaluation on tcg-rules.

**Architecture:** Two additive changes in the pipeline: a title-continuation rule in `build_tree`, and an optional `layout` manifest field switching `extract_lines` to pdfplumber's `layout=True` mode. Evaluation is data-driven with hard regression gates (identical section IDs; persona anchors pass).

**Tech Stack:** Existing pipeline (Python/uv/pytest, pdfplumber).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-27-extraction-quality-design.md`
- Content is never hand-edited; only the manifest and code change, content regenerates via `just all` and must end `verify OK`.
- Suite green throughout (`just test`, currently 39); commits Conventional with the `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer.

---

### Task 1: Title continuation rule

**Files:** Modify `pipeline/src/benchside_pipeline/parse.py` (`build_tree`); test `pipeline/tests/test_parse.py`.

- [ ] Failing tests: wrapped title joined; heading-follows case not joined:

```python
def test_wrapped_title_ending_in_comma_joins_next_line(fixture_source):
    lines = ["1. Alpha, Beta,", "and Gamma Cards", "body text here"]
    sections = build_tree(lines, fixture_source)
    assert sections[0].title == "Alpha, Beta, and Gamma Cards"
    assert sections[0].body == "body text here"


def test_no_join_when_next_line_is_heading(fixture_source):
    lines = ["1. Alpha,", "2. Beta", "body b"]
    sections = build_tree(lines, fixture_source)
    assert [s.title for s in sections] == ["Alpha,", "Beta"]
```

- [ ] Implement in `build_tree`: after creating `sec` from a heading whose `title` ends with `","`, peek the next non-empty line; if it does not classify as a heading, consume it and set `sec.title = f"{sec.title} {line}".strip()` (update breadcrumb construction accordingly — breadcrumbs are built from ancestor titles at creation time, so apply the join before constructing the Section / pushing to the stack; restructure the loop to look ahead via index iteration).
- [ ] `just test` green; commit `fix(pipeline): join wrapped section titles that end with a comma`.

### Task 2: `layout` manifest flag + evaluation

**Files:** Modify `pipeline/src/benchside_pipeline/model.py` (SourceDoc `layout: bool = False`), `manifest.py` (OPTIONAL += "layout"), `parse.py` (`extract_lines(pdf_path, layout=False)` and `parse_pdf` passes `source.layout`); tests in `test_manifest.py`, `test_parse.py`; possibly `sources/sources.yaml` + regenerated `content/` (evaluation outcome).

- [ ] Failing tests: manifest round-trips `layout: true`; `extract_lines(path, layout=True)` still returns the fixture lines (fixture PDF is single-column; both modes must find the headings).
- [ ] Implement; `just test` green; commit `feat(pipeline): per-document layout-aware extraction flag`.
- [ ] **Evaluation cycle:** set `layout: true` on tcg-rules only → `just all`. Hard gates: `verify OK`; tcg section count still 66 with identical IDs (`git diff content/tcg-rules.json` inspected — structure hunks only if bodies changed); `uv run pytest tests/test_personas.py -v` passes. Soft gate: read the new bodies of Turn Actions / Setting Up to Play / Energy Types in the diff — genuinely more readable?
- [ ] Decision per spec: keep flag on (commit manifest + content: `feat(content): layout-aware extraction for tcg-rules`) OR revert flag to false and note the outcome in the PR body. Either way update issue #8 with findings.

## Definition of Done

- Both wrapped titles whole in `content/tcg-rules.json`; no body leakage of title fragments.
- Suite green (41 tests after additions); `verify OK`; persona tests pass at DB level.
- PR closes #8 with the evaluation outcome documented.
