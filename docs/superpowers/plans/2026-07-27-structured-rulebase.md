# Structured Rulebase — Phase 1 Infrastructure + Pilot (Issue #20) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the rewrites layer (schema validation, flattening, verify guards, CLI/status integration) and prove it with a ~30-section pilot spanning all five archetypes.

**Architecture:** New `rewrites/<doc-id>.json` committed layer validated by hand-rolled per-archetype checks (no new deps). Build flattens entries into the existing `sections.body`; verify gains rewrite guards (coverage, see-also, quotes discipline, 12-gram overlap tripwire, judge review gate) with `--release` strictness. Zero DB-schema/app changes.

**Tech Stack:** Existing pipeline (Python/uv/pytest). No new dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-27-structured-rulebase-design.md`
- Zero new runtime deps; zero DB-schema changes; app untouched.
- Text comparisons (quotes, overlap) whitespace-normalized (collapse runs of whitespace to single spaces) — layout-mode extraction pads lines.
- Suite green throughout (`just test`, 43 now); Conventional Commits with trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Do not touch `app/` (owned by the parallel #29 effort).

---

### Task 1: Rewrite entry validation (`rewrites.py`)

**Files:** Create `pipeline/src/benchside_pipeline/rewrites.py`; test `pipeline/tests/test_rewrites.py`.

**Interfaces:**
- Produces: `ARCHETYPES: dict[str, dict]` (required/optional field specs); `validate_entry(section_id: str, entry: dict) -> list[str]` (error strings, `[]` = valid); `load_rewrites(rewrites_dir: Path) -> dict[str, dict]` (doc-id-keyed union of `{section_id: entry}` maps from every `rewrites/*.json`, filename = `<doc-id>.json`; malformed JSON or duplicate section ids raise `RewriteError`).

Field specs (from the spec doc):

```python
COMMON_REQUIRED = ("archetype", "tier")
COMMON_OPTIONAL = ("review", "quotes", "see_also")   # review defaults "pending"
ARCHETYPES = {
    "mechanic":   {"required": ("summary",), "optional": ("state", "branch", "ends_when", "effects")},
    "procedure":  {"required": ("summary", "steps"), "optional": ()},
    "penalty":    {"required": ("summary", "infraction", "base_penalty"), "optional": ("examples", "upgrade_conditions")},
    "definition": {"required": ("terms",), "optional": ()},
    "note":       {"required": ("summary", "paragraphs"), "optional": ()},
}
```

Validation rules: unknown archetype; missing required fields; unknown fields (not common/archetype); `tier` ∈ {judge, standard}; `review` ∈ {pending, reviewed}; `steps`/`terms`/`paragraphs` non-empty lists when present; `branch` requires `when` + non-empty `options` each with `condition`+`outcome`; `base_penalty` non-empty list of {tier, penalty}; `effects` non-empty str→str map when present.

- [ ] Failing tests: one valid entry per archetype validates clean; each rule above has a negative test (12+ cases, table-driven with `pytest.mark.parametrize`); `load_rewrites` round-trips a fixture dir and raises on duplicate ids across files.
- [ ] Implement; `just test` green; commit `feat(pipeline): rewrite entry schema validation`.

### Task 2: Deterministic flattening (`flatten.py`)

**Files:** Create `pipeline/src/benchside_pipeline/flatten.py`; test `pipeline/tests/test_flatten.py`.

**Interfaces:**
- Produces: `flatten_entry(entry: dict) -> str` — archetype-aware, deterministic, newline-joined. Field order fixed: summary; then archetype body (mechanic: state lines, `When {when}:` + `- {condition}: {outcome}[ — {detail}]` options, effects as `{label}: {value}`, `Ends when:` lines; procedure: `1. [{actor}: ]{action}[ — {note}]` numbered steps; penalty: infraction, `Examples:` lines, `Penalty ({tier}): {penalty}` lines, `Upgrades:` lines; definition: `{term}: {meaning}` lines; note: paragraphs). No trailing whitespace; two flattens of the same entry byte-identical.

- [ ] Failing tests: golden output per archetype (exact expected strings); determinism (flatten twice, equal); minimal entries (only required fields) flatten without empty-section headers.
- [ ] Implement; `just test` green; commit `feat(pipeline): archetype-aware flattening to searchable text`.

### Task 3: Verify guards for the rewrites layer

**Files:** Create `pipeline/src/benchside_pipeline/content_check.py`; modify `pipeline/src/benchside_pipeline/verify.py` (no changes to DB checks) and `__main__.py` (wire below); test `pipeline/tests/test_content_check.py`.

**Interfaces:**
- Produces: `check_rewrites(content_dir: Path, rewrites_dir: Path, release: bool = False) -> list[str]`:
  1. entry validation errors (Task 1) for every entry;
  2. coverage: every **leaf** section (per content JSON) has an entry — error in release mode, `warning:`-prefixed string otherwise; container sections must NOT have entries (error always);
  3. orphans: entry ids absent from content — error always;
  4. `see_also` ids exist in content (any document) — error;
  5. quotes: whitespace-normalized quote must be substring of the source section's normalized body AND of some normalized entry text field — error;
  6. overlap tripwire: any 12-consecutive-token run (casefolded, whitespace-normalized) shared between an entry text field and the source body, not fully inside a declared quote — error;
  7. release mode: `tier: judge` entries with `review != reviewed` — error.
- Text-field enumeration: every str value and str list element in the entry except `archetype`/`tier`/`review`/`see_also` keys.

- [ ] Failing tests: fixture content dir + rewrites dir exercising each rule positively and negatively (coverage warn vs release error; quote declared→ok; same sentence undeclared→error; 11-token overlap→ok, 12→error).
- [ ] Implement (n-gram: sliding window over token lists; declared-quote token spans subtracted); `just test` green; commit `feat(pipeline): rewrites verification — coverage, quotes discipline, overlap tripwire`.

### Task 4: Build + CLI integration

**Files:** Modify `pipeline/src/benchside_pipeline/build.py` (body substitution), `__main__.py` (`verify --release` flag; `content-status` subcommand); `justfile` (`content-status` recipe; `verify` recipe unchanged); test `pipeline/tests/test_build.py`, `test_cli.py` additions.

**Interfaces:**
- `build_db(content_dir, out_path, rewrites_dir: Path | None = None)`: when a section has a rewrite entry, `sections.body` ← `flatten_entry(entry)`; sections without entries keep verbatim body (pilot-phase mixed state is expected; release coverage gate is verify's job, not build's).
- `python -m benchside_pipeline verify [--release] --root ..`: runs DB checks + `check_rewrites` when `rewrites/` exists; `--release` escalates coverage/review to errors.
- `python -m benchside_pipeline content-status --root ..`: per-document table — leaves, entries, coverage %, archetype counts, review counts. Exit 0 always.
- `all` = parse → build (with rewrites) → verify (non-release).

- [ ] Failing tests: build substitutes flattened body for a fixture section with an entry and leaves others verbatim; `verify --release` exit 1 on coverage gap, 0 when complete+reviewed; `content-status` output contains coverage line.
- [ ] Implement; `just test` green; `just all` on real corpus still `verify OK` (no rewrites yet → warnings only); commit `feat(pipeline): rewrites-aware build, release verify, content-status`.

### Task 5: Pilot — ~30 hot sections across all archetypes

**Files:** Create `rewrites/tcg-rules.json`, `rewrites/tournament-rules.json`, `rewrites/penalty-guidelines.json` (partial — pilot sections only).

Selection (adjust for actual ids at execution; aim ~30): the special-conditions cluster incl. Asleep (mechanic ×6-8), setup/mulligan + deck-check/legality-check procedures (procedure ×5-6), one penalty family e.g. §5.6.x (penalty ×5-6), a Glossary slice (definition ×1 covering ~15 terms), intro/philosophy sections (note ×3-4), plus both persona-anchor sections whatever their archetype.

- [ ] Author entries (drafted from `content/` verbatim reference; structure per archetype; judge tier for penalty/procedure tournament content, standard for rulebook mechanics; quotes only where exact wording is load-bearing — expect few).
- [ ] `just all` → verify passes with coverage warnings only for un-piloted sections; zero quote/overlap/see-also errors.
- [ ] Adversarial fidelity pass: for each pilot entry, an independent reviewer compares entry against source body for meaning drift/omission/invention; findings fixed or logged in the PR description.
- [ ] Persona anchors: DB-level persona tests pass against the flattened pilot content (Asleep top hit must survive its body becoming structured text — if ranking shifts, tune within established levers only; BLOCKED if impossible).
- [ ] Schema retro: list any field the pilot needed and lacked, or lacked and needed; spec/plan amended before mass authoring.
- [ ] Commit `feat(content): structured-rulebase pilot — 30 sections across five archetypes`.

## Definition of Done

- All verify guards implemented + tested (both directions); suite green (expect ~60 pipeline tests).
- Pilot: ~30 entries, fidelity-passed, verify clean (warnings only for coverage), persona gates green, schema retro recorded.
- `just content-status` reports the pilot accurately.
- PR closes nothing (#20 stays open through mass authoring) but links the pilot evidence.

---

## Pilot Retro (2026-07-27, executed)

Schema survived contact with two amendments and four policy findings:

1. **Coverage is body-based, not leaf-based** — containers can carry real
   prose (tcg-Special Conditions). Authoring universe is 247 sections, not
   183. Implemented in content_check.
2. **Penalty archetype v1.1** — real penalty sections need per-severity
   examples (`base_penalty[].examples`, `.note`) and judge `handling[]`
   guidance. Implemented with tests.
3. **Character names lurk in verbatim sources** (Glossary examples) and
   currently ship; rewrites must strip them (policy: never carry
   character/species names into entries — structured rewrite fixes this
   for free).
4. **Cross-section synthesis is sanctioned**: effects tables may state
   facts corroborated elsewhere in the corpus (e.g. Asleep's
   "Abilities: Still usable"); the fidelity pass verifies corroboration.
   Two such facts in the pilot, both verified accurate.
5. **Pilot depth over breadth**: 17 entries (all five archetypes, incl.
   the full 68-term Glossary and the largest penalty section) instead of
   ~30 shallow ones. Fidelity pass: no drift, no omission, no incorrect
   invention.
6. **Tier reflects citation criticality, not host document** — intro
   notes in judge documents are standard tier; procedures/penalties
   judges cite are judge tier.

Mass authoring may proceed on schema v1.1.
