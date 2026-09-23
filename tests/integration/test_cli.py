import pytest

from app import config
from app.cli import main
from app.db.templates import list_templates
from tests.paths import PROBE_HTML


@pytest.fixture
def configured(conn, database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    config.get_settings.cache_clear()
    yield conn
    config.get_settings.cache_clear()


def test_import_stores_the_file_and_prints_the_ids(configured, capsys):
    assert main(["import", str(PROBE_HTML), "--name", "Probe.xls"]) == 0
    output = capsys.readouterr().out
    assert "stored    template" in output
    assert [summary.name for summary in list_templates(configured)] == ["Probe"]


def test_seed_fills_an_empty_library_once(configured, capsys):
    assert main(["seed"]) == 0
    assert main(["seed"]) == 0
    assert "skipped" in capsys.readouterr().out
    [seeded] = list_templates(configured)
    assert seeded.name == "InterNACHI Residential -2026-09-22"
    assert (seeded.sections, seeded.items, seeded.comments) == (13, 69, 392)


def test_migrate_is_safe_to_repeat(configured, capsys):
    assert main(["migrate"]) == 0
    assert "already up to date" in capsys.readouterr().out
