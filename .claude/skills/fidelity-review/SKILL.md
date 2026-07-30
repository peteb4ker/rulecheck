---
name: fidelity-review
description: Use after authoring a batch of rewrite entries - adversarially verifies each entry carries the source's meaning, before the batch is committed
---

# Fidelity Review

Independently verify that authored entries mean what the source means.

**Announce at start:** "Using fidelity-review on <n> entries in <doc>."

<HARD-RULE>
The author does not review their own work. Every batch this process has
produced contained at least one real defect the author missed and an
independent reviewer caught — including a missing game-scope qualifier
that would have made a judge rule incorrectly, and a dropped rule players
encounter every single game. Self-review is not a substitute; it is how
those defects survive.
</HARD-RULE>

## Method

**Batch-read, then analyse.** Read the whole `rewrites/<doc>.json` once and
the whole `content/<doc>.json` once, then compare. Reading section-by-
section burns turns and loses the cross-section context you need to judge
corroboration.

For each entry, compare against the matching section's verbatim `body`.

## What counts as a finding

The bar: **would someone relying on the entry act differently than someone
reading the source?** If no, it is not a finding.

| Class | Meaning |
|---|---|
| `DRIFT` | The entry states something the source doesn't, or contradicts it |
| `OMISSION` | A load-bearing fact is missing |
| `INVENTION` | A rule, number, or condition appears that isn't in the source |

Severity is `high` when a reader would act wrongly on a rule they'd hit in
normal play or adjudication; `low` for fine-grained phrasing that doesn't
change behaviour.

**Not findings** — do not report these: style, compression that keeps the
point, reordering, archetype choice, or the deliberate removal of
character/species names (that removal is policy).

## Maximum-scrutiny checklist

Every one of these has produced a real defect. Check them explicitly:

- **Numbers**: counts, thresholds, time limits, deck caps, prize payouts,
  round structures. Verify each against source rather than sampling.
- **Tier→penalty mappings** and which examples sit under which tier.
- **Game-scope qualifiers** (TCG / VG / GO / UNITE). A procedure scoped to
  one game presented as general is a high-severity finding.
- **Modality**: `may` vs `must`.
- **and/or logic**: an "any of these" trigger rendered as "all of these"
  narrows when a rule fires.
- **Cross-section synthesis**: if an entry states a fact not in its own
  source section, verify it is genuinely corroborated elsewhere in the
  corpus. Accurate synthesis is sanctioned; unverified assertion is not.
  Use `just corroborate "the words in question"` rather than grep. It
  searches the source text and our entries together, and it matches
  inflections, so a search for "damage counter" also finds "damage
  counters". A section listed as `ours only` uses a word our entry uses and
  the rulebook never does, which is where to look first.
- **Invention from world knowledge**: when a source section is thin or
  label-only, an author may fill gaps from general knowledge. Judge each
  such statement: supported by the corpus, or invented? (A real review
  found 3 of 11 terms unsupported this way.)
- **Character/species names** surviving into an entry — a policy violation,
  report it.

## Degraded source text

Some sources are multi-column extractions with rotated diagram labels
(mirrored words like `SDRAC`, `EZIRP`, `EVITCA`). That noise is not
content: do not report its absence as an omission. **Do** report an entry
that copied scrambled text in, or a real rule buried in the noise that the
entry missed.

## Watch for guard evasion

If an entry's text looks like source text merely reordered or permuted,
report it. Reversing a list to defeat the 12-token overlap tripwire leaves
the copying intact and only disables the check — this really happened. The
correct outcomes are restructure, summarize-and-point, or skip.

## Output

Numbered findings — id, class, one sentence, severity — or `NO FINDINGS`.
Then adjudicate anything the author explicitly flagged as uncertain
(agree/disagree plus why). Then a one-line verdict.

Report findings; do not fix them. The author applies fixes, so the
authoring context stays with the author and the review stays independent.

**Including the serious ones.** Finding a high-severity defect is not a
licence to correct it. A reviewer who fixes an entry and then records a
verdict on it has reviewed its own writing, which is the one thing this
process exists to prevent, and the finding it was proudest of is the one
where its judgement is now worth least. Hand it on instead.

## Recording the verdict

Write results to `validation/<doc-id>.json` so the review is durable and
machine-checkable rather than living in a chat transcript:

```json
{
  "<section-id>": {
    "entry_sha256": "<sha256 of the canonical entry JSON>",
    "verdict": "clean",
    "findings": []
  }
}
```

The hash is what makes this trustworthy: if an entry is edited after
review, the recorded hash no longer matches and the buddy script flags it
as stale rather than silently accepting an unreviewed change.

### Handing a high-severity finding on

A high-severity finding must say what happens next. Two ways:

```json
{"class": "OMISSION", "severity": "high", "note": "…",
 "acknowledged": true, "owner": "author"}
```

`acknowledged` with an `owner` is the reviewer's move: the defect is real,
it is somebody's, and the reviewer is not touching the content. The review
gate goes green; the release gate does not, because handing a defect over
does not close it.

`resolved: true` is the author's move, recorded when the entry is corrected.
A reviewer setting this on its own fix is the failure described above. The
two are mutually exclusive and the buddy script rejects both at once.

## Validate with the buddy script

```bash
just check-fidelity-review --doc tcg-rules
```

Deterministic gate: every non-skipped entry has a verdict, no verdict is
stale against its entry, every high-severity finding is either resolved or
owned, no orphan records.

Pass `--doc` while reviewing one document. Without it every entry in every
other document prints a pending line — 183 of them at the time of writing —
and the one line that matters is somewhere in the middle of them.
