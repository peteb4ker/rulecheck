"""Tests for the fair-use transformation report (issue #7b)."""

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "transformation_report.py"
spec = importlib.util.spec_from_file_location("transformation_report", SCRIPT)
report = importlib.util.module_from_spec(spec)
sys.modules["transformation_report"] = report
spec.loader.exec_module(report)


def test_longest_shared_run_finds_the_reused_stretch():
    source = "the active pokemon is asleep and cannot attack or retreat".split()
    authored = "note that the active pokemon is asleep and cannot attack".split()
    assert report.longest_shared_run(source, authored) == 8


def test_longest_shared_run_is_zero_for_a_real_paraphrase():
    source = "the active pokemon is asleep and cannot attack".split()
    authored = "sleeping blocks attacking until something removes it".split()
    assert report.longest_shared_run(source, authored) == 0


def test_longest_shared_run_needs_consecutive_tokens():
    """Shared words scattered about are not reuse of wording."""
    source = "alpha beta gamma delta".split()
    authored = "delta something gamma something beta".split()
    assert report.longest_shared_run(source, authored) == 1


def test_longest_shared_run_handles_empty_input():
    assert report.longest_shared_run([], ["a"]) == 0
    assert report.longest_shared_run(["a"], []) == 0


def test_budgets_are_below_the_tripwire_threshold():
    """The budgets exist to catch what the tripwire cannot: a section that
    quotes heavily through declared quotes stays inside the 12-token rule and
    is still leaning on its source."""
    assert 0 < report.CORPUS_QUOTE_BUDGET < report.SECTION_QUOTE_BUDGET < 1
