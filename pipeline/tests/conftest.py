from pathlib import Path

import pytest
from reportlab.pdfgen import canvas


def make_pdf(path: Path, lines: list[str]) -> Path:
    c = canvas.Canvas(str(path))
    y = 800
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
        if y < 72:
            c.showPage()
            y = 800
    c.save()
    return path


FIXTURE_LINES = [
    "1. Setup",
    "Shuffle your deck and draw 7 cards.",
    "1.1 Prizes",
    "Set aside 6 prize cards. See section 3.2 for conditions during setup.",
    "2. Turn Structure",
    "Players alternate turns.",
    "3. Special Conditions",
    "Conditions affect Active Pokemon only.",
    "3.2 Asleep",
    "Flip a coin between turns. If heads, the Pokemon wakes up.",
]


@pytest.fixture
def fixture_pdf(tmp_path):
    return make_pdf(tmp_path / "fixture.pdf", FIXTURE_LINES)


@pytest.fixture
def fixture_source():
    from benchside_pipeline.model import SourceDoc

    return SourceDoc(
        id="fixture-doc", prefix="fix", title="Fixture Rules Document",
        version="1.0", published="2026-01-01", url="https://example.com/fixture.pdf",
        file="fixture.pdf",
        heading_rules=[r"^(\d+)\.\s+(.+)$", r"^(\d+\.\d+)\s+(.+)$"],
    )
