# Held-out templates

Four stock templates from Spectora's Template Center, each added to the trial account and
exported with **Export HTML Text** without any edits, on 23 September 2026.

**They have not been opened or analysed, on purpose.** Everything the parser knows comes from
the fixtures in `../spectora/` and from the file format. These four are run once, after the
parser is written, as a blind test that it generalises. The rule for that run: if a file fails,
fix the general rule that failed. Never add a case for a particular template.

The hashes below were recorded when the files were committed, before any parser code existed,
so the git history shows they were not changed to fit the parser.

| File | Template | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `tpl-gromicko.xls` | Ben Gromicko's Template for Home Inspection, by Big Ben Inspections | 183,353 | `768bf27744d9ac26ec62a32b6c786b02713079189b3c6875ca30f18df6e31903` |
| `tpl-radon.xls` | Radon Inspection, by Spectora | 7,156 | `f81224ef08b0a72d32094ef3cee7c074bbb2d3702495d03395a82b6627c256e7` |
| `tpl-room-by-room.xls` | Room-by-Room Residential Template, by Spectora | 104,896 | `7966e1eabb09ae9e34531e1a81e72a4f05c3ea64437ded96300c3c8cbe35d230` |
| `tpl-trec.xls` | TREC REI 7-6, by Spectora; marked "PDF Output" in Template Center | 32,404 | `db0ef74c46171cd5af4dbfcb26a8bcd3e84a4a59693475a4b9c0c655a169b703` |

Spectora showed a warning when exporting the TREC template: "Note that this template is a
special type (TREC_7_6), which includes data that might not work well with a re-import such as
locked sections and items. We don't recommend re-importing!" That is the only thing known about
its contents, and it came from Spectora's UI, not from the file.

## The run, 23 September 2026

Run once, after the parser, importer, report and editor were finished (parser version 1), with
`python -m app.cli parse` on each file and `pytest --holdout` against a test database. The
hashes above were checked first and all four matched.

**How blind it was.** Radon, TREC and Gromicko were unseen. Room-by-Room was not fully blind:
the analysis used a copy of the same stock template from outside this repository (see
`docs/format/eda-findings.md`), so its size was known in advance. It is still a check that the
parser reproduces those numbers from our own export.

| File | Verdict | Sections | Items | Comments | Deficiency / Info / Limit | Import notes |
| --- | --- | --- | --- | --- | --- | --- |
| `tpl-gromicko.xls` | HTML | 17 | 133 | 1,248 | 921 / 215 / 112 | 73 order ties |
| `tpl-radon.xls` | HTML | 2 | 3 | 10 | 0 / 10 / 0 | 3 order ties |
| `tpl-room-by-room.xls` | HTML | 22 | 136 | 798 | 661 / 114 / 23 | 120 order ties |
| `tpl-trec.xls` | HTML | 7 | 42 | 218 | 141 / 70 / 7 | 1 invariant |

**What held.**

- All four were recognised as HTML Text exports, with all 42 headers and no unknown ones.
- Every row became a comment. None was skipped and none was empty.
- Each file imported, and the in-transaction verification passed: every source row stored
  cell for cell, and the tree read back field for field.
- Parsing the stored rows again reproduced each template exactly, and every comment re-parsed
  on its own from its source row, which is what revert does.
- Room-by-Room gave 22 sections, 136 items and 798 comments, the numbers measured on the
  outside copy. Its 120 order-tie notes match the 120 of 220 groups measured there.
- TREC's warning about locked sections and items did not show up in the file: `Locked`,
  `Simple Format` and `Disable Photos` are empty on every row of all four exports.

**What it found.**

- TREC has one comment, `Type of Storage Equipment` (row 213), with Answer Type `checkbox` and
  no choices. It is reported as an unusual combination and imported as it is. This is the
  intended behaviour, not a failure.
- Gromicko's comment text holds 13 images inside the text, all hosted on Spectora's servers
  (`cdn.spectora.com/editor_assets/...`). The importer copied only the Default Photos, so these
  would have stopped working with the Spectora account, and nothing said so. **A general gap:
  content at risk was not visible.**
- Seven of those images carry `float: left`, which the display policy did not allow, so text
  no longer wrapped around them. **A general gap: ordinary formatting was held back.**
- Gromicko also carries attributes pasted from a website builder (`data-testid`,
  `data-mesh-id`, `data-motion-part`). They carry no formatting; they are kept, not displayed,
  and listed in the report.
- TREC's one YouTube frame is styled `position: absolute` without a positioned container. The
  display drops `position`, and the frame shows at its own size. Nothing to fix.
