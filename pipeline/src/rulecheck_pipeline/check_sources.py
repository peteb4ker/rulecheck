"""Authenticate the source PDFs already on disk against the manifest.

Deliberately offline: pokemon.com sits behind a WAF that serves bot-challenge
HTML to repeated automated fetches, so the sanctioned fallback is downloading
the PDFs by hand in a browser. That path needs a way to answer "did I get the
right file?" without going back to the network — hence a module that reads
`sources/` and `sources.yaml` and nothing else. Keep it that way: no HTTP
client belongs in here (a test asserts as much).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from rulecheck_pipeline.model import SourceDoc

CHUNK = 65536


@dataclass
class SourceCheck:
    """Outcome of hashing one local file. Status is 'ok' (matches the
    manifest), 'mismatch' (wrong bytes), 'missing' (no file), or 'unrecorded'
    (file present, manifest has no sha256 to check it against)."""
    doc_id: str
    path: Path
    status: str  # "ok" | "mismatch" | "missing" | "unrecorded"
    sha256: str | None      # of the local file; None when missing
    expected: str | None    # from the manifest


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def check_source(source: SourceDoc, sources_dir: Path) -> SourceCheck:
    """Hash sources_dir/source.file and compare with the recorded sha256. Reads only; never writes or fetches."""
    path = Path(sources_dir) / source.file
    if not path.is_file():
        return SourceCheck(source.id, path, "missing", None, source.sha256)
    digest = _hash_file(path)
    if source.sha256 is None:
        status = "unrecorded"
    elif digest == source.sha256:
        status = "ok"
    else:
        status = "mismatch"
    return SourceCheck(source.id, path, status, digest, source.sha256)


def check_sources(sources: list[SourceDoc], sources_dir: Path) -> list[SourceCheck]:
    """Check every manifest document, in manifest order."""
    return [check_source(source, sources_dir) for source in sources]
