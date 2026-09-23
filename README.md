# Spectora template importer

Take-home for Hive Inspect: import a Spectora HTML-text template export into a structured,
editable, persistent template library. The brief is in `docs/assignment/`.

> Status: format analysis and data-model design are done. The app is not built yet; setup,
> database initialisation and environment variables will be documented here when it is.

## Layout

```
README.md              this file
NOTES.md               what was cut and why, limitations, how work was checked, time spent
docs/
  assignment/          the brief
  format/              what a Spectora export actually contains
    spectora-format.md   file mechanics, headers, encoding, traps
    column-map.md        every one of the 42 columns, measured
    eda-findings.md      identity, ordering, HTML, duplicates, the Plain Text variant
    probe-test-plan.md   the probes run in Spectora to close open questions
  design/
    schema.md            data model, and rule zero: know the format, never the template
    preservation.md      coverage, the cell ledger, HTML render policy, format detection
  research/            background market research, not part of the deliverable
fixtures/
  spectora/            the exports analysed, with provenance in its README
  editor/              HTML copied from Spectora's comment editor
  holdout/             four templates kept unseen until the parser exists
tools/                 analysis scripts, Python standard library only
```

## Analysis tools

No dependencies beyond Python 3.

```
python tools/verify_claims.py fixtures/spectora/probe-html.xls   # re-asserts every documented claim
python tools/invariants.py    fixtures/spectora/*.xls              # structure checks for any export
python tools/coverage.py      fixtures/spectora/*.xls              # which cells the schema consumes
python tools/eda.py           fixtures/spectora/probe-html.xls     # full exploratory profile
```

`verify_claims.py` also asserts facts about the probe comments, so it is meant for
`probe-html.xls`; the other three work on any export.
