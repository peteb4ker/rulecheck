from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from rulecheck_pipeline.model import SourceDoc

USER_AGENT = "rulecheck-pipeline/0.1 (offline rules reference builder)"
CHUNK = 65536
TIMEOUT_SECONDS = 60


@dataclass
class DownloadResult:
    """Outcome of one document fetch; status is 'ok' (hash matches), 'changed' (upstream revised), or 'new' (no recorded hash)."""
    doc_id: str
    status: str  # "ok" | "changed" | "new"
    sha256: str
    path: Path


def download_doc(source: SourceDoc, dest_dir: Path) -> DownloadResult:
    """Atomically fetch source.url into dest_dir/source.file, hashing while streaming; validates PDF magic bytes before destination write; raises OSError leaving no file on failure."""
    dest_dir = Path(dest_dir)
    dest = dest_dir / source.file
    request = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    fd, tmp_name = tempfile.mkstemp(dir=dest_dir, prefix=f".{source.file}.")
    try:
        with os.fdopen(fd, "wb") as tmp, urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            first = resp.read(CHUNK)
            if not first.startswith(b"%PDF-"):
                raise OSError(
                    f"{source.url} returned non-PDF content "
                    f"(starts with {first[:32]!r}) — likely a bot-challenge page"
                )
            digest.update(first)
            tmp.write(first)
            while chunk := resp.read(CHUNK):
                digest.update(chunk)
                tmp.write(chunk)
        os.replace(tmp_name, dest)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise
    hex_digest = digest.hexdigest()
    if source.sha256 is None:
        status = "new"
    elif hex_digest == source.sha256:
        status = "ok"
    else:
        status = "changed"
    return DownloadResult(doc_id=source.id, status=status, sha256=hex_digest, path=dest)
