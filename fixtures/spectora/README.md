# Spectora export fixtures

Every file here was exported by us from a Spectora free-trial account, starting from Spectora's
own stock **InterNACHI Residential** template, loaded from Spectora's Template Center. None
contains customer data.

Export path in Spectora: Templates, My Templates, select the template, three dots, Export to
spreadsheet, then **Export HTML Text** unless noted. Spectora names the download
`<Template Name>-YYYY-MM-DD.xls`; the files were renamed here.

| File | Rows | What it is |
| --- | --- | --- |
| `internachi-residential-2026-09-22.xls` | 392 | **The primary fixture.** The stock template exactly as loaded, HTML Text export, 22 September 2026. |
| `internachi-residential-rich-comment.xls` | 392 | The same template after rewriting one comment, `Fireplace / Damper Doors / Damper Inoperable`, using every control in Spectora's comment editor: sized text, colour, link, Vimeo embed, and a table with merged cells. Also sets that comment's Default Location, one default photo, a Category and a Recommendation. |
| `probe-html.xls` | 403 | Adds a probe section `ZZ Probe & Test <x>` with one comment of every answer format, every Category, three Recommendations, three default photos, special characters in the section, item and comment names, plus an empty section and an empty item. Exterior items reordered in the UI. |
| `probe-plain.xls` | 403 | The same template state as `probe-html.xls`, exported with **Export Plain Text** seconds later. The failure-case fixture. |
| `probe-duplicate.xls` | 423 | `probe-html.xls` plus two adjacent sections both named `ZZ Dup`, each holding items `General`, `Same`, `Same`. |

`../editor/spectora-editor-kitchen-sink.html` is the source HTML of the rewritten comment, copied
from Spectora's editor code view, used to diff against what the export produced.

`../holdout/` holds four other stock templates that are deliberately not analysed. See the
README there.

What each file taught us is in `docs/format/eda-findings.md`.
