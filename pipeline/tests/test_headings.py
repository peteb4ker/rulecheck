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


APPENDIX_RULE = r"^(Appendix [A-Z]|[1-8])(?::?\s+((?!.*\.{2,})(?=.*[A-Za-z])[^a-z].*))?$"


def test_bare_appendix_heading_falls_back_to_its_number_as_title():
    """The penalty guidelines write "Appendix A" on a line of its own, with no
    title after it. Requiring a title meant the heading was never recognised
    and its content was absorbed into the previous section, leaving a
    judge-relevant appendix findable but not citable."""
    h = classify_line("Appendix A", [APPENDIX_RULE])
    assert h is not None, "bare appendix heading not recognised"
    assert h.number == "Appendix A"
    assert h.title == "Appendix A", "title should fall back to the number"


def test_appendix_heading_with_a_title_keeps_the_title():
    h = classify_line("Appendix A Rating Zones", [APPENDIX_RULE])
    assert (h.number, h.title) == ("Appendix A", "Rating Zones")
