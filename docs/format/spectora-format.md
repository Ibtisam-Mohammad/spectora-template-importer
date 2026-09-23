# Spectora template export: verified format reference

> **Evidence log.** This document records what was measured and why. The rules the importer
> follows are maintained in `docs/rules.md`; where the two disagree, `docs/rules.md` wins.

**Every fact below marked "verified" was confirmed by parsing a real Spectora HTML-Text export
(`InterNACHI Residential`, 392 comments) with an XML parser, not inferred from documentation.**

Sources:

- Spectora, *How to Export a Template* — `support.spectora.com/en/articles/2769896`
- Spectora, *How to Import a Template from a Spreadsheet* — `support.spectora.com/en/articles/6198400`
- Spectora's official sample sheet, "Spectora Sample Template Layout", header-only, 28 columns
- Spectora Glossary — article 1821112
- `InspectorHub/OpenInspection` (AGPL-3.0), `server/lib/migration-intake/adapters/spectora.ts`,
  an independently authored reference implementation

> **Licensing note.** OpenInspection is AGPL-3.0. Reading it for design is free. Copying code
> into a publicly deployed app triggers the network-use source-disclosure obligation. Treat it
> as a reference, credit it either way.

---

## Getting the export

Templates → My Templates → select the template → three dots, top right → **Export to
spreadsheet** → **Export HTML Text** → Download File.

**Permission gate.** Spectora: "In order to successfully export a template, it's important to
ensure that the necessary permission is turned on… Settings, then Teams, and finally selecting
Edit Template." If the option is missing on a trial account, that is why.

**Naming inconsistency.** The export article says `Export to spreadsheet`; the import article
calls the same path `Export Template`. Do not expect the label to match the docs exactly.

**Plain vs HTML, Spectora's words.** Plain Text "will remove any HTML elements such as links,
videos, and images, as well as any styling like bold or italics." HTML Text "will allow you to
keep all your comments intact, including any links, styling, and formatting you have added."
Take HTML Text. There is no public plain-text sample to diff against, so the only stated
difference is column D's contents.

---

## The file, verified

| Property | Value |
| --- | --- |
| Filename pattern | `<Template Name>-YYYY-MM-DD.xls` |
| Extension | `.xls` |
| **Actual format** | **OOXML / XLSX.** Magic bytes `PK\x03\x04`, `file` reports "Microsoft Excel 2007+" |
| Worksheets | Exactly one, named `Sheet1` |
| Shared strings | **None.** No `xl/sharedStrings.xml`; all values are inline `<v>` cells |
| Dimension | `A1:AP393` for InterNACHI Residential; `A1:AP799` for Room-by-Room |
| Header row | Row 1. No preamble or junk rows |
| Columns | **42** (A → AP) |
| Row meaning | One row per comment. Section and item names repeat on every row |

**Trap: the extension lies.** A `.xls` file that is really a ZIP will be rejected or
mis-handled by legacy-xls parsers. Detect by file signature, not extension. Package contents
verified: `xl/workbook.xml`, `xl/worksheets/sheet1.xml`, `xl/styles.xml`, `xl/theme/theme1.xml`,
`docProps/*`, `[Content_Types].xml`.

## The 42 headers, byte-exact and verified

```
A   Section Name
B   Item Name
C   Comment Name
D   Comment Text
E   Comment Type (info, limit, defect)
F   Category (-1: Low, 0: Med, 1: High)
G   Multiple Choice Options (comma-separated)
H   Unit Type Options (numeric answers only, comma-separated)
I   Recommendation (from list)
J   Order (w/i item)
K   Answer Type (boolean, checkbox, date, number, range, text)
L   Default Value
M   Default Value 2 (for "range" types)
N   Default Unit Type (for "number" and "range" types)
O   Default Location
P   Default Estimate Min
Q   Default Estimate Max
R   Locked
S   Simple Format
T   Disable Photos
U   Uses
V   Default Photo 1            AB  Default Photo 4            AH  Default Photo 7
W   Default Photo 1 Caption    AC  Default Photo 4 Caption    AI  Default Photo 7 Caption
X   Default Photo 2            AD  Default Photo 5            AJ  Default Photo 8
Y   Default Photo 2 Caption    AE  Default Photo 5 Caption    AK  Default Photo 8 Caption
Z   Default Photo 3            AF  Default Photo 6            AL  Default Photo 9
AA  Default Photo 3 Caption    AG  Default Photo 6 Caption    AM  Default Photo 9 Caption
                               AN  Default Photo 10
                               AO  Default Photo 10 Caption
AP  Last Modified
```

**The documentation is stale.** Spectora's published import format is **28 columns**, stopping
at `Default Photo 3 Caption`. The real export emits Photo 4 through 10 as well. Building
strictly to the documented list silently ignores 14 columns.

**Headers carry parenthetical suffixes.** The column is `Comment Type (info, limit, defect)`,
not `Comment Type`. **Match headers exactly against the 42 known strings**, parenthetical
included. They were byte-identical in every export examined, HTML and Plain. Prefix or pattern
matching would be guessing; `Default Value` is a prefix of `Default Value 2`, which shows why.
If Spectora ever changes a header, report the unknown and the missing header by name rather
than map a column by resemblance. The file is refused only when Section Name or Item Name is
missing (rule F6).

---

## The three traps worth knowing before you write the parser

### 1. Entity encoding is doubled, and the correct handling differs per column

Verified on the raw worksheet XML:

```
raw XML          'Siding, Flashing &amp;amp; Trim'
after XML parse  'Siding, Flashing &amp; Trim'
after HTML decode 'Siding, Flashing & Trim'
```

Every text column arrives double-encoded, so after your XML parser has done its job you are
still holding HTML entities. What you do next must differ by column:

- **`Section Name`, `Item Name`, `Comment Name` are plain text.** They need one further
  HTML-entity decode. Skip it and the inspector sees `Siding, Flashing &amp; Trim` as a
  heading in your UI.
- **`Comment Text` is HTML** and contains real markup: `<p>`, `<a href>`, `<strong>`. Keep it
  as-is after the XML layer and render it. Decoding it again corrupts the markup and turns
  escaped content into live tags, which is both a rendering bug and an injection risk.

Same-looking input, opposite handling. This is the single easiest way to silently corrupt a
customer's template.

### 2. Items are blocks within their section, never names

Verified on InterNACHI Residential: **61 distinct item names resolve to 69 actual items.** Eight
names appear under more than one section. OpenInspection reports the same pattern more severely
on a larger file: 76 names, 90 items, one name appearing under eleven sections.

"Windows" under Bedrooms is not the same item as "Windows" under Kitchen. Key on the name alone
and you merge them, concatenate their comment lists, and produce a template that looks
plausible and is wrong. If you display an import count, display the one your grouping produced,
because that is the number the inspector will check against.

The adopted rule goes further: a new contiguous block is a new section or item even when its
name repeats (rules S2 and S3), because Spectora allows duplicate names.

### 3. `Order (w/i item)` is not scoped to the item

The name is misleading. Verified:

| Grouping key | Groups where order starts at 0 and runs consecutively |
| --- | --- |
| section + item | 27 of 69 |
| section + item + comment type | 110 of 115 |

The counter restarts per **comment type** within the item. In `Exterior / Exterior Doors` the
rows read `0 defect, 0 info, 1 defect, 2 defect…`, so a naive sort on this column inside an
item interleaves the types and puts two comments at position zero.

**The reconstruction rule that works**, measured at 64 of 69 items producing a clean `0..n-1`
in every type group:

1. Take each item's rows, which form one contiguous block.
2. Within the item, group by `Comment Type`.
3. Sort by `Order (w/i item)` **within each type group**.
4. Render the type groups in the order the Spectora UI uses: **Informational, Limitations,
   Deficiencies**.

Do not use raw file order for comments. Only 33 of 69 items happen to be alphabetical by
comment name, and none are in display order.

---

## Verified against the live Spectora UI

Cross-checked the export against screenshots of the same template in Spectora's template
editor.

**Confirmed exactly:**

- The editor is three columns, **Sections | Items | Comments**, matching the glossary's
  "Column 1 / Column 2 / Column 3" and the Template → Section → Item → Comment nesting.
- Comments are bucketed **Informational / Limitations / Deficiencies**, mapping one-to-one onto
  `info` / `limit` / `defect`.
- All 13 sections, with identical names **and identical order** to the file's first-appearance
  order.
- `Inspection Details / General` holds exactly In Attendance, Occupancy, Style, Temperature,
  Type of Building, Weather Conditions, matching `Order` values 0 through 5.
- `Exterior / Exterior Doors` holds one informational comment, **zero limitations** and seven
  deficiencies, and the deficiency order on screen matches `Order` 0 through 6.
- `Answer Type` is rendered as the small icon beside each comment name. Temperature shows a `#`
  and is `number`; its siblings show a list glyph and are `checkbox`.
- The UI's **Answer Choices** are column G `Multiple Choice Options`. For Exterior Entry Door
  they read "Wood, Glass, Steel, Hollow Core, Single Pane, Fiberglass" in both.
- `Default Location` and the default photo slots are empty in both.

**Important mapping clarification.** The UI field labelled **"Default Text"** is column D
`Comment Text`. The comment's *name* is the label in the list; `Comment Text` is the default
narrative body. That is why 83 of 392 rows have an empty `Comment Text`: multiple-choice
informational comments such as Exterior Entry Door carry their content in the answer choices
and have no body at all. An importer that treats an empty `Comment Text` as a broken row will
reject valid data.

### Item order

Resolved in `docs/format/eda-findings.md` §3. The export follows a persisted item order and
tracked a deliberate reorder in the editor, but no column carries it, so the importer reports
item order as best-effort.

---

## Observed values, verified

```
Comment Type   defect 302 | info 78 | limit 12          always populated
Category       "0" 281 | "1" 21 | blank 90              blank on exactly the 78 info + 12 limit rows
Answer Type    boolean 315 | checkbox 72 | number 4 | text 1
Comment Text   309 of 392 populated, raw HTML; 83 blank
Recommendation populated on 4 rows only, lowercase slugs: "pro" x3, "monitor" x1
Last Modified  "09/20/2026 22:54:06"  → MM/DD/YYYY HH:MM:SS, 24-hour, no timezone
```

`Category` is meaningful only for defects. Do not render a severity on an info or limit comment.

**29 of 42 columns are constant across every row in this export**, including all 20 photo
columns (empty), `Locked`, `Simple Format`, `Disable Photos`, `Default Location`,
`Default Unit Type` and `Default Value 2` (all empty), plus:

- `Default Estimate Min` = `10` and `Default Estimate Max` = `1000` on **all 392 rows**
- `Uses` = `0` on all 392 rows

Those are system defaults in these templates. They are stored anyway (rule V8).

---

## What the export does not contain

This is the "missing from the export" bucket, sourced from the vendor rather than from your own
scope cuts.

- **Template name.** Not a column. It survives only in the filename.
- **Section and item ordering.** No order column exists above the comment level, so first
  appearance in the file is the only ordering the file expresses.
- **Section and item settings.** Only the names are exported. Sections also carry Hide Overview
  Grid, Optional/Included, Icon, Standards of Practice and Reminders; items carry Info Item,
  Optional/Included and Reminders. Field-by-field table in `docs/format/column-map.md`.
- **All template-level settings**: Header Text, Display Options, Item Ratings configuration,
  Defect Categories, Reinspection Categories, Reinspection Header Text. Spectora enumerates
  these in its *Copy Template Settings* article precisely because they do not travel.
- **Image and video binaries.** The photo columns are URL and caption text fields only.

**Correction to an earlier note in this file: Spectora has no feature called "conditional
logic."** The nearest equivalent is Classic Ratings show/hide behaviour, where IN items show
informational comments, NI and NP show limitations, and D shows both informational and
deficient. That is a template setting, not per-comment data, and it is not in the file.

---

## Spectora's own object model

From their glossary, which literally labels the nesting by spreadsheet column:

- **Template** — "The 'Blueprint' which reports are created from."
- **Section** — "The largest container of information, usually a room name or system type.
  'Column 1.'"
- **Item** — "The middle container of information. 'Column 2.'"
- **Comment** — "The smallest container… informational comments, limitations, and defects
  observations. 'Column 3.'"

Comment types are Informational, Limitation and Deficiency, and the deficiency label is
user-renameable to Observations, Issues or Recommendations. That maps one-to-one onto Hive's
documented Information, Limitations, and Defects or deficiencies, so the mapping is the
identity.

**"Tags" in Spectora means Location Tags**, an account-level setting for marking where a comment
applies. It is not a comment-tagging taxonomy. The only per-comment hook in the file is
`Default Location`, which was empty throughout.

**Item Rating** has two modes: Classic (fixed IN, NI, NP plus a custom defect label, maximum
four, comments show and hide by rating) and Custom (up to eight, unlinked, all comments always
shown). A per-template setting, absent from the export.

---

## Round-trip import, for reference

Templates → three dots → Add Templates → Import from a Spreadsheet → select file → Import
Template.

- Spectora: "If you have a .csv or other file type, convert it to .xls or .xlsx first."
- The result is named `Imported from XLS - today's date`.
- Spectora: "Importing from a spreadsheet always **creates a new template** — it cannot be added
  to or merged into an existing one."
- Ordering: "narratives (comments) are organized in the order they appear in the spreadsheet
  within each item. Use the `Order (w/i item)` column to control the exact sequence."
- What the importer validates is **not documented**. No error list, no required-versus-optional
  table, no row limit, no statement on unknown columns.

**There is no Spectora public API.** `api.spectora.com` returns 403 with no documentation;
`docs.spectora.com` and `developers.spectora.com` do not resolve. The spreadsheet is the only
public integration surface.

---

## What this means for the build

Maintained as `docs/rules.md`.
