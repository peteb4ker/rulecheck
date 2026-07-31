# Glyph rendering for players

**Date:** 2026-07-31
**Status:** Approved by Pete (brainstorming session)
**Issue:** supersedes the hand-off in PR #24, whose 15-glyph inventory was guesswork

## What this is

RuleCheck is primarily for players while they are playing. Today a player who
searches "asleep" gets a well-structured page of text. This adds a layer of
glyphs to the structured rows so the shape of a rule is visible before a word
is read.

Phase one covers the game rules document only, which is the player document.
That is 62 shipped entries; the other two sections are index pages that ship
nothing.
Judges come later. Rule diagrams come later still.

## Scope

In scope:

- A `glyph` decision recorded per lexicon term.
- Build-time matching of glyph-bearing concepts inside structured field
  values, never in free prose.
- One glyph per structured row, chosen by a deterministic priority rule.
- Rendering in the existing reader layout, which does not change.
- SF Symbols as placeholders throughout, so the whole path can be judged on
  a real device before any icon is sourced.

Out of scope:

- Search results, the browse list, and a condition quick-reference screen.
  Pete chose the rule body alone.
- Rule diagrams. Sequenced after this ships.
- The tournament rules and penalty guidelines.
- Energy type symbols, which carry a separate licensing question.

## The concepts

29 concepts, derived by counting how often each would render inside the
structured fields of the 62 shipped game-rules entries. The counts are evidence, not
estimates, and they come from matching with the lexicon stemmer so
inflections group.

The **Grouping** column below is for reading this table. The lexicon's own
five categories are `entity`, `action`, `state`, `modifier` and `phase`, and
the priority rule uses those. Assigning a category to each concept is part of
the classification work, not a decision this spec makes. Four of them need
thought and are called out under Open questions.

| Grouping | Concept | Renders | Sections |
|---|---|---|---|
| Special Condition | Burned | 8 | 3 |
| Special Condition | Poisoned | 6 | 3 |
| Special Condition | Asleep | 5 | 3 |
| Special Condition | Paralyzed | 5 | 2 |
| Special Condition | Confused | 4 | 3 |
| Action | Knock Out | 13 | 13 |
| Action | draw | 13 | 8 |
| Action | retreat | 11 | 8 |
| Action | discard | 10 | 7 |
| Action | flip | 8 | 7 |
| Action | place | 8 | 4 |
| Action | attach | 7 | 6 |
| Action | remove | 5 | 4 |
| Action | search | 4 | 3 |
| Zone or object | deck | 28 | 19 |
| Zone or object | Bench | 21 | 12 |
| Zone or object | Prize card | 18 | 17 |
| Zone or object | Ability | 18 | 10 |
| Zone or object | Energy | 13 | 7 |
| Zone or object | damage counter | 10 | 5 |
| Zone or object | hand | 8 | 5 |
| Zone or object | Trainer card | 8 | 8 |
| Zone or object | discard pile | 6 | 4 |
| Zone or object | Stadium | 5 | 3 |
| Outcome | blocked | 12 | 7 |
| Outcome | allowed | 5 | 5 |
| Outcome | Heads | 3 | 3 |
| Outcome | Tails | 3 | 3 |
| Modifier | face down | 5 | 3 |

The Renders column counts how often each concept *occurs* in structured
text, which is what made the case for including it. It is not the number of
glyphs drawn. Only one glyph renders per row, so a row naming three concepts
still draws one.

Measured against the built matcher: **130 glyphs on 214 structured rows, 60%
of them, across 47 of the 62 shipped sections.** That is the number to judge
this by.

### Deliberately held out

Three concepts are classified and carry no glyph:

| Concept | Renders | Reason |
|---|---|---|
| attack | 49 | Too common to carry meaning as a glyph |
| play | 34 | Too common to carry meaning as a glyph |
| evolve | 31 | Too common to carry meaning as a glyph |

"Pokemon" is also held out, at 107 renders across 34 sections. It is the most
common noun in a Pokémon rulebook, so a glyph on it would appear almost
everywhere and would make every other glyph harder to notice.

These decisions are recorded rather than implied, so the next person to read
the lexicon can see they were considered and disagree with them.

### Too rare to source

Seven concepts appear once or twice and are excluded for now: shuffle, face
up, heal, reveal, Active Spot, clockwise, counterclockwise. The rotation pair
is worth taking if good icons turn up, since the idea is visual by nature and
hard to state in words, but it does not justify sourcing on its own.

## Data model

A `glyph` field on each lexicon term with three values, and the rendering
held separately. Absent means the concept has not been considered, so
classifying a new term never silently creates a sourcing obligation.

| Value | Meaning | Renders |
|---|---|---|
| `true` | Decided. This concept carries a glyph. | Whatever `glyph_render` says |
| `false` | Decided. This concept carries no glyph. | Nothing |
| `"undecided"` | Not yet decided. | A chip of the term's own name |

The third value is what lets the whole set ship before anyone has judged it.
A concept marked `undecided` renders a chip derived from its term, so it is
visible and readable on day one, and becoming a symbol later is a data
change rather than a gap to be filled first.

An undecided chip is deliberately indistinguishable from a decided one. The
point of the review gate is to judge how the page reads, and marking the
provisional ones would tell the reader what to think. Which concepts are
still open is recorded in the lexicon, where a decision belongs, not in the
rendering.

```json
{
  "term": "Asleep",
  "category": "state",
  "gloss": "A Special Condition. The Pokémon is turned sideways and cannot attack or retreat.",
  "variants": ["asleep"],
  "glyph": true,
  "glyph_render": { "symbol": "moon.zzz" }
}
```

A glyph is either a symbol or a text chip.

**The chip is the general backstop, not a special case for one concept.** Any
concept where no picture reads unambiguously renders its word instead. This
matters more than it first appears: it means no concept is ever blocked on
finding a good icon, and it removes the pressure to accept a weak symbol just
to fill a slot.

Two rules of thumb for choosing. Use a chip when the word is itself what a
player recognises, which is why Ability, Heads and Tails are chips: cards
print ABILITY as a banner, and a coin call is a word before it is a picture.
Use a symbol when a picture is faster to parse than reading. The failure mode
to avoid is chipping everything, which turns the page back into text and
undoes the point of the exercise.

`tint` names a `Palette` case rather than a colour, so chips follow the
existing design tokens and light and dark mode come free:

```json
{
  "term": "Ability",
  "category": "entity",
  "glyph": true,
  "glyph_render": { "chip": "ABILITY", "tint": "negative" }
}
```

An undecided concept needs nothing else. The chip text is its term in caps
and the tint follows the rules below:

```json
{
  "term": "damage counter",
  "category": "entity",
  "glyph": "undecided"
}
```

A held-out concept records why:

```json
{
  "term": "attack",
  "category": ["entity", "action"],
  "glyph": false,
  "glyph_note": "Renders 49 times across 18 sections. Too common to carry meaning."
}
```

## Chip colour

Low-risk and revisable. This is a first cut to be judged on screen at the
review gate, not a settled system.

A chip is drawn from a single `Palette` token: the background is that token
at low opacity and the text is the token at full strength. One token gives
both, so light and dark come free from the existing Solar and Lunar sets and
no chip needs a colour pair maintained by hand.

Colour carries meaning, and the meaning is what the concept does to the
player rather than which lexicon category it sits in. Colours are shared
across concepts on purpose. A player should learn four colours, not thirty.

| Tint | Means | Concepts |
|---|---|---|
| `negative` | Stops, blocks or harms you | Asleep, Burned, Confused, Paralyzed, Poisoned, blocked, Knock Out |
| `positive` | Permits or restores | allowed |
| `accent` | Something you do, or its outcome | draw, discard, retreat, flip, place, attach, remove, search, Heads, Tails |
| `secondary` | A thing or a place | deck, Bench, Prize card, Energy, damage counter, hand, Trainer card, discard pile, Stadium, face down |

`positive` is a new token and the only addition. It exists because `blocked`
and `allowed` are the pair where a colour contrast does the most work, and
reading one against the other should not require reading at all.

### When the source overrides the semantics

A concept may override its semantic tint where the source material has an
established colour a player already recognises. Ability is the case that
prompted this rule: it renders `negative`, which is to say red, not because
an Ability is bad but because the cards print ABILITY as a red banner and
that is the thing a player's eye is trained on.

An override is recorded explicitly, so it reads as a decision rather than a
miscategorisation:

```json
{
  "term": "Ability",
  "category": "entity",
  "glyph": true,
  "glyph_render": { "chip": "ABILITY", "tint": "negative" },
  "glyph_note": "Red follows the cards, which print ABILITY as a red banner. Not a semantic negative."
}
```

Overrides should stay rare. If several accumulate, the semantic groups are
wrong and the table above should change instead.

### glyph_triggers

Literal matching handles most rows and not all. "No attacking" contains
neither the word "blocked" nor any other glyph-bearing term, so it would
render nothing, while today the app at least colours it red.

```json
{
  "term": "blocked",
  "category": "modifier",
  "glyph": true,
  "glyph_render": { "symbol": "nosign" },
  "glyph_triggers": ["no attacking", "no retreating", "cannot attack", "cannot retreat"]
}
```

`variants` stays what it is, inflections that the validator holds to a shared
stem. `glyph_triggers` are phrases meaning the concept without naming it, so
they cannot share a stem and get their own rule: each must occur in the
corpus, which `check-lexicon` enforces the way it already catches invented
terms.

This is what lets `blocked()` in `StructuredRuleView.swift` be deleted. That
function currently decides what turns red by searching for the words
"blocked", "cannot" and "no ", which is a guess at meaning.

## Build-time annotation

Matching happens in `build_db`, not in `rewrites/`. Authored files stay
hand-written and glyphs stay derived, so they cannot drift from the lexicon
and a rebuild always regenerates them.

The entry JSON already ships whole in `sections.structure` and is decoded by
Swift, so glyphs ride inside that column and **the database schema does not
change**.

Annotation is parallel arrays aligned to the fields that render as rows:

```json
{
  "state": ["No attacking", "No retreating", "Turned sideways"],
  "state_glyphs": ["blocked", "blocked", "asleep"],
  "branch": { "options": [{ "condition": "Heads" }, { "condition": "Tails" }] },
  "branch_glyphs": ["heads", "tails"]
}
```

The four annotated fields are `state`, `effects`, `branch.options` and
`steps`. Free prose fields, including `summary` and any paragraphs, are never
annotated. Glyphs earn attention by being rare, and a glyph beside every
mention of a common word would make the page harder to read.

### Priority

A value can match several glyph-bearing concepts. One glyph renders per row,
chosen by priority over the lexicon's five categories:

1. `state`
2. `modifier`
3. `entity`
4. `action`
5. `phase`

Ties break toward the rarer concept, measured by total renders across the
corpus, because a rarer term carries more information. A row is about the
state it describes or the qualifier on it; any object or action it mentions
along the way is incidental.

A term carrying two categories, which the lexicon allows and "attack" already
uses, takes the higher priority of the two.

This rule is deterministic and testable. The same entry always produces the
same glyph.

## App rendering

The reader layout does not change. `StructuredRuleView` already draws each
state line as a `Label` whose icon is a small accent circle. The circle
becomes the glyph.

The app decodes the glyph arrays as optional and guards on count. A missing
array, a mismatched length, or an unknown glyph name renders exactly as the
app renders today. Degradation is silent and total: no glyph, no change.

A chip renders as a small capsule with the given tint and the text in caps,
sized to the surrounding type ramp.

## Placeholders first

Phase one uses SF Symbols throughout. They cost nothing, ship with the
device, scale with Dynamic Type and carry accessibility labels already.

The purpose is a feedback loop before any spend on graphics. With the whole
path built, Pete can judge density, placement and whether the priority rule
picks the right concept for each row, on a real device, before a single icon
is sourced.

Two things shrink the sourcing list well below 29. Some SF Symbols will be
good enough to keep, which is a legitimate outcome rather than a compromise,
since they stay visually consistent with the rest of iOS. And any concept
where no symbol reads clearly can render as a chip instead, so nothing is
blocked on finding the right icon.

What is left needing a real icon are the concepts with a look players already
recognise and where a word would be slower to read: Bench, Prize card, damage
counter, Knock Out, Energy, discard pile and face down. At most seven, and
fewer if chips read well. The exact list is decided at the review gate with
the placeholders on screen, not now.

## Testing

Pipeline:

- The stemmer already groups inflections; matching tests assert that
  "evolving" and "evolves" reach the same concept.
- Priority is tested directly: a value matching a state and an object must
  render the state.
- Annotation arrays must align with the field they annotate, tested per
  archetype.
- A `glyph: true` term with no `glyph_render` fails `check-lexicon`.
- A `glyph_trigger` that never occurs in the corpus fails `check-lexicon`,
  the same way an invented term does.
- Held-out terms must carry a `glyph_note`, so a `false` is always a decision
  rather than an oversight.

App:

- A section with no glyph arrays renders as it does today.
- A chip whose `tint` names no `Palette` case falls back to the accent colour.
- A glyph array shorter or longer than its field is ignored rather than
  crashing.
- An unknown glyph name renders no glyph.
- The two persona acceptance tests keep passing against the real database.

## Open questions

Four concepts need a lexicon category assigned:

- **blocked** and **allowed**. Probably `modifier`, since they qualify whether
  something may happen rather than naming a thing or an act.
- **Heads** and **Tails**. Coin outcomes; `state` fits the coin and `entity`
  fits the face. Lower stakes than it looks, because both render as chips and
  the branch conditions they match are the literal words "Heads" and "Tails",
  so a competing match is unlikely. Still worth deciding rather than
  defaulting, since category drives the priority rule.

These get decided during classification, following the build-lexicon skill,
not here.

## Risks

**Glyph noise.** The judgement that attack, play, evolve and Pokemon are too
common is reasoned but unproven until it is on a screen. The placeholder
phase exists to test it, and the boolean makes reversing any of them a data
change.

**Priority picking the wrong concept.** The rule is a guess at what a row is
about. The placeholder build will show where it is wrong, and the fix is
either reordering the categories or holding out a concept.

**Matching inside sentence-shaped values.** State lines are sentences, not
labels, so a line can mention a concept it is not about. Category priority
mitigates this and does not eliminate it.

## Sequence

1. Lexicon: add the boolean, the render and the triggers to the 29 concepts,
   plus notes on the four held out.
2. Pipeline: matching, priority, annotation, tests.
3. App: decoding, glyph and chip rendering, delete `blocked()`.
4. Build to the simulator, screenshot, review.
5. Replace the placeholder symbols that read wrong.
6. Judges and rule diagrams, as separate work.
