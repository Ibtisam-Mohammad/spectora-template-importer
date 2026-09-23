"""The rules checklist and the test suite must agree."""

from collections import Counter

from tests.rules_catalog import UNIT_GROUPS, documented_rule_ids, rule_group, tagged_rules
from tests.rules_pending import PENDING


def test_rule_ids_are_unique():
    duplicates = [rule for rule, n in Counter(documented_rule_ids()).items() if n > 1]
    assert not duplicates, f"duplicate rule ids in docs/rules.md: {duplicates}"


def test_tests_cite_only_documented_rules():
    unknown = set(tagged_rules()) - set(documented_rule_ids())
    assert not unknown, f"tests cite rules missing from docs/rules.md: {sorted(unknown)}"


def test_pending_lists_only_documented_rules():
    unknown = PENDING - set(documented_rule_ids())
    assert not unknown, f"rules_pending.py lists unknown rules: {sorted(unknown)}"


def test_every_rule_is_tested_or_pending():
    missing = set(documented_rule_ids()) - set(tagged_rules()) - PENDING
    assert not missing, f"rules with no test and not marked pending: {sorted(missing)}"


def test_no_rule_is_both_tested_and_pending():
    both = set(tagged_rules()) & PENDING
    assert not both, f"tested rules still listed in rules_pending.py: {sorted(both)}"


def test_format_rules_have_a_unit_test():
    tagged = tagged_rules()
    lacking = [
        rule
        for rule in documented_rule_ids()
        if rule_group(rule) in UNIT_GROUPS
        and rule in tagged
        and not any(path.startswith("tests/unit/") for path in tagged[rule])
    ]
    assert not lacking, f"format rules tested only outside tests/unit: {lacking}"
