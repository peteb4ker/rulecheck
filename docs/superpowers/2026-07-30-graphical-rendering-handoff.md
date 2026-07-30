# Rule Check, graphical rendering hand-off

For a design-focused Claude session. Read this, then CLAUDE.md, then the
[design spec](specs/2026-07-26-rulecheck-design.md) and the
[Solar/Lunar spec](specs/2026-07-27-solar-lunar-implementation-design.md).
This document does not repeat those. It adds the graphical brief, the data
that constrains it, and the boundaries.

We want a **spec** back, not code.

## The shift

Rule Check shipped as a text app. Search returns sections, sections render as
structured text: state lists, effect tables, branch cards, numbered steps.
That works and it is live on the App Store.

The owner's direction is that this app is used **by players while they are
playing**, so it should be as graphical as it can be. "Rotated clockwise"
should be an icon. "No attacking" should be an icon. Coin flip, Asleep and
Poisoned should be icons. Whole rule pages should be composable as icons plus
short text plus graphical sections, potentially with flow charts, or with the
play area drawn at different stages of a turn.

Players come first. The professor experience is considered good enough as it
is, so do not spend the budget there.

## What the data will and will not support

This is measured from the 62 authored sections of the game rules document, not
estimated. Please design against it rather than around it.

**Only 32% of sections carry anything iconifiable.** 20 of 62 have at least one
short label-and-outcome pair. The other 42 are prose-shaped, with content like
"Not part of the name, shares its name with the non-Delta version". Those will
not become glyphs and a design that assumes otherwise will not survive contact
with the corpus.

**The density is concentrated exactly where players look.** The five special
conditions hold 21 of the iconifiable elements between them:

```
tcg-Asleep      8    state x3, effects x3, branch
tcg-Paralyzed   6    state x3, effects x3
tcg-Confused    4    state x1, effects x2, branch
tcg-Burned      3    state x2, branch
tcg-Poisoned         state x2, branch
```

**The recurring vocabulary is small.** Across the whole document: Knock Out 11,
Prize cards 11, Heads and Tails 5, Blocked 4, Attack and Retreat 6, No
attacking and No retreating 4. Everything else appears exactly once.

The conclusion we draw, which you are free to challenge: you cannot make most
of the rulebook graphical, but you can make **the most-used part of it almost
entirely graphical**. The special conditions need no re-authoring, only
rendering.

## The data you are rendering

Every section carries an authored JSON structure in one of five archetypes.
The app decodes it in `app/RuleCheck/Data/RuleStructure.swift` and renders it
in `app/RuleCheck/Reader/StructuredRuleView.swift`.

| Archetype | Fields | Count, game rules |
| --- | --- | --- |
| mechanic | summary, state[], branch{when, options[]}, ends_when[], effects{} | 46 |
| procedure | summary, steps[{actor, action, note}] | 7 |
| definition | terms[{term, meaning}] | 6 |
| note | summary, paragraphs[] | 3 |
| penalty | summary, infraction, base_penalty[], handling[] | 0 here, 13 in penalty guidelines |

`Asleep` is the worked example, and is the section to design first:

```json
{
  "archetype": "mechanic",
  "summary": "A sleeping Pokemon is rotated counterclockwise and skips both
              attacking and retreating until a coin flip wakes it.",
  "state": ["Rotated counterclockwise", "No attacking", "No retreating"],
  "branch": {
    "when": "Pokemon Checkup",
    "options": [
      {"condition": "Heads", "outcome": "Wakes up",
       "detail": "Stand the card right-side up."},
      {"condition": "Tails", "outcome": "Still Asleep",
       "detail": "Flip again at the next Checkup."}
    ]
  },
  "effects": {"Abilities": "Still usable", "Attack": "Blocked",
              "Retreat": "Blocked"}
}
```

## Questions we want the spec to answer

1. **What does a fully graphical Asleep page look like?** That is the proof of
   concept. If it works there it works for the other four conditions.
2. **Where does the icon vocabulary live?** A mapping from string to icon in
   the app is simple but silently degrades when an author writes "Blocked."
   with a full stop. Structured icon hints in the pipeline are robust but add
   an authoring burden across 244 entries. We have no strong view.
3. **What happens to a term with no icon?** 68% of sections are prose-shaped,
   so the fallback is the common case, not the edge case.
4. **Do flow charts earn their place?** Only 7 sections are procedures. Be
   honest if the answer is no.
5. **Is a play-area diagram worth it?** Active spot, Bench, Prize cards, Deck,
   Discard, Hand and Lost Zone. Which sections would genuinely use one?
6. **How does this coexist with the professor experience?** The penalty
   guidelines are 13 penalty-archetype sections with tier tables. They should
   not regress.

## Icon inventory

A measured inventory is in `.scratch/icon-inventory.md` in the repo. Summary:
15 icons render every special condition page graphically. Five conditions, then
Blocked, Coin flip, Heads, Tails, Knock Out, Prize card, Allowed, Damage
counter, Attack, Retreat. A further 22 covers board zones and the eleven energy
types.

Icons are being sourced externally. Assume single-colour glyphs that take the
palette tokens, so dark mode works without a second asset. Assume solid shapes
over thin lines, since these render around 44 points.

## Boundaries

**Zero network calls, ever.** Not a default, a shipped promise, verified by a
privacy manifest declaring no data collection. Every asset ships in the bundle.
The app is currently 3.8 MB and that is a feature.

**No Pokemon character or species names** anywhere user-facing. The game's name
is fine and is used throughout. Pikachu is not.

**Visual language is available, text is not.** The repository contains no
verbatim rules text and a 12-token overlap tripwire enforces that. But card
imagery is normal in this category: Dex, Collectr, HoloDex and others have
shipped card scans for years without issue. So energy symbols, damage counters,
card silhouettes and play-area layouts are all fair game. Do not source
fan-made icon packs that state no licence, since silence defaults to all rights
reserved.

**Solar and Lunar palette**, already implemented in
`app/RuleCheck/Design/Palette.swift`. Do not introduce new colour systems.

**iOS 17 minimum**, SwiftUI, GRDB as the only dependency.

**iPad is currently a stretched iPhone layout.** Universal build, and the iPad
screenshots show full-width rows with a lot of empty space on a 13 inch screen.
If the graphical direction suggests an answer there, say so.

## Non-goals

Deck building, collection tracking, card database, rulings compendium, card
legality. All explicitly out of scope. This is a rules reference.
