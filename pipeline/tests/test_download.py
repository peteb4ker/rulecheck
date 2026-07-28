import dataclasses
import hashlib

import pytest

from rulecheck_pipeline.download import download_doc
from rulecheck_pipeline.model import SourceDoc

PDF_BYTES = b"%PDF-1.7\nfake pdf bytes"


def make_source(tmp_path, content: bytes, sha256=None):
    origin = tmp_path / "origin.pdf"
    origin.write_bytes(content)
    return SourceDoc(
        id="fixture-doc", prefix="fix", title="Fixture", version="1.0",
        published="2026-01-01", url=origin.as_uri(), file="fixture.pdf",
        heading_rules=[r"^(\d+)\.\s+(.+)$"], sha256=sha256,
    )


@pytest.fixture
def dest(tmp_path):
    d = tmp_path / "sources"
    d.mkdir()
    return d


def test_new_download(tmp_path, dest):
    result = download_doc(make_source(tmp_path, PDF_BYTES), dest)
    assert result.status == "new"
    assert result.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert result.path == dest / "fixture.pdf"
    assert result.path.read_bytes() == PDF_BYTES


def test_ok_when_hash_matches(tmp_path, dest):
    digest = hashlib.sha256(PDF_BYTES).hexdigest()
    assert download_doc(make_source(tmp_path, PDF_BYTES, digest), dest).status == "ok"


def test_changed_when_hash_differs(tmp_path, dest):
    result = download_doc(make_source(tmp_path, PDF_BYTES, "0" * 64), dest)
    assert result.status == "changed"
    assert result.path.exists()  # file still saved for inspection


def test_failed_download_leaves_no_file(tmp_path, dest):
    source = make_source(tmp_path, PDF_BYTES)
    source = dataclasses.replace(source, url=(tmp_path / "missing.pdf").as_uri())
    with pytest.raises(OSError):
        download_doc(source, dest)
    assert list(dest.iterdir()) == []


def test_non_pdf_response_rejected(tmp_path, dest):
    source = make_source(tmp_path, b"<html>Pardon Our Interruption</html>")
    with pytest.raises(OSError, match="non-PDF"):
        download_doc(source, dest)
    assert list(dest.iterdir()) == []
