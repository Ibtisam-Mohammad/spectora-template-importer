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
