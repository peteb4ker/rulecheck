# Glyph rendering for players: implementation plan

> **Status 2026-07-31: tasks 1 to 5 shipped.** The glyph layer is on `main`
> and running. Task 6, the review gate, ran informally from simulator
> screenshots rather than as a written step. The follow-up work it produced is
> tracked as issues #52 and #53 rather than left in this plan.

**Goal:** A player reading a rule sees a glyph on each structured row, so the
shape of the rule is visible before a word is read. Phase one is the game
rules document, with SF Symbols standing in for real icons so the whole path
can be judged on a device before anything is sourced.

**Spec:** `docs/superpowers/specs/2026-07-31-glyph-rendering-design.md`. The
spec wins if this plan disagrees with it.

**Architecture:** The lexicon records which concepts get a glyph. The pipeline
matches those concepts inside structured field values at build time and writes
parallel glyph arrays into the entry JSON. The app decodes those arrays and
draws a symbol or a chip. No database schema change: the entry JSON already
ships whole in `sections.structure`.

**Tech stack:** Python via uv for the pipeline, SwiftUI and GRDB for the app,
both already in place. No new dependencies.

## Global constraints

- TDD throughout. A test must fail before the code that makes it pass exists,
  and both directions get verified. No placebo tests.
- Every module gets a test file. `pipeline/src/rulecheck_pipeline/glyphs.py`
  gets `pipeline/tests/test_glyphs.py`.
- Never push to `main`. Branch, PR, let CI run. `--no-verify` is off the table.
- Read every row of `gh pr checks`, not the tail.
- Commits use Conventional Commits with the body saying why, and keep the
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` trailer.
- `just all` and `just test` green before any PR.
- No Pokemon character or species names anywhere user-facing.
- The lexicon must stay re-derivable. Never hand-edit it into a state you
  could not reproduce.

---

### Task 1: Lexicon schema for glyphs

Validation before data, so the data cannot be written wrong.

**Files:**
- Modify: `pipeline/src/rulecheck_pipeline/lexicon.py`
- Modify: `pipeline/tests/test_lexicon.py`

**Interfaces:**
- Produces: `validate()` accepting and checking `glyph`, `glyph_render`,
  `glyph_note`, `glyph_triggers`. Task 2 writes data against this.

- [x] **Step 1: Write the failing tests**

Cover, in `test_lexicon.py`:

- `glyph` must be a boolean when present.
- `glyph: true` requires `glyph_render`.
- `glyph: false` requires `glyph_note`, so a held-out concept is always a
  recorded decision rather than an oversight.
- `glyph_render` is exactly one of `{"symbol": str}` or
  `{"chip": str, "tint": str}`, never both and never neither.
- A chip's text must be non-empty.
- `glyph_triggers` is a list of non-empty strings.
- `glyph_triggers` on a term with `glyph: false` is an error, since a
  held-out concept has nothing to trigger.
- A term with no `glyph` key at all is valid and gets no glyph.

Run them and confirm they fail:

```bash
cd pipeline && uv run pytest tests/test_lexicon.py -q
```

- [x] **Step 2: Extend `validate()` until they pass**

Keep the existing error-message style: name the term, say what is wrong, say
what to do about it.

- [x] **Step 3: Confirm the existing lexicon still validates**

```bash
just check-lexicon
```

No term has glyph fields yet, so this must pass unchanged. If it does not,
the new checks are firing on absent keys.

- [x] **Step 4: PR**

Title: `feat(lexicon): schema for glyph decisions`.

---

### Task 2: Classify the missing concepts and record the glyph decisions

**Files:**
- Modify: `content/lexicon/*.json`
- Modify: `scripts/check_lexicon.py`
- Modify: `pipeline/tests/test_check_lexicon.py` (create if absent)

**Interfaces:**
- Produces: 29 terms carrying `glyph: true` with a `glyph_render`, and 4
  carrying `glyph: false` with a `glyph_note`. Task 3 matches against these.

- [x] **Step 1: Classify the 12 terms not yet in the lexicon**

Follow `.claude/skills/build-lexicon/SKILL.md`. Eleven are glyph-bearing:
Paralyzed, Confused, Knock Out, search, Trainer card, Stadium, blocked,
allowed, Heads, Tails, face down. One is held out: Pokemon.

Two category questions the spec left open. Category drives the priority rule,
so decide rather than default, and put the reasoning in the gloss:

- **blocked** and **allowed**. Likely `modifier`: they qualify whether
  something may happen rather than naming a thing or an act.
- **Heads** and **Tails**. Coin outcomes. `state` fits the coin, `entity`
  fits the face. Lower stakes than it first appeared, since both render as
  chips and the rows they match are the literal words, so a competing match
  is unlikely.

- [x] **Step 2: Add glyph fields to all 33 terms**

The 29 glyph-bearing concepts and their counts are in the spec. Use SF Symbol
names for `glyph_render.symbol`.

Chips are the backstop for any concept where no symbol reads unambiguously,
so nothing is blocked on finding a good icon. Three are chips from the start:

```json
{ "chip": "ABILITY", "tint": "negative" }
{ "chip": "HEADS",   "tint": "accent" }
{ "chip": "TAILS",   "tint": "accent" }
```

Reach for a chip when the word is what a player recognises. Reach for a
symbol when a picture is faster to read than the word. Chipping everything
turns the page back into text, which is the thing this work exists to fix, so
prefer a symbol where one genuinely works and leave the rest for the review
gate in Task 6.

The four held out are attack, play, evolve and Pokemon. Each needs a
`glyph_note` giving its render count and why it is held out.

- [x] **Step 3: Write the failing buddy-script tests, then extend the script**

`check_lexicon.py` must additionally fail when:

- A `glyph_trigger` never occurs in the corpus, the same way an invented term
  does today.
- Two terms declare the same `glyph_render.symbol`, which would make two
  concepts indistinguishable on screen.

~~It must warn when a glyph-bearing term is dense enough that the glyph would
likely become wallpaper.~~ **Dropped, and the reason is worth keeping.** The
corpus does not support a threshold: "deck" is written 107 times and keeps
its glyph while "attack" is written 117 and does not, and by structured
renders it is 28 against 31. Any cut-off fires on the wrong terms often
enough to be ignored, and a check people ignore is worse than no check.
Judging this is what Task 6 is for.

- [x] **Step 4: Verify**

```bash
just check-lexicon
just test
```

- [x] **Step 5: PR**

Title: `feat(content): record which concepts carry a glyph`. The body should
list the four held out with their counts, since that is the decision most
likely to be questioned later.

---

### Task 3: Matching and priority

**Files:**
- Create: `pipeline/src/rulecheck_pipeline/glyphs.py`
- Create: `pipeline/tests/test_glyphs.py`

**Interfaces:**
- Produces: `glyph_for(text, terms) -> str | None` and
  `annotate(entry, terms) -> dict`. Task 4 calls `annotate`.

- [x] **Step 1: Write the failing tests**

- A value naming one glyph-bearing concept returns that glyph.
- Inflections match: "evolving" and "evolves" reach the same concept. Reuse
  the lexicon stemmer rather than writing a second one.
- Accents fold: "Pokémon" and "Pokemon" are the same word. This bit an
  earlier analysis and is worth a test of its own.
- A value naming no glyph-bearing concept returns `None`.
- A held-out concept returns `None` even though it is classified.
- Priority: a value naming both a `state` and an `entity` returns the state.
- Ties inside one category break toward the rarer concept.
- A term with two categories takes the higher priority of the two.
- A `glyph_trigger` phrase matches: "No attacking" returns the blocked glyph.
- Matching is deterministic: the same input returns the same glyph every time.

- [x] **Step 2: Implement until they pass**

Priority order is `state`, `modifier`, `entity`, `action`, `phase`. Rarity is
measured by total renders across the corpus, computed once rather than per
call.

- [x] **Step 3: Sanity check against the real corpus**

```bash
cd pipeline && uv run python -c "
import json, sys; sys.path.insert(0,'src')
from rulecheck_pipeline import glyphs, lexicon
# print every state line in tcg-rules with the glyph it resolves to
"
```

Read the output. **Done: 130 glyphs on 214 structured rows, 60% of them,
across 47 sections.**

The spec first said 270, and that was the spec being wrong rather than the
matcher. 270 counts how often concepts *occur*; only one glyph renders per
row, so a row naming three concepts draws one. The spec now carries the real
figure.

One thing this surfaced: `build_index` needs the occurrence counts passed in,
or every tie inside a category breaks alphabetically instead of toward the
rarer concept. Without them "Tails, Still Asleep" draws the Asleep glyph;
with them it draws TAILS, which is what the row is about. Task 4 must compute
and pass them.

- [x] **Step 4: PR**

Title: `feat(pipeline): resolve a glyph for a structured row`.

---

### Task 4: Annotate at build time

**Files:**
- Modify: `pipeline/src/rulecheck_pipeline/build.py`
- Modify: `pipeline/tests/test_build.py`

**Interfaces:**
- Produces: `state_glyphs`, `effect_glyphs`, `branch_glyphs` and
  `step_glyphs` inside `sections.structure`. Task 5 decodes them.

- [x] **Step 1: Write the failing tests**

- Each glyph array has exactly the same length as the field it annotates.
- A row resolving to no glyph gets `null` in the array, not a gap, so the
  arrays stay aligned.
- An entry with none of the four fields gets no glyph arrays at all.
- `rewrites/*.json` is never modified. Annotation happens on the way into the
  database and nowhere else.
- Rebuilding is idempotent: building twice produces byte-identical JSON.

- [x] **Step 2: Implement until they pass**

- [x] **Step 3: Verify against the real build**

```bash
just all
sqlite3 build/rulecheck.db "select json_extract(structure,'\$.state_glyphs') from sections where id='tcg-Asleep';"
git status --short          # rewrites/ must be untouched
```

- [x] **Step 4: PR**

Title: `feat(pipeline): write glyph annotations into the built database`.

---

### Task 5: Render in the app

**Files:**
- Modify: `app/RuleCheck/Data/RuleStructure.swift`
- Modify: `app/RuleCheck/Reader/StructuredRuleView.swift`
- Create: `app/RuleCheck/Design/Glyph.swift`
- Modify: `app/RuleCheckTests/` (a test file for glyph decoding and fallback)

**Interfaces:**
- Consumes: the glyph arrays from Task 4.

- [x] **Step 1: Write the failing tests**

- A section with no glyph arrays renders as it does today.
- A glyph array shorter or longer than its field is ignored rather than
  crashing. This is the one that protects against a pipeline bug reaching a
  player.
- An unknown glyph name renders no glyph.
- A chip whose tint names no `Palette` case falls back to the accent colour.

- [x] **Step 2: Add `Glyph.swift`**

A small view taking a glyph name and drawing either an SF Symbol or a chip.
Chips are a capsule with the tint, text in caps, sized against the existing
type ramp. Every glyph carries an accessibility label, since a glyph that
replaces a word must still be readable aloud.

- [x] **Step 3: Wire it into `StructuredRuleView`**

The layout does not change. Each state line already draws a `Label` whose
icon is a small accent circle at
[StructuredRuleView.swift:35](app/RuleCheck/Reader/StructuredRuleView.swift:35);
the circle becomes the glyph. Effects rows, branch options and steps take the
same treatment.

- [x] **Step 4: Delete `blocked()`**

[StructuredRuleView.swift:104](app/RuleCheck/Reader/StructuredRuleView.swift:104)
decides what turns red by searching for "blocked", "cannot" and "no ". The
`blocked` glyph and its triggers replace it. If anything still needs to
render red, drive it from the glyph, not from a string search.

- [x] **Step 5: Verify**

```bash
just app-test
```

Both persona acceptance tests must still pass against the real database.

- [x] **Step 6: PR**

Title: `feat(app): draw a glyph on each structured row`.

---

### Task 6: Put it on a screen and stop

**Files:** none. This is a review gate, not a change.

- [x] **Step 1: Build to the simulator and capture the rules a player hits**

```bash
just app-db
```

Then build and launch in the simulator, and screenshot at least: Asleep,
Confused, Paralyzed, Poisoned, Burned, the attacking procedure, and one
Appendix entry with sparse structure.

- [x] **Step 2: Send the screenshots to Pete and wait**

The questions to put to him, which are the reason this phase exists:

- Is the density right, or does the page look busy?
- Does the priority rule pick the concept each row is actually about?
- Do the held-out four look like the right call now that it is visible?
- Which placeholder symbols read wrong, and for each one, does it need a real
  icon or is a chip clearer? The chip is always available, so no concept has
  to wait on sourcing.
- Are there too many chips? If the page reads as text badges, some need to
  become symbols instead.

- [x] **Step 3: Do not proceed past this point without an answer**

The next work is replacing placeholder symbols, and it depends entirely on
what he says. At most seven are expected to need a real icon, and fewer if
chips read well: Bench, Prize card, damage counter, Knock Out, Energy,
discard pile and face down. Everything else is either a system symbol that
works or a chip.

---

## Out of scope, recorded so it is not drifted into

- Search results, browse list, and a condition quick-reference screen.
- Rule diagrams for the top rules. Sequenced after this ships.
- The tournament rules and penalty guidelines.
- Energy type symbols, which carry their own licensing question.


---

## What actually happened

Worth recording, since three of these were only found by running the thing
rather than by reading it.

**The spec's 270 was wrong.** It counted how often concepts occur; only one
glyph renders per row. The real figure is 130 glyphs on 214 structured rows,
60% of them, across 47 of 62 sections.

**The density warning in Task 2 was dropped.** The corpus does not support a
threshold: "deck" is written 107 times and keeps its glyph while "attack" is
written 117 and does not. Any cut-off fires on the wrong terms often enough
to be ignored.

**Ties broke alphabetically until the counts were passed.** Without occurrence
counts the row "Tails, Still Asleep" drew the Asleep glyph, because "asleep"
sorts before "tails".

**Effects were annotated in file order while the app renders them sorted.**
Every glyph would have landed on the wrong row for any entry whose effects
were not already alphabetical.

**The first build printed "HEA… Heads".** A truncated chip duplicating the
word beside it. A chip whose text is the condition now replaces that text.

Four validator catches during Task 2 are recorded in that PR: two derivational
variants, a multi-word variant the validator could not handle, an unextractable
term, and two trigger phrases that were invented rather than observed.
