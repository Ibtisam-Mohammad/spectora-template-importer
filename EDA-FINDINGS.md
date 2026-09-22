# EDA findings

Exploratory analysis of Spectora HTML-text exports, run by `tools/eda.py` and
`tools/invariants.py`.

Two files analysed:

| File | Rows | Sections | Items | Distinct item names |
| --- | --- | --- | --- | --- |
| `InterNACHI Residential -2026-09-22.xls` (committed) | 392 | 13 | 69 | 61 |
| Room-by-Room Residential (second export, generalisation test) | 798 | 22 | 136 | **62** |

Both are 42 columns. The second file exists only to prove the parser rules generalise; it is
not committed.

---

## 1. Parsing hazards in the file mechanics

**Cells are sparse, and in two different ways.** Some columns have **no `<c>` element at all**
on a given row, others have a `<c>` element with no `<v>` child. Both mean empty, and a parser
must handle both.

| Absent element entirely | Present but valueless |
| --- | --- |
| F (90 rows), G (320), H (388), I (388), **V–AO (all 392 rows)** | H (1), L (339), M, N, R, S, T (392 each), O (391) |

All twenty photo columns have **zero cells in the entire data region** despite appearing in the
header. **Index cells by the `r` attribute, never by position in the cell list.** A parser that
walks `<c>` elements in order will shift every column right of the first gap. This is the most
likely silent failure in the whole file.

**Cell type is `t="str"` on 2,877 cells.** That is the OOXML "formula result string" type, not
the usual shared-string or inline-string type, and there is no `sharedStrings.xml`. Some
spreadsheet libraries treat `t="str"` as a cached formula value and behave oddly. Test whatever
library you pick against this file specifically.

**Whitespace is not clean.** 210 of 309 populated `Comment Text` values and 11 `Comment Name`
values carry leading or trailing whitespace. No value is whitespace-only.

**Comment Text contains raw line breaks:** 253 line feeds and 43 carriage returns. Any
line-oriented processing of the cell values will break.

**Non-ASCII characters are present**, all in `Comment Text`: 189 non-breaking spaces (U+00A0,
from `&nbsp;`) and 2 right single quotation marks (U+2019). Read and write UTF-8 end to end, and
do not "normalise" whitespace, because collapsing U+00A0 changes rendered output.

---

## 2. Identity hazards

### Comment name is not unique within an item

`Fireplace / Damper Doors` contains **two comments both named `Damper Inoperable`**. A schema
keyed on `(section, item, comment name)` silently drops one.

**Use a surrogate key plus row position.** Do not derive comment identity from the name.

### Item name is not unique within the template

Measured reuse across sections:

| File | Item names reused | Worst case |
| --- | --- | --- |
| InterNACHI Residential | 2 | `General` under 8 sections |
| Room-by-Room | **13** | 62 distinct names resolving to 136 items |

In the Room-by-Room template, keying items on name alone would collapse **136 items into 62**,
merging every room's `Doors`, `Windows`, `Floors` and `Walls` into one. Item identity is
`(Section Name, Item Name)`. This is the single most damaging mistake available.

---

## 3. Ordering is only partially recoverable

This corrects an earlier, more confident conclusion.

**`Order (w/i item)` is a sort hint, not an index.** Measured density of a clean `0..n-1`
sequence per `(section, item, comment type)` group:

| File | Dense groups | Groups with duplicate Order values | Groups with gaps |
| --- | --- | --- | --- |
| InterNACHI Residential | 110 / 115 | 1 | 2 |
| Room-by-Room | **25 / 220** | **120** | 127 |

In Room-by-Room the column is frequently constant. All ten defects under `Roof / Coverings`
carry `Order = 5`. All six informational comments under `Inspection Details / General` carry
`Order = 5`.

**File position is not a reliable fallback either.** Those same six informational comments
appear in the InterNACHI file in forward alphabetical order with `Order` 0 through 5, and in the
Room-by-Room file in **reverse** order with `Order` constant at 5.

**Item order does not match the UI at all.** Two independent exports both order `Exterior` as
`… Eaves, Walkways, Vegetation`; Spectora's editor shows Vegetation before Walkways. Section
order matched the UI exactly in both files.

**Practical rule:** sort comments by `Order`, tie-break on row position, render type groups as
Informational, Limitations, Deficiencies. Then **state in the import report that display order
is best-effort**, because the export does not reliably encode it. Presenting a reordered
template as a faithful copy would be the dishonest option.

---

## 4. Invariants that held on both files

These are safe to validate against, and a violation is worth surfacing rather than ignoring.

- 42 columns, header on row 1, single sheet `Sheet1`.
- Every row has a non-blank `Section Name` and `Item Name`.
- `Comment Type` is always one of `info`, `limit`, `defect`.
- `Answer Type` is always within the documented six.
- **`Category` is populated if and only if `Comment Type == defect`.** Zero exceptions across
  1,190 rows.
- **`Multiple Choice Options` is populated if and only if `Answer Type == checkbox`.** Zero
  exceptions in either direction.

Type and answer-type correlate strongly: every `defect` and every `limit` row is `boolean`.
Only `info` rows vary, carrying `checkbox`, `number`, `text` and one `boolean`.

`date` and `range` never occur in either file but are documented, so accept them.

---

## 5. Comment Text / HTML

- 309 of 392 populated. **111 populated bodies contain no markup at all**; 198 contain HTML.
- Tags used are only `<p>` (244), `<a>` (43), `<strong>` (1), `<div>` (1).
- **Zero unbalanced tags** across both files. The HTML is well-formed.
- Attributes: `href`, `target`, one `class`, one `style`.
- **31 `&amp;` entities survive XML decoding and must remain encoded**, because the value is
  HTML.
- **43 hyperlinks to 20 external hosts.** None are Spectora-hosted, so they will not break on
  migration. Mostly consumer DIY sites, plus `nachi.org`, `youtube.com` and one `porch.com`.
  Many use `http://` rather than `https://`.

Lengths, useful for column sizing: Section max 44, Item max **62**, Comment Name max 42,
Comment Text max 665. A 50-character truncation on item names, which one open-source
implementation applies, would corrupt data in this file.

---

## 6. Multiple choice options

- 72 rows carry choices, ranging from 2 to 18 options each.
- **The format has no escaping mechanism for embedded commas.** A choice value containing a
  comma is unrecoverable by construction. None were observed in either file, but this is a
  format limitation to declare rather than a solved problem.
- Choice values legitimately contain ampersands and quote characters, for example
  `Knob & Tube` and `1 1/2"`.
- `Multiple Choice Options` is single entity-encoded, unlike the name and body columns. See
  `COLUMN-MAP.md`.

---

## 7. Columns carrying no customer information

Constant across all 392 rows of the committed file:

- `Default Estimate Min` = `10`, `Default Estimate Max` = `1000`, `Uses` = `0`. System
  defaults, not authored values.
- `Default Value 2`, `Default Unit Type`, `Default Location`, `Locked`, `Simple Format`,
  `Disable Photos` and all twenty photo columns are empty throughout.

`Default Value` is populated on exactly one row. `Recommendation` on four, as opaque lowercase
slugs (`pro`, `monitor`). `Unit Type Options` on three.

Surfacing any of these in an editor as though the customer configured them is worse than
omitting them.

---

## 8. Consequences for the importer

1. Index cells by the `r` attribute. Never by position.
2. Treat absent `<c>` and valueless `<c>` identically as empty.
3. Item key is `(section, item)`. Comment key is a surrogate plus row position.
4. Sort comments by `Order`, tie-break on row position, and declare ordering as best-effort.
5. Preserve `Comment Text` byte-for-byte after XML decoding. Do not trim, normalise whitespace
   or re-encode entities.
6. Validate the six invariants in section 4 and report violations instead of silently
   coercing.
7. Accept all six documented `Answer Type` values, not only the four present.
8. Suppress the constant columns in section 7 from the editor, and record them as
   deliberately not modelled.
