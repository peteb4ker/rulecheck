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


def test_sha256_optional_field(tmp_path):
    with_hash = VALID.replace(
        '    file: "fixture.pdf"\n',
        '    file: "fixture.pdf"\n    sha256: "abc123"\n',
    )
    assert load_manifest(write(tmp_path, with_hash))[0].sha256 == "abc123"
    assert load_manifest(write(tmp_path, VALID))[0].sha256 is None


def test_unknown_key_warns(tmp_path, capsys):
    typoed = VALID.replace(
        '    file: "fixture.pdf"\n',
        '    file: "fixture.pdf"\n    sha265: "typo"\n',
    )
    docs = load_manifest(write(tmp_path, typoed))
    assert docs[0].sha256 is None
    err = capsys.readouterr().err
    assert "sha265" in err and "fixture-doc" in err


def test_layout_optional_field(tmp_path):
    with_layout = VALID.replace(
        '    file: "fixture.pdf"\n',
        '    file: "fixture.pdf"\n    layout: true\n',
    )
    assert load_manifest(write(tmp_path, with_layout))[0].layout is True
    assert load_manifest(write(tmp_path, VALID))[0].layout is False
