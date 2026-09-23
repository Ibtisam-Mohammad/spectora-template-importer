"""Rules not yet implemented. Remove an ID the moment a test verifies it.

The rules meta-test requires every rule in docs/rules.md to be either tagged by a test or listed
here, and forbids a rule from being both. The build is complete when this set is empty.
"""

PENDING: frozenset[str] = frozenset(
    {
    }
)  # fmt: skip
