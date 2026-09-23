from app.cli import main
from tests.paths import PRIMARY
from tests.xlsx_builder import build_xlsx


def test_parse_prints_the_structure(capsys):
    assert main(["parse", str(PRIMARY)]) == 0
    output = capsys.readouterr().out
    assert "verdict   SPECTORA_HTML" in output
    assert "sections  13" in output
    assert "items     69" in output
    assert "comments  392  defect=302  info=78  limit=12" in output


def test_parse_reports_a_refusal(tmp_path, capsys):
    path = tmp_path / "notes.xlsx"
    path.write_bytes(build_xlsx([["Room", "Finding"]]))
    assert main(["parse", str(path)]) == 1
    assert "refused   UNKNOWN_SPREADSHEET" in capsys.readouterr().out
