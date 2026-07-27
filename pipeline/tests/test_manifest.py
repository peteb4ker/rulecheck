from pathlib import Path

import pytest

from benchside_pipeline.manifest import ManifestError, load_manifest

VALID = """
documents:
  - id: fixture-doc
    prefix: fix
    title: "Fixture Rules Document"
    version: "1.0"
    published: "2026-01-01"
    url: "https://example.com/fixture.pdf"
    file: "fixture.pdf"
    heading_rules:
      - '^(\\d+)\\.\\s+(.+)$'
      - '^(\\d+\\.\\d+)\\s+(.+)$'
"""


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "sources.yaml"
    p.write_text(text)
    return p


def test_load_valid_manifest(tmp_path):
    docs = load_manifest(write(tmp_path, VALID))
    assert len(docs) == 1
    d = docs[0]
    assert d.id == "fixture-doc"
    assert d.prefix == "fix"
    assert d.heading_rules[0] == r"^(\d+)\.\s+(.+)$"


def test_missing_field_raises(tmp_path):
    bad = VALID.replace('    version: "1.0"\n', "")
    with pytest.raises(ManifestError, match="version"):
        load_manifest(write(tmp_path, bad))


def test_duplicate_prefix_raises(tmp_path):
    doubled = VALID + VALID.replace("documents:\n", "").replace(
        "id: fixture-doc", "id: other-doc"
    )
    with pytest.raises(ManifestError, match="prefix"):
        load_manifest(write(tmp_path, doubled))
