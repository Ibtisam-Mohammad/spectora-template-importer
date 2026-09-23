"""Rules not yet implemented. Remove an ID the moment a test verifies it.

The rules meta-test requires every rule in docs/rules.md to be either tagged by a test or listed
here, and forbids a rule from being both. The build is complete when this set is empty.
"""

PENDING: frozenset[str] = frozenset(
    {
        "F9",
        "O5",
        "PH2",
        "H1", "H2", "H3", "H4", "H5", "H6",
        "R1", "R2", "R3", "R5",
        "E1", "E2", "E3", "E4", "E5", "E6",
        "Z2",
    }
)  # fmt: skip
