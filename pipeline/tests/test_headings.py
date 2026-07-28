from rulecheck_pipeline.headings import Heading, classify_line

RULES = [r"^(\d+)\.\s+(.+)$", r"^(\d+\.\d+)\s+(.+)$"]


def test_level_one_heading():
    assert classify_line("3. Special Conditions", RULES) == Heading(1, "3", "Special Conditions")


def test_level_two_heading():
    assert classify_line("3.2 Asleep", RULES) == Heading(2, "3.2", "Asleep")


def test_body_line_is_not_heading():
    assert classify_line("Flip a coin. If heads, the Pokemon wakes up.", RULES) is None


def test_leading_whitespace_tolerated():
    assert classify_line("  3.2 Asleep ", RULES) == Heading(2, "3.2", "Asleep")
