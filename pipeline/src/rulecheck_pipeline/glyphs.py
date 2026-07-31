"""Which glyph, if any, a structured row shows.

The lexicon says which concepts carry a glyph. This finds them inside the
short values that already render as their own row in the reader: a state
line, an effects row, a branch option, a step. Free prose is never touched.
Glyphs earn attention by being rare, and one beside every mention of a common
word would make a page harder to read rather than easier.

A row can name several concepts, and only one glyph renders, so the choice
has to be deterministic. Category decides first, because a row is about the
state it describes or the qualifier on it, and any object or action it
mentions along the way is incidental. Within one category the rarer concept
wins, since a rarer term carries more information.
"""

from __future__ import annotations

import unicodedata

from rulecheck_pipeline.lexicon import UNDECIDED, categories_of, stem, tokenize

# A row is about its state, then its qualifier. Objects and actions are what
# the row happens to mention on the way to saying that.
PRIORITY = ("state", "modifier", "entity", "action", "phase")

# The fields that render as their own row. Anything else is prose.
ANNOTATED = ("state", "effects", "branch", "steps")


def fold(text: str) -> str:
    """Drop accents, so "Pokémon" and "Pokemon" are one word.

    Three separate analyses of this corpus have miscounted because of this.
    The shipped matcher does not get to make the same mistake.
    """
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def stems(text: str) -> list[str]:
    return [stem(w) for w in tokenize(fold(text))]


def build_index(terms: list[dict], counts: dict[str, int] | None = None) -> list[dict]:
    """The glyph-bearing concepts, ordered so the first match is the right one.

    Sorted once here rather than compared per row, so matching a row is a
    scan and the ordering rule lives in exactly one place.

    `counts` is how often each term occurs, used only to break ties inside a
    category. Absent, every term ties at zero and the order falls back to the
    term itself, which keeps the result deterministic either way.
    """
    counts = counts or {}
    index = []
    for entry in terms:
        decision = entry.get("glyph")
        if decision is not True and decision != UNDECIDED:
            # False is a recorded decision to render nothing. Absent means
            # nobody has considered it. Neither matches.
            continue

        term = entry["term"]
        rank = min((PRIORITY.index(c) for c in categories_of(entry)
                    if c in PRIORITY), default=len(PRIORITY))
        keys = [stems(term)] + [stems(t) for t in entry.get("glyph_triggers", []) or []]
        index.append({
            "term": term,
            "glyph": _glyph_render(entry),
            "rank": rank,
            "count": counts.get(term, 0),
            "keys": [k for k in keys if k],
        })

    # Rarer wins inside a category. The term breaks any remaining tie, so two
    # runs of the same build never disagree.
    return sorted(index, key=lambda e: (e["rank"], e["count"], e["term"]))


# What an undecided concept's chip is tinted, by category. Colour carries
# meaning, and the meaning is what the concept does to the player: a state is
# something that has happened to you, an action is something you do, an object
# is neither. A concept can override this by naming its own render.
TINT_BY_CATEGORY = {
    "state": "negative",
    "modifier": "secondary",
    "entity": "secondary",
    "action": "accent",
    "phase": "accent",
}
DEFAULT_TINT = "secondary"


def _glyph_render(entry: dict) -> dict:
    """Exactly what the app draws, resolved here rather than in Swift.

    The app renders what it is given and looks nothing up, so the whole
    mapping from concept to appearance stays in the lexicon where it can be
    reviewed, and the app degrades by simply not drawing anything it cannot
    understand.

    `name` travels alongside for the accessibility label. A glyph that
    replaces a word still has to be readable aloud.
    """
    term = entry["term"]
    render = entry.get("glyph_render")

    if render:
        out = {"name": term}
        out.update(render)
        return out

    # Undecided with nothing specified: a chip of its own name. This is what
    # lets a concept ship and be looked at before anyone chooses a symbol.
    cats = categories_of(entry)
    tint = next((TINT_BY_CATEGORY[c] for c in cats if c in TINT_BY_CATEGORY),
                DEFAULT_TINT)
    return {"name": term, "chip": term.upper(), "tint": tint}


def glyph_for(text: str, index: list[dict]) -> dict | None:
    """The one glyph this row shows, or None.

    The index is already in priority order, so the first concept found is the
    one that wins.
    """
    row = stems(text or "")
    if not row:
        return None
    for entry in index:
        for key in entry["keys"]:
            if _contains(row, key):
                return entry["glyph"]
    return None


def _contains(row: list[str], key: list[str]) -> bool:
    n = len(key)
    return any(row[i:i + n] == key for i in range(len(row) - n + 1))


def annotate(entry: dict, index: list[dict]) -> dict:
    """Glyph arrays for one entry, parallel to the fields they annotate.

    Returns only the arrays. The caller merges them, because `rewrites/` is
    hand-authored and must never be written back to: annotation happens on the
    way into the database and nowhere else.

    A row with no glyph gets None rather than being skipped. A gap would slide
    every later glyph onto the wrong row.
    """
    out: dict = {}

    state = entry.get("state")
    if state:
        out["state_glyphs"] = [glyph_for(line, index) for line in state]

    effects = entry.get("effects")
    if effects:
        # Sorted by label, because that is the order the app renders them in:
        # a truth table that reshuffles between launches is disorienting, so
        # RuleStructure.orderedEffects sorts. Annotating in file order instead
        # would put every glyph on the wrong row for any entry whose effects
        # were not already written alphabetically.
        #
        # Both halves of the row are read: the label names the thing and the
        # value says what happens to it, and either can carry the concept.
        out["effect_glyphs"] = [glyph_for(f"{k} {v}", index)
                                for k, v in sorted(effects.items())]

    branch = entry.get("branch") or {}
    options = branch.get("options")
    if options:
        out["branch_glyphs"] = [
            glyph_for(f"{o.get('condition', '')} {o.get('outcome', '')}", index)
            for o in options
        ]

    steps = entry.get("steps")
    if steps:
        out["step_glyphs"] = [
            glyph_for(f"{s.get('actor', '')} {s.get('action', '')}", index)
            for s in steps
        ]

    return out
