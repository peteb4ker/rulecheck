"""Tests for the fidelity-review buddy validator.

The scenarios here come from running a real review over the 62 game-rules
entries, which is what surfaced the independence problem the handoff state
exists to solve.
"""

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_fidelity_review.py"
spec = importlib.util.spec_from_file_location("check_fidelity_review", SCRIPT)
cfr = importlib.util.module_from_spec(spec)
sys.modules["check_fidelity_review"] = cfr
spec.loader.exec_module(cfr)


def build(tmp_path, entries, verdicts):
    (tmp_path / "rewrites").mkdir()
    (tmp_path / "validation").mkdir()
    (tmp_path / "rewrites" / "doc.json").write_text(json.dumps(entries))
    (tmp_path / "validation" / "doc.json").write_text(json.dumps(verdicts))
    return tmp_path


ENTRY = {"archetype": "mechanic", "tier": "standard", "summary": "A rule."}


def verdict_for(entry, **kw):
    record = {"verdict": "clean", "entry_sha256": cfr.entry_hash(entry), "findings": []}
    record.update(kw)
    return record


def finding(**kw):
    f = {"class": "OMISSION", "severity": "high", "note": "source rule dropped"}
    f.update(kw)
    return f


def test_a_clean_verdict_passes(tmp_path):
    root = build(tmp_path, {"s1": ENTRY}, {"s1": verdict_for(ENTRY)})
    errors, warnings = cfr.check(root)
    assert errors == [] and warnings == []


def test_editing_an_entry_after_review_is_stale(tmp_path):
    """The load-bearing check. Without it, an edit launders unreviewed
    content through a gate that already passed."""
    root = build(tmp_path, {"s1": dict(ENTRY, summary="Changed.")},
                 {"s1": verdict_for(ENTRY)})
    errors, _ = cfr.check(root)
    assert any("STALE" in e for e in errors)


def test_an_unresolved_high_severity_finding_fails(tmp_path):
    root = build(tmp_path, {"s1": ENTRY},
                 {"s1": verdict_for(ENTRY, verdict="findings", findings=[finding()])})
    errors, _ = cfr.check(root)
    assert any("unresolved high-severity" in e for e in errors)


def test_a_high_severity_finding_may_be_handed_off_instead_of_fixed(tmp_path):
    """The reviewer reports; the author fixes. Requiring `resolved` to clear
    the gate forced the reviewer to author the fix and then sign off on its
    own work, which is the one thing an independent review must not do."""
    root = build(tmp_path, {"s1": ENTRY},
                 {"s1": verdict_for(ENTRY, verdict="findings",
                                    findings=[finding(acknowledged=True,
                                                      owner="author")])})
    errors, warnings = cfr.check(root)
    assert errors == []
    assert any("awaiting the author" in w for w in warnings)


def test_a_handed_off_finding_still_blocks_a_release(tmp_path):
    """Handing off unblocks the review loop, not the ship. --strict is the
    release gate and an acknowledged finding is still an open defect."""
    root = build(tmp_path, {"s1": ENTRY},
                 {"s1": verdict_for(ENTRY, verdict="findings",
                                    findings=[finding(acknowledged=True,
                                                      owner="author")])})
    errors, _ = cfr.check(root, strict=True)
    assert any("high-severity" in e for e in errors)


def test_handing_off_needs_an_owner(tmp_path):
    """An acknowledged finding with nobody named is a finding nobody owns."""
    root = build(tmp_path, {"s1": ENTRY},
                 {"s1": verdict_for(ENTRY, verdict="findings",
                                    findings=[finding(acknowledged=True)])})
    errors, _ = cfr.check(root)
    assert any("needs an owner" in e for e in errors)


def test_a_finding_cannot_be_both_resolved_and_awaiting_someone(tmp_path):
    root = build(tmp_path, {"s1": ENTRY},
                 {"s1": verdict_for(ENTRY, verdict="findings",
                                    findings=[finding(resolved=True, acknowledged=True,
                                                      owner="author")])})
    errors, _ = cfr.check(root)
    assert any("both resolved and acknowledged" in e for e in errors)


def test_a_low_severity_finding_needs_no_disposition(tmp_path):
    root = build(tmp_path, {"s1": ENTRY},
                 {"s1": verdict_for(ENTRY, verdict="findings",
                                    findings=[finding(severity="low")])})
    errors, _ = cfr.check(root)
    assert errors == []


def test_a_missing_verdict_warns_but_fails_under_strict(tmp_path):
    root = build(tmp_path, {"s1": ENTRY}, {})
    errors, warnings = cfr.check(root)
    assert errors == [] and any("no fidelity verdict" in w for w in warnings)
    errors, _ = cfr.check(root, strict=True)
    assert any("no fidelity verdict" in e for e in errors)


def test_scoping_to_one_document_hides_other_documents_pending_work(tmp_path):
    """183 unreviewed entries produced 183 warning lines, which buried the
    one line that mattered. Reviewing document by document needs to see only
    the document being reviewed."""
    (tmp_path / "rewrites").mkdir()
    (tmp_path / "validation").mkdir()
    (tmp_path / "rewrites" / "doc.json").write_text(json.dumps({"s1": ENTRY}))
    (tmp_path / "rewrites" / "other.json").write_text(json.dumps({"s2": ENTRY}))
    (tmp_path / "validation" / "doc.json").write_text(
        json.dumps({"s1": verdict_for(ENTRY)}))

    _, warnings = cfr.check(tmp_path)
    assert len(warnings) == 1, "the other document's entry should be pending"

    _, warnings = cfr.check(tmp_path, doc="doc")
    assert warnings == [], "scoped to doc, nothing is pending"


def test_scoping_does_not_hide_a_real_failure_in_that_document(tmp_path):
    root = build(tmp_path, {"s1": dict(ENTRY, summary="Changed.")},
                 {"s1": verdict_for(ENTRY)})
    errors, _ = cfr.check(root, doc="doc")
    assert any("STALE" in e for e in errors)


def test_an_unknown_document_is_an_error_not_a_silent_pass(tmp_path):
    """A typo in --doc must not report a clean review of nothing."""
    root = build(tmp_path, {"s1": ENTRY}, {"s1": verdict_for(ENTRY)})
    errors, _ = cfr.check(root, doc="typo")
    assert any("no such document" in e for e in errors)


def test_a_verdict_for_an_entry_that_does_not_exist_is_an_error(tmp_path):
    root = build(tmp_path, {"s1": ENTRY},
                 {"s1": verdict_for(ENTRY), "ghost": verdict_for(ENTRY)})
    errors, _ = cfr.check(root)
    assert any("does not exist" in e for e in errors)


def test_a_skipped_entry_needs_no_verdict(tmp_path):
    root = build(tmp_path, {"s1": {"skip": "index page, ships nothing"}}, {})
    errors, warnings = cfr.check(root)
    assert errors == [] and warnings == []
