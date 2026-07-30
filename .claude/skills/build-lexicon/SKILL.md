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

## Words that are two things at once

Some terms are genuinely more than one category. In the game rules "attack" is
a thing printed on a card about 25 times and something a player does about 8
times. "retreat" and "damage" behave the same way.

Give the term every category that applies:

```json
{
  "term": "attack",
  "category": ["entity", "action"],
  "gloss": "A printed attack on a Pokemon card, and the act of using one."
}
```

Do not pick one and move on. A single category forces an arbitrary choice, and
two people classifying different batches will choose differently with nothing
to catch it. If a term looks like two categories, it usually is.

## Multi-word terms

`just lexicon-candidates` proposes phrases as well as single words, marked `2w`
or `3w`. Many of the most important entities are phrases: damage counter,
Special Condition, Pokemon Checkup, Prize card, Retreat Cost, Basic Pokemon.

Classify the phrase as its own term when it means something its parts do not.
"damage counter" is a specific marker, not any counter that happens to be
about damage.

The words inside a classified phrase still need their own decision. "damage"
appears on its own as well, so classifying "damage counter" does not settle it.

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

`category` is one value or a list. `variants` are spellings you have actually
seen; validate rejects any that do not share the term's stem, and any that
never occur. `sections` are section ids where the term is defined or used
most clearly, and are optional; they exist so a future reader can find the
rule behind the word.

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
- **One file per batch, under `content/lexicon/`.** Batches are assigned by
  frequency band and are disjoint, so two people never edit one file. Name the
  file after the band.
- **Stay inside your band.** A term outside it belongs to someone else, and
  classifying it twice produces a duplicate that only surfaces at merge.
