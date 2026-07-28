import shutil

from rulecheck_pipeline.__main__ import main


def make_repo(tmp_path, fixture_pdf):
    root = tmp_path / "repo"
    (root / "sources").mkdir(parents=True)
    (root / "content").mkdir()
    shutil.copy(fixture_pdf, root / "sources" / "fixture.pdf")
    (root / "sources" / "sources.yaml").write_text(
        """
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
    )
    return root


def test_all_pipeline(tmp_path, fixture_pdf):
    root = make_repo(tmp_path, fixture_pdf)
    assert main(["all", "--root", str(root)]) == 0
    assert (root / "content" / "fixture-doc.json").exists()
    assert (root / "build" / "rulecheck.db").exists()


def test_verify_failure_exit_code(tmp_path, fixture_pdf):
    root = make_repo(tmp_path, fixture_pdf)
    assert main(["parse", "--root", str(root)]) == 0
    # sabotage: blank a leaf body in the content JSON
    p = root / "content" / "fixture-doc.json"
    p.write_text(p.read_text().replace(
        "Flip a coin between turns. If heads, the Pokemon wakes up.", ""))
    assert main(["build", "--root", str(root)]) == 0
    assert main(["verify", "--root", str(root)]) == 1


def test_download_new_then_changed(tmp_path, fixture_pdf):
    root = make_repo(tmp_path, fixture_pdf)
    origin = tmp_path / "origin.pdf"
    origin.write_bytes(b"%PDF-1.4 official pdf bytes")
    yaml_path = root / "sources" / "sources.yaml"
    yaml_path.write_text(yaml_path.read_text().replace(
        'url: "https://example.com/fixture.pdf"', f'url: "{origin.as_uri()}"'))

    assert main(["download", "--root", str(root)]) == 0  # no recorded hash -> "new"
    assert (root / "sources" / "fixture.pdf").read_bytes() == b"%PDF-1.4 official pdf bytes"

    yaml_path.write_text(yaml_path.read_text().replace(
        'file: "fixture.pdf"', 'file: "fixture.pdf"\n    sha256: "' + "0" * 64 + '"'))
    assert main(["download", "--root", str(root)]) == 1  # hash mismatch -> "changed"


def test_release_verify_and_content_status(tmp_path, fixture_pdf):
    import json

    root = make_repo(tmp_path, fixture_pdf)
    assert main(["parse", "--root", str(root)]) == 0
    (root / "rewrites").mkdir()
    # cover only one of the leaf sections -> release verify must fail
    (root / "rewrites" / "fixture-doc.json").write_text(json.dumps({
        "fix-3.2": {"archetype": "note", "tier": "standard",
                    "summary": "Structured.", "paragraphs": ["Line."]}}))
    assert main(["build", "--root", str(root)]) == 0
    assert main(["verify", "--root", str(root)]) == 0          # warnings only
    assert main(["verify", "--release", "--root", str(root)]) == 1
    assert main(["content-status", "--root", str(root)]) == 0
