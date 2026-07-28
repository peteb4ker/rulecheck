# Structured Rulebase (Issue #20, Plan 1.2 re-scoped) — Design Spec

**Date:** 2026-07-27 · **Status:** Approved direction (Pete); spec pending review
**Supersedes:** the prose-paraphrase approach approved earlier on #20 (never
specced — superseded by the design package's "rule as structure, not prose").

## What this is

Convert the rulebase from extracted prose into an authored, validated,
structured representation. The structure IS the paraphrase: states,
branches, tables, steps, and short original micro-copy are inherently
non-verbatim (a stronger legal posture than prose rewriting, per the
research gate), and they feed the design package's diagram UI directly.
Text search is preserved by indexing a deterministic flattening of the
structure. All three documents complete before any release.

## Decisions locked in

| Decision | Choice |
|---|---|
| Authoring | Claude drafts every section; tiered human review (judge tier eyes-on, standard tier spot-checked); review status tracked per section |
| Rollout | All three documents structured before release; order penalty-guidelines → tournament-rules → tcg-rules; pilot of ~30 hot sections across all archetypes first to validate the schema |
| Verbatim | Research-gate hybrid: declared short `quotes[]` only, usable in any text field; ≥12-consecutive-word undeclared overlap with source verbatim fails verify |
| Phase split | Phase 1 (this spec): content model + authoring + validation, flattened into the existing `sections.body` at build — **zero DB-schema or app changes**. Phase 2 (later, separate effort): structured payload in the DB + diagram rendering, coordinated with the #29 design refresh |
| Exact-wording UI | The design's "Exact wording" toggle ships constrained: declared quotes + citation to the official document, never the full verbatim body |

## The archetype family

Every leaf section gets exactly one archetype (containers need none —
their children carry content; verify enforces this partition):

1. **`mechanic`** — game mechanics. Fields: `summary`, `state[]` (facts
   true while in effect), `branch` (`when`, `options[]` of
   {condition, outcome, detail?}), `ends_when[]`, `effects{}` (label →
   value truth table), `see_also[]`.
2. **`procedure`** — ordered processes (setup, deck checks, penalty
   application). Fields: `summary`, `steps[]` ({actor?, action, note?}),
   `see_also[]`.
3. **`penalty`** — infraction entries. Fields: `summary`, `infraction`,
   `examples[]`, `base_penalty` ({tier, penalty}[] table),
   `upgrade_conditions[]`, `see_also[]`.
4. **`definition`** — term lists (Glossary). Fields: `terms[]`
   ({term, meaning}).
5. **`note`** — prose that resists structure (philosophy, intros,
   credits). Fields: `summary`, `paragraphs[]`. This is the plain-text
   fallback archetype; it is still paraphrase and overlap-guarded.

Cross-cutting fields on every entry: `archetype`, `tier`
(`judge` | `standard`), `review` (`pending` | `reviewed`), optional
`quotes[]` (exact verbatim spans, each declared here AND present in the
source section AND used in some text field). Empirical grounding: the
penalty guidelines are step/penalty shaped (23/68 numbered-step bodies,
penalty vocabulary in 55/68), the handbook is bullet-policy shaped
(24/119), the rulebook is mechanic prose plus a 12k-char Glossary.

## Skiplist (added 2026-07-27, issue #44)

Some sections do not belong in a search-first rules app: diagram furniture
with no prose, colophons, and long reference enumerations better served by
a pointer to the official source. A rewrite entry may instead be
`{"skip": "<reason>"}` — a mandatory reason makes every exclusion a
recorded decision.

**Skip means excluded from the build, never shipped verbatim.** Skipped
sections are omitted from `sections`, from FTS, from document outlines and
from xrefs; leaving them as source text would defeat the rewrites layer
entirely. Verify enforces: skip stands alone (no content fields), names a
real section, satisfies coverage, and nothing may `see_also` a skipped
section (it does not exist in the app).

Struggling to paraphrase is a signal to consider skipping — never a
licence to permute or reorder source text to evade the overlap guard.

## Storage & pipeline

- New committed layer `rewrites/<doc-id>.json`: `{section_id: entry}`.
  Hand-authored (drafted by Claude, edited by humans), never touched by
  `parse`. `content/` remains the machine-regenerated verbatim reference
  (internal only; repo stays private until its handling is decided).
- **Build (phase 1):** `sections.body` in the shipped DB is produced by a
  deterministic archetype-aware flattening of the rewrite entry (e.g.
  mechanic: summary ¶ state lines ¶ "When <when>:" branch lines ¶
  effects "label: value" lines ¶ ends-when lines). Same schema, same app,
  same FTS behavior; search hits now land on structured-derived text.
- **Verify additions (release mode):**
  - coverage: every leaf section has a rewrite entry; no orphan entries
    (stale IDs after re-ingest fail loudly);
  - archetype validity: required fields per archetype, non-empty;
  - `see_also` targets exist;
  - quotes: each declared quote appears verbatim in the source section
    body AND in the entry's own text; no undeclared ≥12-word overlap
    between any entry text field and the source body;
  - review gate: `tier: judge` entries must be `review: reviewed`.
  Non-release verify reports the same as warnings + a coverage summary.
- `just content-status`: per-document coverage / archetype mix / review
  state report.
- Persona anchors re-validated against flattened text (search behavior
  will shift — the gates are the tripwire, and ranking tuning stays
  within the established levers).

## Authoring workflow

Per document: draft in PR-reviewable chunks (~50-70 sections), each chunk
passing an adversarial fidelity pass (fresh reviewer instance compares
entry against verbatim source for meaning drift; findings listed in the
PR) before human review. Judge-tier sections enumerated explicitly in
each PR description for eyes-on review. Pilot chunk first: ~30 hot
sections spanning all five archetypes (special-conditions cluster,
deck-check procedures, a penalty family, a Glossary slice, notes),
schema adjusted from pilot findings before mass authoring.

## Out of scope (phase 2+, separate efforts)

- DB structured-payload column(s) and app diagram rendering (#29's later
  phases / the "generalize the design" hand-off).
- Going public; `content/` verbatim quarantine strategy.
- Any change to search UX or app code.

## Testing

- Pipeline unit tests: flattening per archetype (golden outputs), each
  verify rule (positive + negative fixtures), quotes guard both
  directions, overlap detector (n-gram window) with boundary cases.
- Persona acceptance at DB level after each document lands.
- App suite untouched but run per document PR (bundled DB content
  changes).
