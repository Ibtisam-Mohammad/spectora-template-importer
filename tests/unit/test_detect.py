import pytest

from app.spectora.columns import map_columns
from app.spectora.detect import detect, refusal
from app.spectora.model import Verdict
from app.spectora.workbook import read_workbook
from tests.paths import PRIMARY, PROBE_DUPLICATE, PROBE_HTML, PROBE_PLAIN, RICH_COMMENT
from tests.xlsx_builder import SPECTORA_HEADERS, build_xlsx, spectora_row


def verdict_of(data: bytes):
    workbook = read_workbook(data)
    return detect(workbook, map_columns(workbook))


@pytest.mark.rule("D1")
@pytest.mark.parametrize(
    "path", [PRIMARY, RICH_COMMENT, PROBE_HTML, PROBE_DUPLICATE], ids=lambda p: p.name
)
def test_html_text_exports_are_recognised(path):
    detection = verdict_of(path.read_bytes())
    assert detection.verdict is Verdict.SPECTORA_HTML
    assert refusal(detection) is None


@pytest.mark.rule("D1")
def test_the_plain_text_export_is_recognised_and_explained():
    detection = verdict_of(PROBE_PLAIN.read_bytes())
    assert detection.verdict is Verdict.SPECTORA_PLAIN
    assert refusal(detection) is None
    assert any("Export HTML Text" in reason for reason in detection.reasons)


@pytest.mark.rule("D1", "F6")
def test_a_spreadsheet_without_section_and_item_is_refused_with_its_differences():
    data = build_xlsx([["Room", "Finding", "Notes"], ["Kitchen", "Leak", "x"]])
    detection = verdict_of(data)
    assert detection.verdict is Verdict.UNKNOWN_SPREADSHEET
    refused = refusal(detection)
    assert refused is not None
    assert any("Section Name" in reason for reason in refused.details)
    assert any("'Room'" in reason for reason in refused.details)


@pytest.mark.rule("D1", "F6")
def test_only_section_and_item_are_required():
    data = build_xlsx([["Section Name", "Item Name"], ["S", "I"]])
    assert verdict_of(data).verdict is not Verdict.UNKNOWN_SPREADSHEET


@pytest.mark.rule("D1")
def test_a_template_with_neither_markup_nor_text_is_not_called_plain():
    rows = [SPECTORA_HEADERS, spectora_row(section_name="S", item_name="I", comment_name="C")]
    assert verdict_of(build_xlsx(rows)).verdict is Verdict.SPECTORA_HTML
