"""The game's vocabulary: entities, actions, states, modifiers and phases.

Two jobs. Group the inflections of one term so "evolve", "evolves", "evolved"
and "evolving" count as the same thing. Keep apart the words that merely look
related, because in this domain they are genuinely different: "attack" is an
action and "attacker" is an entity; "attach" is an action and "attachment" is
the thing attached; "play" is an action and "player" is a person.

That distinction is the whole design. Inflectional suffixes are stripped, since
they mark tense and number and do not change what a word denotes. Derivational
suffixes are left alone, since they build a new word with a new meaning, which
needs its own lexicon entry.

Stemming here is not a general English stemmer and does not try to be. It needs
to be right on this corpus and to surface candidates a reviewer confirms, so a
false grouping is cheap and a missed one is the expensive case.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CATEGORIES = {"entity", "action", "state", "modifier", "phase"}

# The third glyph state. A concept nobody has judged yet still renders, as a
# chip of its own name, so the set can ship and be looked at before anyone
# decides which ones deserve a drawn symbol.
UNDECIDED = "undecided"

# Marks tense or number. Stripping these does not change what a word denotes.
INFLECTIONAL = ("ing", "ed", "es", "s")

# Builds a new word with a new meaning. Never stripped, because "attacker" is
# not "attack" and treating it as one would merge an entity into an action.
DERIVATIONAL = ("er", "ers", "ment", "ments", "ion", "ions", "able", "ability",
                "ance", "ence", "ness", "ist", "ive")

_VOWELS = set("aeiou")


def stem(word: str) -> str:
    """Reduce a word to the form its inflections share.

    evolve, evolves, evolved, evolving  -> evolv
    flip, flipped, flipping             -> flip
    attack, attacks, attacked           -> attack
    attacker, attackers                 -> attacker   (a different word)
    counter, counters                   -> counter    (a noun, not a verb)
    """
    w = word.lower()

    # Normalise a plural before deciding whether the word is derivational, so
    # "counters" and "attackers" reach their singular first. Otherwise the
    # plural of a derived noun looks like a different word from its singular.
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]

    if any(w.endswith(d) and len(w) - len(d) >= 3 for d in DERIVATIONAL):
        return w

    verbal = False
    changed = True
    while changed:
        changed = False
        for suffix in INFLECTIONAL:
            if not w.endswith(suffix) or len(w) - len(suffix) < 3:
                continue
            if suffix == "s" and w.endswith("ss"):
                continue
            w = w[: -len(suffix)]
            verbal = verbal or suffix in ("ing", "ed")
            changed = True
            break

    # flipp -> flip. Only after stripping ing or ed, so "class" keeps both s.
    if verbal and len(w) > 3 and w[-1] == w[-2] and w[-1] not in _VOWELS:
        w = w[:-1]
    # evolve -> evolv, rotate -> rotat, so every inflection lands on one form
    if len(w) > 3 and w.endswith("e"):
        w = w[:-1]
    # penalti -> penalty, abiliti -> ability. English pluralises a final "y"
    # as "ies", so stripping the plural leaves an "i". This must run last:
    # "penalties" only reaches "penalti" after the trailing "e" comes off.
    if len(w) > 2 and w.endswith("i"):
        w = w[:-1] + "y"
    return w


def categories_of(entry: dict) -> list[str]:
    """A term's categories, as a list however it was written.

    Some words are genuinely two things. "attack" is a thing printed on a card
    about 25 times in the game rules and something a player does about 8 times.
    Forcing one category would make a parallel classifier pick arbitrarily, and
    two batches would disagree with nothing to catch it.
    """
    value = entry.get("category")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []


def same_term(a: str, b: str) -> bool:
    """True when two words are inflections of one another."""
    return stem(a) == stem(b)


def load(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())["terms"]


def validate(terms: list[dict]) -> list[str]:
    """Schema errors only. Corpus agreement is the buddy script's job."""
    errors: list[str] = []
    seen: dict[str, str] = {}
    for entry in terms:
        term = entry.get("term")
        if not term:
            errors.append("entry with no term")
            continue
        cats = categories_of(entry)
        if not cats:
            errors.append(f"{term}: needs a category")
        for cat in cats:
            if cat not in CATEGORIES:
                errors.append(
                    f"{term}: category {cat!r} must be one of {sorted(CATEGORIES)}")
        if len(cats) != len(set(cats)):
            errors.append(f"{term}: repeats a category")
        if not entry.get("gloss", "").strip():
            errors.append(f"{term}: needs a gloss saying what it means")

        key = stem(term)
        if key in seen and seen[key] != term:
            errors.append(
                f"{term}: shares a stem with {seen[key]!r}. If they are the same "
                f"term make one a variant of the other; if they are genuinely "
                f"different words, say so in the gloss"
            )
        seen[key] = term

        for variant in entry.get("variants", []):
            if not same_term(variant, term):
                errors.append(
                    f"{term}: variant {variant!r} does not share its stem "
                    f"({stem(variant)} vs {stem(term)}), so it is a different word"
                )

        errors.extend(_glyph_errors(term, entry))
    return errors


def _glyph_errors(term: str, entry: dict) -> list[str]:
    """Whether this concept renders an icon, and how.

    The decision is a boolean so that holding a concept back is a recorded
    judgement rather than an absence someone later mistakes for an oversight.
    "attack" renders 49 times across 18 sections, which is too often for a
    glyph to mean anything, and the next person to read the lexicon should be
    able to see that was considered.
    """
    errors: list[str] = []
    has_key = "glyph" in entry
    glyph = entry.get("glyph")
    render = entry.get("glyph_render")
    triggers = entry.get("glyph_triggers")

    if not has_key:
        if render is not None:
            errors.append(
                f"{term}: has glyph_render but no glyph — without the decision the "
                f"matcher never picks it up, so the rendering would go unused")
        if triggers is not None:
            errors.append(
                f"{term}: has glyph_triggers but no glyph — nothing for them to render")
        return errors

    if not (isinstance(glyph, bool) or glyph == UNDECIDED):
        errors.append(
            f"{term}: glyph must be true, false or {UNDECIDED!r}, not {glyph!r}")
        return errors

    if glyph == UNDECIDED:
        # Nothing else is required. The chip text comes from the term and the
        # tint from its meaning, which is the whole point of this state: a
        # concept is visible and readable before anyone has judged it, and
        # becoming a symbol later is a data change rather than a gap to fill
        # before anything can ship.
        if render is not None:
            if "symbol" in render:
                errors.append(
                    f"{term}: glyph is {UNDECIDED!r} but glyph_render names a symbol. "
                    f"Choosing a symbol is the decision — set glyph to true")
            else:
                errors.extend(_render_errors(term, render))
    elif glyph:
        if render is None:
            errors.append(f"{term}: glyph is true, so it needs a glyph_render")
        else:
            errors.extend(_render_errors(term, render))
    else:
        if not str(entry.get("glyph_note", "")).strip():
            errors.append(
                f"{term}: glyph is false, so it needs a glyph_note saying why. "
                f"A bare false reads as an oversight rather than a decision")
        if render is not None:
            errors.append(f"{term}: glyph is false, so glyph_render is unused")
        if triggers is not None:
            errors.append(
                f"{term}: glyph is false, so it cannot carry glyph_triggers — "
                f"there is no glyph for them to render")

    if triggers is not None:
        if not isinstance(triggers, list):
            errors.append(f"{term}: glyph_triggers must be a list")
        elif not all(isinstance(t, str) and t.strip() for t in triggers):
            errors.append(
                f"{term}: glyph_triggers must all be non-empty strings")
    return errors


def _render_errors(term: str, render: dict) -> list[str]:
    """A glyph is a symbol or a chip, never both and never neither.

    The chip is the backstop. Where no picture states a concept clearly the
    word does, which is why "Ability" renders as a chip: the cards print it
    that way and a player reads the word faster than any symbol for it.
    """
    if not isinstance(render, dict):
        return [f"{term}: glyph_render must be an object"]

    has_symbol = "symbol" in render
    has_chip = "chip" in render
    if has_symbol == has_chip:
        return [
            f"{term}: glyph_render must be either a symbol or a chip, not "
            f"{'both' if has_symbol else 'neither'}"
        ]

    errors: list[str] = []
    if has_symbol:
        if not str(render.get("symbol", "")).strip():
            errors.append(f"{term}: symbol needs a name")
    else:
        if not str(render.get("chip", "")).strip():
            errors.append(f"{term}: chip needs text to show")
        if not str(render.get("tint", "")).strip():
            errors.append(
                f"{term}: chip needs a tint naming a Palette case, so it "
                f"follows the design tokens and works in dark mode")
    return errors


def tokenize(text: str) -> list[str]:
    """Words, with possessives and "(s)" folded away.

    Without this "a card's name" yields a stray "s" and "(s)" plurals add
    another, which together produced the third most frequent candidate in the
    real corpus while meaning nothing.
    """
    text = re.sub(r"\(s\)", "s", text)
    text = re.sub(r"(['\u2019])s\b", "", text)
    return [w for w in re.findall(r"[A-Za-zÀ-ÿ]+", text) if len(w) > 1]


# Edges only. A phrase may contain these ("up to X") but starting or ending on
# one means the n-gram was cut mid-sentence rather than being a real term.
_EDGE_STOP = frozenset("""
a an the and or but if when then than that this these those it its is are was were be
been being do does did have has had can cannot could may might must will would to of in
on at by for with from into onto over under about as so such no not only both each any
all every other another same own more most less few many much you your they them their
there here what which who how why where while during before after until since between
through against above below up down out off again once per via
""".split())


def segments(text: str) -> list[list[str]]:
    """Word runs that punctuation does not interrupt.

    A phrase cannot span a comma or a full stop. Tokenizing the whole string
    first merges "round(s), single elimination" into "rounds single", which is
    not a term anyone uses and which dominated the first n-gram run.
    """
    return [tokenize(part) for part in re.split(r"[.,;:!?()\[\]/\u2014\u2013]", text)]


def stem_phrase(phrase: str) -> str:
    """Stem every word, so "damage counters" and "damage counter" agree."""
    return " ".join(stem(w) for w in tokenize(phrase))


def extract(texts: list[str], min_count: int = 1, max_words: int = 1) -> list[dict]:
    """Candidate terms from any corpus, deterministically.

    This is the half that has to survive TPCi revising a document and us
    changing how we parse it. Given text in, the same candidates come out
    every time, so re-running after a revision produces a diff to classify
    rather than a job to redo. Judgement lives in the classification step; no
    judgement lives here.

    Each candidate carries the surface forms it was built from, so a reviewer
    can see that "evolve" stands for evolve, evolves, evolved and evolving
    without going back to the text.
    """
    counts: dict[str, int] = {}
    forms: dict[str, dict[str, int]] = {}
    for text in texts:
      for segment in segments(text):
        words = [w.lower() for w in segment]
        for n in range(1, max_words + 1):
            for i in range(len(words) - n + 1):
                gram = words[i:i + n]
                # Multi-word terms must not begin or end on a function word.
                if n > 1 and (gram[0] in _EDGE_STOP or gram[-1] in _EDGE_STOP):
                    continue
                surface = " ".join(gram)
                key = " ".join(stem(w) for w in gram)
                counts[key] = counts.get(key, 0) + 1
                forms.setdefault(key, {})
                forms[key][surface] = forms[key].get(surface, 0) + 1

    candidates = []
    for key, total in counts.items():
        if total < min_count:
            continue
        surface = sorted(forms[key].items(), key=lambda kv: (-kv[1], kv[0]))
        candidates.append({
            "stem": key,
            "words": len(key.split()),
            "count": total,
            # The most frequent spelling is the one a reader recognises.
            "lemma": surface[0][0],
            "forms": [w for w, _ in surface],
        })
    return sorted(candidates, key=lambda c: (-c["count"], c["stem"]))


# Where the game's concepts actually live. A term in one of these places is
# load-bearing by construction: a rule turns on it, or the document thought it
# deserved its own section. Frequency cannot see this. "Asleep" is written 9
# times and "competitor" 462, and only one of them is a concept the game is
# built from.
STRUCTURAL_SOURCES = (
    ("section title", 5),   # the document's own table of contents
    ("defined term", 5),    # a definition archetype names it explicitly
    ("effect row", 4),      # a rule's outcome table turns on it
    ("branch", 4),          # a rule forks on it
    ("state", 3),           # a condition while something is in effect
    ("penalty tier", 3),
    ("actor", 2),           # who performs a step
)


def structural_candidates(sections: list[dict], entries: dict) -> list[dict]:
    """Concepts drawn from structure rather than prose frequency.

    `sections` are index rows (id, title). `entries` are rewrite entries by id.

    Returns each concept with the places it came from and a weight, so a term
    naming a whole section outranks one mentioned in a single effects row. No
    occurrence floor: "mulligan" is written 4 times and is still a rule of the
    game, which a frequency cut can never express.
    """
    found: dict[str, dict] = {}

    def add(text: str, source: str, weight: int, where: str):
        text = (text or "").strip()
        # Structured fields hold phrases; a long one is prose describing a
        # concept rather than naming it. Section titles get more room, because
        # the rulebook writes headings like "Full details of taking a
        # mulligan" and the concept is buried inside. The classifier names the
        # concept; extraction only has to surface the section.
        cap = 9 if source == "section title" else 4
        if not text or len(text.split()) > cap:
            return
        key = stem_phrase(text)
        if not key:
            return
        rec = found.setdefault(key, {"term": text, "weight": 0,
                                     "sources": set(), "sections": set()})
        rec["weight"] += weight
        rec["sources"].add(source)
        rec["sections"].add(where)
        # Prefer the shortest surface form as the canonical name.
        if len(text) < len(rec["term"]):
            rec["term"] = text

    for row in sections:
        sid, title = row.get("id", ""), row.get("title", "")
        add(title, "section title", 5, sid)

    for sid, entry in entries.items():
        if "skip" in entry:
            continue
        for t in entry.get("terms", []) or []:
            add(t.get("term", ""), "defined term", 5, sid)
        for key in (entry.get("effects") or {}):
            add(key, "effect row", 4, sid)
        for value in (entry.get("effects") or {}).values():
            add(value, "effect row", 4, sid)
        branch = entry.get("branch") or {}
        add(branch.get("when", ""), "branch", 4, sid)
        for opt in branch.get("options", []) or []:
            add(opt.get("condition", ""), "branch", 4, sid)
            add(opt.get("outcome", ""), "branch", 4, sid)
        for line in entry.get("state") or []:
            add(line, "state", 3, sid)
        for row in entry.get("base_penalty") or []:
            add(row.get("tier", ""), "penalty tier", 3, sid)
        for step in entry.get("steps") or []:
            add(step.get("actor", ""), "actor", 2, sid)

    out = []
    for key, rec in found.items():
        out.append({"stem": key, "term": rec["term"], "weight": rec["weight"],
                    "sources": sorted(rec["sources"]),
                    "sections": sorted(rec["sections"])[:3]})
    return sorted(out, key=lambda c: (-c["weight"], c["term"]))
