"""Tests for the skills' buddy validators.

The skills produce judgement; these scripts prove state. They are only
trustworthy if they actually fail when the state is wrong, so every check
gets a negative test.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
CHECK_REVIEW = SCRIPTS / "check_fidelity_review.py"

ENTRY = {"archetype": "note", "tier": "standard",
         "summary": "A summary.", "paragraphs": ["Body."]}


def entry_sha(entry):
    sys.path.insert(0, str(SCRIPTS))
    from check_fidelity_review import entry_hash
    return entry_hash(entry)


def make_repo(tmp_path, entries, verdicts):
    (tmp_path / "rewrites").mkdir()
    (tmp_path / "rewrites" / "doc.json").write_text(json.dumps(entries))
    if verdicts is not None:
        (tmp_path / "validation").mkdir()
        (tmp_path / "validation" / "doc.json").write_text(json.dumps(verdicts))
    return tmp_path


def run_review(root, *extra):
    return subprocess.run(
        [sys.executable, str(CHECK_REVIEW), "--root", str(root), *extra],
        capture_output=True, text=True)


def test_clean_review_passes(tmp_path):
    root = make_repo(tmp_path, {"a-1": ENTRY}, {
        "a-1": {"entry_sha256": entry_sha(ENTRY), "verdict": "clean", "findings": []}})
    result = run_review(root, "--strict")
    assert result.returncode == 0, result.stderr
    assert "fidelity review OK" in result.stdout


def test_stale_verdict_fails(tmp_path):
    """The load-bearing check: an entry edited after review must not pass."""
    root = make_repo(tmp_path, {"a-1": ENTRY}, {
        "a-1": {"entry_sha256": entry_sha(ENTRY), "verdict": "clean", "findings": []}})
    edited = dict(ENTRY, summary="Quietly changed after review.")
    (root / "rewrites" / "doc.json").write_text(json.dumps({"a-1": edited}))
    result = run_review(root)
    assert result.returncode == 1
    assert "STALE" in result.stderr


def test_missing_verdict_warns_then_fails_strict(tmp_path):
    root = make_repo(tmp_path, {"a-1": ENTRY}, {})
    lenient = run_review(root)
    assert lenient.returncode == 0
    assert "no fidelity verdict" in lenient.stderr
    strict = run_review(root, "--strict")
    assert strict.returncode == 1


def test_unresolved_high_severity_finding_fails(tmp_path):
    root = make_repo(tmp_path, {"a-1": ENTRY}, {
        "a-1": {"entry_sha256": entry_sha(ENTRY), "verdict": "findings",
                "findings": [{"class": "OMISSION", "severity": "high",
                              "note": "dropped a scope qualifier"}]}})
    result = run_review(root)
    assert result.returncode == 1
    assert "unresolved high-severity" in result.stderr


def test_resolved_high_severity_finding_passes(tmp_path):
    root = make_repo(tmp_path, {"a-1": ENTRY}, {
        "a-1": {"entry_sha256": entry_sha(ENTRY), "verdict": "findings",
                "findings": [{"class": "OMISSION", "severity": "high",
                              "note": "dropped a scope qualifier", "resolved": True}]}})
    assert run_review(root, "--strict").returncode == 0


def test_skipped_entries_need_no_verdict(tmp_path):
    root = make_repo(tmp_path, {"a-1": {"skip": "colophon"}}, {})
    assert run_review(root, "--strict").returncode == 0


def test_verdict_on_skipped_entry_fails(tmp_path):
    root = make_repo(tmp_path, {"a-1": {"skip": "colophon"}}, {
        "a-1": {"entry_sha256": "x", "verdict": "clean", "findings": []}})
    result = run_review(root)
    assert result.returncode == 1
    assert "skipped entry" in result.stderr


def test_orphan_verdict_fails(tmp_path):
    root = make_repo(tmp_path, {"a-1": ENTRY}, {
        "a-1": {"entry_sha256": entry_sha(ENTRY), "verdict": "clean", "findings": []},
        "gone-9": {"entry_sha256": "x", "verdict": "clean", "findings": []}})
    result = run_review(root)
    assert result.returncode == 1
    assert "does not exist" in result.stderr


@pytest.mark.parametrize("record,needle", [
    ({"verdict": "maybe", "findings": []}, "verdict must be"),
    ({"verdict": "clean", "findings": [{"class": "DRIFT", "severity": "low", "note": "x"}]},
     "'clean' but findings"),
    ({"verdict": "findings", "findings": []}, "but none recorded"),
    ({"verdict": "findings", "findings": [{"class": "TYPO", "severity": "low", "note": "x"}]},
     "class must be"),
    ({"verdict": "findings", "findings": [{"class": "DRIFT", "severity": "medium", "note": "x"}]},
     "severity must be"),
    ({"verdict": "findings", "findings": [{"class": "DRIFT", "severity": "low", "note": "  "}]},
     "needs a note"),
])
def test_malformed_records_fail(tmp_path, record, needle):
    root = make_repo(tmp_path, {"a-1": ENTRY},
                     {"a-1": {"entry_sha256": entry_sha(ENTRY), **record}})
    result = run_review(root)
    assert result.returncode == 1
    assert needle in result.stderr


def test_entry_hash_is_key_order_independent(tmp_path):
    """Reformatting an entry must not invalidate its review."""
    a = {"archetype": "note", "tier": "standard", "summary": "S", "paragraphs": ["P"]}
    b = {"paragraphs": ["P"], "summary": "S", "tier": "standard", "archetype": "note"}
    assert entry_sha(a) == entry_sha(b)
