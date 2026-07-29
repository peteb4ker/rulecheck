import dataclasses
import hashlib
import sys

import pytest

from rulecheck_pipeline.check_sources import check_source, check_sources
from rulecheck_pipeline.model import SourceDoc

PDF_BYTES = b"%PDF-1.7\nfake pdf bytes"
PDF_SHA = hashlib.sha256(PDF_BYTES).hexdigest()


@pytest.fixture
def source():
    return SourceDoc(
        id="fixture-doc", prefix="fix", title="Fixture", version="1.0",
        published="2026-01-01", url="https://example.com/fixture.pdf",
        file="fixture.pdf", heading_rules=[r"^(\d+)\.\s+(.+)$"], sha256=PDF_SHA,
    )


@pytest.fixture
def sources_dir(tmp_path):
    d = tmp_path / "sources"
    d.mkdir()
    return d


def test_ok_when_local_file_matches_recorded_hash(source, sources_dir):
    (sources_dir / "fixture.pdf").write_bytes(PDF_BYTES)

    result = check_source(source, sources_dir)

    assert result.status == "ok"
    assert result.sha256 == PDF_SHA
    assert result.expected == PDF_SHA
    assert result.path == sources_dir / "fixture.pdf"


def test_mismatch_when_local_bytes_differ(source, sources_dir):
    other = b"%PDF-1.7\nsomebody else's bytes"
    (sources_dir / "fixture.pdf").write_bytes(other)

    result = check_source(source, sources_dir)

    assert result.status == "mismatch"
    assert result.sha256 == hashlib.sha256(other).hexdigest()
    assert result.expected == PDF_SHA
    # The bad file is left alone — checking never mutates sources/.
    assert (sources_dir / "fixture.pdf").read_bytes() == other


def test_missing_when_file_absent(source, sources_dir):
    result = check_source(source, sources_dir)

    assert result.status == "missing"
    assert result.sha256 is None
    assert result.expected == PDF_SHA


def test_unrecorded_when_manifest_has_no_hash(source, sources_dir):
    (sources_dir / "fixture.pdf").write_bytes(PDF_BYTES)
    source = dataclasses.replace(source, sha256=None)

    result = check_source(source, sources_dir)

    assert result.status == "unrecorded"
    assert result.sha256 == PDF_SHA  # so it can be pasted into sources.yaml
    assert result.expected is None


def test_hashing_streams_a_file_larger_than_one_chunk(source, sources_dir):
    from rulecheck_pipeline.check_sources import CHUNK

    big = b"%PDF-1.7\n" + bytes(range(256)) * ((CHUNK * 3) // 256)
    (sources_dir / "fixture.pdf").write_bytes(big)
    source = dataclasses.replace(source, sha256=hashlib.sha256(big).hexdigest())

    assert check_source(source, sources_dir).status == "ok"


def test_check_sources_reports_every_document_in_manifest_order(sources_dir):
    def doc(doc_id, filename, sha):
        return SourceDoc(
            id=doc_id, prefix=doc_id[:3], title=doc_id, version="1.0",
            published="2026-01-01", url=f"https://example.com/{filename}",
            file=filename, heading_rules=[r"^(\d+)\.\s+(.+)$"], sha256=sha,
        )

    (sources_dir / "good.pdf").write_bytes(PDF_BYTES)
    (sources_dir / "bad.pdf").write_bytes(b"%PDF-1.7\nwrong")
    docs = [doc("aaa", "good.pdf", PDF_SHA),
            doc("bbb", "bad.pdf", PDF_SHA),
            doc("ccc", "gone.pdf", PDF_SHA)]

    results = check_sources(docs, sources_dir)

    assert [(r.doc_id, r.status) for r in results] == [
        ("aaa", "ok"), ("bbb", "mismatch"), ("ccc", "missing")]


def test_module_pulls_in_no_network_client():
    """The whole point of this command is that it works when the WAF has
    locked us out. Importing it must not drag in an HTTP client."""
    module = sys.modules["rulecheck_pipeline.check_sources"]
    imported = {name for name in vars(module)
                if getattr(vars(module)[name], "__name__", "") in
                {"urllib", "urllib.request", "requests", "httpx", "socket"}}
    assert imported == set()
    src = (module.__file__ and open(module.__file__).read()) or ""
    for banned in ("urllib", "requests", "httpx", "socket", "download_doc"):
        assert banned not in src, f"check_sources must stay offline: found {banned}"
