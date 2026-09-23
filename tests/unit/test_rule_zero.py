"""Rule zero: the format core knows Spectora's format, never a template's content."""

import ast
from pathlib import Path

import pytest

from tests.helpers import analysed
from tests.paths import ANALYSED, ROOT

CORE = ROOT / "app" / "spectora"

# Format tokens that happen to equal something an inspector typed. Each needs a reason.
FORMAT_TOKENS = {
    "Type": "OOXML relationship attribute read in workbook.py; a stock comment is also named Type",
}


def _string_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text("utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _template_content() -> set[str]:
    """Everything an inspector could have typed, across every analysed fixture."""
    content: set[str] = set()
    for path in ANALYSED:
        template = analysed(path).template
        content.update(section.name for section in template.sections)
        content.update(item.name for item in template.items())
        for comment in template.comments():
            content.update((comment.name, comment.recommendation, comment.default_location))
            content.update((*comment.choices, *comment.unit_options))
            content.update(photo.caption for photo in comment.photos)
    return {value.strip() for value in content if len(value.strip()) >= 2}


@pytest.mark.rule("Z1")
def test_the_format_core_contains_no_template_content():
    content = _template_content()
    leaks = {
        f"{path.name}: {literal!r}"
        for path in CORE.glob("*.py")
        for literal in _string_literals(path)
        if literal.strip() in content and literal not in FORMAT_TOKENS
    }
    assert not leaks, f"template content hard-coded in app/spectora: {sorted(leaks)}"


@pytest.mark.rule("Z1")
def test_the_guard_would_catch_a_leak(tmp_path):
    leaky = tmp_path / "leaky.py"
    leaky.write_text('if section == "Exterior":\n    pass\n', "utf-8")
    assert "Exterior" in _string_literals(leaky) & _template_content()
