"""The rule IDs documented in docs/rules.md, and the rule IDs the test suite claims to verify.

Tags are found by reading test source with `ast`, not by collecting tests, so a filtered run
(`pytest -k ...`) cannot make a rule look untested.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = ROOT / "docs" / "rules.md"
TESTS_DIR = ROOT / "tests"

_RULE_LINE = re.compile(r"^\s*-\s*\*\*([A-Z]+\d+)\*\*\s*(.*)$", re.MULTILINE)
_GROUP = re.compile(r"^[A-Z]+")

# Rules about the pure format core. Each needs a unit test that runs without a database.
UNIT_GROUPS = {"F", "T", "S", "O", "V", "D", "H"}


def documented_rule_ids() -> list[str]:
    """Rule IDs in the order they appear in docs/rules.md, duplicates included."""
    return [match.group(1) for match in _RULE_LINE.finditer(RULES_FILE.read_text("utf-8"))]


def documented_rules() -> dict[str, str]:
    """Rule ID to its one-line statement."""
    return {m.group(1): m.group(2) for m in _RULE_LINE.finditer(RULES_FILE.read_text("utf-8"))}


def rule_group(rule_id: str) -> str:
    match = _GROUP.match(rule_id)
    return match.group(0) if match else ""


def _is_rule_marker(node: ast.AST) -> bool:
    """True for `pytest.mark.rule(...)` or `mark.rule(...)`."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    owner = node.func.value
    return node.func.attr == "rule" and isinstance(owner, ast.Attribute) and owner.attr == "mark"


def tagged_rules(tests_dir: Path = TESTS_DIR) -> dict[str, set[str]]:
    """Rule ID to the test files (relative, forward slashes) that tag it."""
    tagged: dict[str, set[str]] = {}
    for path in sorted(tests_dir.rglob("test_*.py")):
        relative = path.relative_to(ROOT).as_posix()
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if not _is_rule_marker(node):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    tagged.setdefault(arg.value, set()).add(relative)
    return tagged
