from pathlib import Path

import pytest

pytest_plugins = ["tests.rules_plugin"]

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--holdout", action="store_true", help="run the held-out templates once")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--holdout"):
        return
    skip = pytest.mark.skip(reason="held-out templates run only with --holdout")
    for item in items:
        if "holdout" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES
