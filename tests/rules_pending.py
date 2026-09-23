"""Rules not yet implemented. Remove an ID the moment a test verifies it.

The rules meta-test requires every rule in docs/rules.md to be either tagged by a test or listed
here, and forbids a rule from being both. The build is complete when this set is empty.
"""

PENDING: frozenset[str] = frozenset(
    {
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8",
        "T1", "T2", "T3", "T4", "T5",
        "S1", "S2", "S3", "S4", "S5", "S6",
        "O1", "O2", "O3", "O4", "O5",
        "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
        "PH1", "PH2",
        "H1", "H2", "H3", "H4", "H5", "H6",
        "D1", "D2",
        "R1", "R2", "R3", "R4", "R5", "R6",
        "E1", "E2", "E3", "E4", "E5", "E6",
        "Z1", "Z2",
    }
)  # fmt: skip
