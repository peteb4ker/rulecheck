import shutil

from benchside_pipeline.__main__ import main


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
    assert (root / "build" / "benchside.db").exists()


def test_verify_failure_exit_code(tmp_path, fixture_pdf):
    root = make_repo(tmp_path, fixture_pdf)
    assert main(["parse", "--root", str(root)]) == 0
    # sabotage: blank a leaf body in the content JSON
    p = root / "content" / "fixture-doc.json"
    p.write_text(p.read_text().replace(
        "Flip a coin between turns. If heads, the Pokemon wakes up.", ""))
    assert main(["build", "--root", str(root)]) == 0
    assert main(["verify", "--root", str(root)]) == 1
