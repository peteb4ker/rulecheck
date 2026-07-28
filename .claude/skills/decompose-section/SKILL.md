---
name: decompose-section
description: Use when converting a source rule section into a structured rewrite entry (or deciding it should be skipped) - covers archetype choice, authoring rules, and the paraphrase guards
---

# Decomposing a Section

Turn one verbatim source section into an authored structured entry, or
decide it does not belong in the app at all.

**The structure IS the paraphrase.** You are not summarizing prose; you are
re-expressing a rule as states, branches, steps, tables, or terms, in your
own words. That is what makes the shipped content transformative rather
than a copy.

**Announce at start:** "Using decompose-section to author <section-id>."

## Step 0: Read the whole source document once

Batch-read `content/<doc-id>.json` in full before authoring anything. You
need neighbouring sections to resolve cross-references and to corroborate
facts. Reading section-by-section wastes turns and loses context.

## Step 1: Decide whether this section ships at all

**Skip-with-reason is a first-class outcome, not a failure.** Before
authoring, ask whether the section belongs in a search-first rules app.

Skip when:

- **No prose to work from** — the source is diagram callouts or table
  furniture. Anything you write would be invention. (Real case: a card
  anatomy section whose source was bare labels; a reviewer found 3 of 11
  authored terms unsupported by any source text.)
- **No rules content** — colophons, credits, marketing framing.
- **Unsearchable reference data** — long enumerations nobody consults
  mid-event, better served by a pointer to the official source. (Real case:
  rating-zone country tables.)

Skip form — the reason is mandatory, so every exclusion is a recorded
decision:

```json
"<section-id>": {"skip": "why this never reaches the app"}
```

Skipped sections are omitted from the built database entirely. They are
never shipped as verbatim source text.

<HARD-RULE>
Struggling to paraphrase is a signal to consider skipping. It is NEVER a
licence to permute, reorder, or otherwise contort source text to slip past
the overlap guard. A real session did this — reversing a country list to
defeat the 12-token tripwire — and it is content copying with the guard
disabled. The honest outcomes are: restructure, summarize-and-point, or
skip.
</HARD-RULE>

## Step 2: Choose the archetype

| Archetype | Use for | Required fields |
|---|---|---|
| `mechanic` | Game rules with state/branch/effects shape | `summary` |
| `procedure` | Ordered processes | `summary`, `steps` |
| `penalty` | Infractions mapped to penalties | `summary`, `infraction`, `base_penalty` |
| `definition` | Term or type lists | `terms` |
| `note` | Prose that resists structure | `summary`, `paragraphs` |

Pick by the shape of the content, not by the host document. `note` is the
honest fallback, not a defeat — but reach for it last.

## Step 3: Author

Non-negotiable rules, every one learned from a real defect:

- **Never 12+ consecutive tokens shared with the source.** The verify
  tripwire fails the build. Genuinely re-express.
- **Preserve every load-bearing fact**: numbers, thresholds, tier→penalty
  mappings, deadlines, counts, deck caps, per-game limits.
- **Preserve modality exactly** — `may` is not `must`. A real finding
  turned "records may be retained" into a directive.
- **Preserve and/or logic exactly** — a real finding turned an "any of
  these" trigger into "all of these", narrowing when an escalation applies.
- **State game-scope qualifiers explicitly** (TCG / VG / GO / UNITE) in
  every field where the source scopes them. A real finding produced a
  GO-only tiebreaker procedure presented as a general rule; a judge would
  have ruled incorrectly in a TCG match.
- **Never include Pokemon character or species names**, even where the
  source uses them in examples. Generalize to card classes ("a Basic
  Pokémon", "a Stage 2"). Sources use them heavily; shipped content must
  not.
- **Cross-section synthesis is allowed only when corroborated** elsewhere
  in the corpus — state a fact from a neighbouring section only if you have
  actually read it there. Note it for the reviewer.
- **Declared quotes are rare.** Use `quotes: ["..."]` only where the exact
  official wording is load-bearing; each must appear verbatim in the source
  AND in your entry text.
- **`see_also` must point at ids that exist and are not skipped.**
- `tier`: `judge` for anything staff cite or enforce; `standard` for
  player-facing content.

## Step 4: Watch for search-ranking side effects

Entries feed the FTS index. Heavy keyword repetition can steal a persona
gate's top hit — this really happened: a reworded entry repeated "deck"
enough to outrank the section the judge persona test expects. Run the
persona gates as part of authoring, not just in CI.

## Step 5: Validate with the buddy script

```bash
just check-decomposition
```

Deterministic gate: runs schema validation, coverage, quotes discipline,
the overlap tripwire, see-also integrity, rebuilds the database, and runs
the persona acceptance tests. Fix every error before handing off. Warnings
about un-authored sections elsewhere are expected mid-project.

## Handing off for review

Authoring is not done until an independent fidelity pass has run — see the
`fidelity-review` skill. Self-review does not substitute: every batch this
process has produced contained at least one real defect that the author
missed and the reviewer caught.
