"""One-way fingerprints of source text, so the paraphrase tripwire keeps
working after the verbatim bodies leave the repository.

The tripwire asks one question: does an authored entry share a run of
`OVERLAP_TOKENS` consecutive tokens with its source? Answering it needs the
source's token runs — not the source's readable text. So we commit salted
hashes of every run and intersect against them.

What this deliberately does not do: store anything recoverable. A hash is
12 hex characters of a salted SHA-256 over a 12-token run. Recovering the
run means guessing all twelve tokens in order and confirming against the
hash, which requires already possessing the text.
"""

from __future__ import annotations

import hashlib
import re

# Bumping either value invalidates every committed fingerprint — `just parse`
# regenerates them, and verify fails loudly on a mismatch rather than
# silently checking nothing.
SHINGLE_TOKENS = 12
DIGEST_CHARS = 12

# Not a secret. It exists so the fingerprints are specific to this project
# rather than a hash any rainbow table of English 12-grams would resolve.
SALT = "rulecheck/shingles/v1"


def tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


def fingerprint(run: tuple[str, ...]) -> str:
    joined = " ".join(run)
    return hashlib.sha256(f"{SALT}\x00{joined}".encode()).hexdigest()[:DIGEST_CHARS]


def fingerprints(text: str, n: int = SHINGLE_TOKENS) -> set[str]:
    """Every n-token run in `text`, hashed. Empty when the text is shorter
    than n tokens — a run that does not exist cannot overlap."""
    toks = tokens(text)
    return {fingerprint(tuple(toks[i:i + n])) for i in range(len(toks) - n + 1)}


def dump(sections, path) -> None:
    """Write per-section fingerprints beside the index.

    `n` and `salt` travel with the data so a future change to either is a
    visible mismatch rather than a check that quietly stops matching.
    """
    import json
    from pathlib import Path

    payload = {
        "n": SHINGLE_TOKENS,
        "salt": SALT,
        "sections": {s.id: sorted(fingerprints(s.body)) for s in sections if s.body},
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def load(path) -> dict[str, set[str]]:
    import json
    from pathlib import Path

    payload = json.loads(Path(path).read_text())
    if payload.get("n") != SHINGLE_TOKENS or payload.get("salt") != SALT:
        raise ValueError(
            f"{path}: fingerprints were built with n={payload.get('n')} "
            f"salt={payload.get('salt')!r}, but this build uses n={SHINGLE_TOKENS} "
            f"salt={SALT!r} — re-run `just parse`"
        )
    return {sid: set(v) for sid, v in payload["sections"].items()}
