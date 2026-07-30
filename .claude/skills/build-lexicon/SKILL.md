---
name: build-lexicon
description: Use when classifying the game's vocabulary into entities, actions, states, modifiers and phases, or when re-deriving the lexicon after a source document changes. Covers the extract, classify, validate loop and the rules for what counts as one term.
---

# Building the lexicon

The lexicon is the game's vocabulary, classified. It backs the icon set, search
synonyms and eventually a knowledge graph.

**The methodology is the asset, not the file.** TPCi revises documents and our
parsing changes, so the lexicon has to be re-derivable from whatever the corpus
is at the time. Never hand-edit it into a state you could not reproduce.

## The loop

    just lexicon-candidates      # deterministic, no judgement
    ...classify the delta...     # judgement, this skill
    just check-lexicon           # deterministic, independent

**Extract** produces candidate terms from the authored corpus, grouping
inflections and counting occurrences. Same input, same output, always. No
judgement lives here.

**Classify** is your job. Only the delta needs attention: terms the extractor
found that are neither classified nor declined.

**Validate** checks the result against the corpus independently. It is the
buddy script, and it does not trust you.

After a source revision, re-run extract, classify what is new, and let validate
confirm nothing that vanished is still claimed. You do not start over.

## What counts as one term

Inflections are one term. Derived words are not.

    evolve, evolves, evolved, evolving   one term, an action
    evolution, evolutions                a different term, an entity
    attack, attacks, attacked            one term, an action
    attacker, attackers                  a different term, an entity
    attach, attaching                    an action
    attachment, attachments              a different term, an entity

The rule is what the word denotes. Tense and number do not change it, so those
group. A suffix that turns an action into a thing or a person creates a new
term that needs its own entry. `stem()` enforces this and validate rejects a
variant that does not share its term's stem.

## Categories

**entity** A thing the game is made of. Card types, card variants, zones,
markers, attributes. Basic Pokemon, Stadium, discard pile, damage counter,
Weakness.

**action** Something a player or the game does. play, attack, evolve, draw,
discard, attach, shuffle, flip, retreat, rotate.

**state** A condition applied to a Pokemon and later removed, rather than
played. Asleep, Burned, Confused, Paralyzed, Poisoned, Knocked Out.

**modifier** Qualifies an action or a quantity and is meaningless alone.
clockwise, counterclockwise, up to X, any number, per turn.

Modifiers are load-bearing rather than decoration. `rotate + counterclockwise`
is Asleep and `rotate + clockwise` is Paralyzed, so dropping the modifier makes
two of the five special conditions indistinguishable.

**phase** A point in the game loop. turn, Pokemon Checkup, mulligan, setup.

If a term genuinely fits none of these, that is a finding worth reporting
rather than forcing. Categories may need to grow.

## Entry shape

```json
{
  "term": "evolve",
  "category": "action",
  "gloss": "Place an Evolution card onto the Pokemon named on it.",
  "variants": ["evolves", "evolved", "evolving"],
  "sections": ["tcg-Evolution"]
}
```

The gloss is your own words. It is not a quotation, and the paraphrase tripwire
applies here as it does everywhere else.

## Declining a term

Ordinary English is not domain vocabulary. Decline it rather than forcing a
category, and give a reason, the same way the skiplist does:

```json
{"term": "appropriate", "reason": "ordinary English, not a game term"}
```

Declining is a real answer. A lexicon that classifies everything is wrong.

## Rules

- **Never invent a term.** Validate checks every entry occurs in the corpus,
  and an invented one fails. If a term you expect is missing, that is a finding
  about the corpus, not a licence to add it.
- **Never declare a variant you have not seen.** Validate checks each one.
- **Do not widen the stemmer to make a grouping work.** If two words should
  group and do not, say so. Changing `stem()` changes every grouping at once.
- **Coverage is a number, not a feeling.** Validate reports the percentage of
  non-stopword occurrences classified. Quote it.
- **Work in batches and re-run validate between them.** A batch that drops
  coverage or adds failures is easier to unpick when it is small.
