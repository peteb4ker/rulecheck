# Extraction Quality (Issue #8) — Design Spec

**Date:** 2026-07-27 · **Status:** Approved by Pete · **Scope decision:**
"titles + light touch" — Plan 1.2's paraphrase supersedes garbled *bodies*,
so this fix targets what survives 1.2 (titles/structure) plus a timeboxed
layout-extraction experiment for the ~5 garbled rulebook sections.

## Problem

1. **Truncated wrapped titles** (structural defect): headings are captured
   from single extracted lines; a PDF title that wraps loses its tail to
   the body. Two known cases in tcg-rules, both with the same signature —
   the captured title ends with `,` (e.g. `Appendix 18: Rare Fossil,
   Unidentified Fossil,` — the wrapped remainder "and Antique Fossil
   Cards" leaks into the body as its first line).
2. **Garbled multi-column bodies** (~5 of 66 tcg-rules sections: Zones,
   Setting Up to Play, Turn Actions, Energy Types, Glossary/Credits):
   pdfplumber's default line extraction interleaves columns/diagram
   labels ("SDRAC", "2) DoK ACnyE oDf …").

## Design

1. **Title continuation rule** in `build_tree` (`parse.py`): after
   classifying a heading, if its title ends with `,` and the *next*
   non-empty line does not classify as a heading, append that line to the
   title (single join, no recursion). Applies to all documents; no config.
2. **Per-document `layout: bool` manifest flag** (optional, default
   false): when set, `extract_lines` uses pdfplumber's
   `extract_text(layout=True)` for that document. Purely additive;
   `SourceDoc` gains `layout: bool = False`, joins `OPTIONAL` keys.
3. **Empirical evaluation, timeboxed to one cycle**: parse tcg-rules with
   `layout: true`; hard gate — section count/IDs must be unchanged
   (66 sections, identical IDs) and the two persona anchors must still
   pass; soft gate — human-readable improvement in the garbled sections'
   bodies (judged from the content diff). Keep the flag on for tcg-rules
   only if both gates pass; otherwise ship the flag off (code stays,
   tested) and the garbled bodies remain Plan 1.2's problem. Either
   outcome closes #8's title half and documents the body half.

## Testing

- Unit: wrapped-title fixture (title ending `,` + continuation line) →
  joined title, continuation absent from body; negative case (title ends
  `,` but next line is a heading) → no join.
- Unit: `layout` manifest round-trip; `extract_lines` honors the flag
  (fixture PDF parses under both modes).
- Regression: full suite (39 pipeline tests) green; content diff reviewed;
  DB-level persona queries pass; app suite unaffected (schema unchanged).

## Out of scope

- Full column-aware extraction rewrite; per-section manual body overrides;
  anything Plan 1.2 (#20) supersedes.
