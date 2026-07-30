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
