# EDA findings

Exploratory analysis of Spectora HTML-text exports, run by `tools/eda.py` and
`tools/invariants.py`.

Two files analysed:

| File | Rows | Sections | Items | Distinct item names |
| --- | --- | --- | --- | --- |
| `fixtures/spectora/internachi-residential-2026-09-22.xls` (committed) | 392 | 13 | 69 | 61 |
| `fixtures/spectora/internachi-residential-rich-comment.xls` (committed; same account, one comment rewritten with every editor control) | 392 | 13 | 69 | 61 |
| `probe-html.xls` (committed; same account plus a probe section exercising every answer format, every category, three recommendations, three photos, special characters, and an empty section and item) | 403 | 14 | 70 | 62 |
| `probe-plain.xls` (committed; the same template exported as Plain Text seconds later) | 403 | 14 | 70 | 62 |
| `probe-duplicate.xls` (committed; probe-html plus two adjacent sections both named `ZZ Dup`) | 423 | 15 by block | 74 by block | 63 |
| Room-by-Room Residential (second export, generalisation test) | 798 | 22 | 136 | **62** |

Both are 42 columns. The second file exists only to prove the parser rules generalise; it is
not committed.

---

## 0. Reconfirmation on `probe-html.xls`

Every claim in this document and in `docs/format/column-map.md` was re-tested against `probe-html.xls`
alone by `tools/verify_claims.py`, which asserts each one with evidence:

```
python tools/verify_claims.py fixtures/spectora/probe-html.xls
probe-html.xls: 75/75 claims PASS
```

The three analysis tools were also re-run on that file. `tools/invariants.py` now reports one
deliberate failure, "Answer Type within documented enum", because `signature` is real and the
header's own list of six is incomplete. That failure is the tool working. `tools/coverage.py`
had its "constant" heuristic corrected: a column is constant only when it holds one non-empty
value on every row; a column with a single populated cell is sparse data, not a default.

Coverage on `probe-html.xls` with the corrected tool and the schema as written:

| Measure | Value |
| --- | --- |
| Grid | 403 rows × 42 columns = 16,926 cells |
| Non-empty | 4,753 |
| Consumed by the schema | 3,544, **74.6%** of non-empty |
| Not consumed | 1,209, all in `Default Estimate Min`, `Default Estimate Max`, `Uses` |
| **Non-empty cells not consumed that vary** | **0** |

One finding is new to this pass and is recorded under column L: a `boolean` comment's
`Default Value` serialises as `true` when ticked and as **`f`** in at least one other state (row
263), so the column carries two different spellings of a boolean and must not be coerced.

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

### Duplicate names

**Duplicate names are allowed, and adjacent duplicates are merged by the export at both
levels.** Tested with `probe-duplicate.xls`. In Spectora: two sections both named `ZZ Dup`, next
to each other, each holding three items `General`, `Same`, `Same`. Six items across two sections,
20 comments. What the export contains:

| | In Spectora | In the export |
| --- | --- | --- |
| Sections | `ZZ Dup`, `ZZ Dup` | one `ZZ Dup` block of 20 rows |
| Items | `General`, `Same`, `Same` in each | `General`, `Same`, `General`, `Same` |
| Comments per item | 6, 2, 2, 6, 2, 2 | 6, 4, 6, 4 |

The file has no section or item identifier, only names repeated on every row, so two same-named
neighbours produce one unbroken block and the boundary between them is gone. No rule can recover
it. What each grouping rule produces from this file:

| Rule | Sections | Items | Correct? |
| --- | --- | --- | --- |
| Group by name | 1 | 2 (`General` 12, `Same` 8) | no, merges everything |
| **Group by contiguous block** | 1 | 4 (6, 4, 6, 4) | closer; loses what the file lost |
| Truth | 2 | 6 | not recoverable from the file |

**Rule adopted: a new contiguous block starts a new node, even if the name repeats.** Twice in the
sheet means twice in the model. It never merges what the file keeps separate. It cannot split
what the file already merged.

**Detection is possible for sections, not for items.** When an item name reappears in a separate
block inside one section block, as `General` and `Same` do here, that is the signature of two
merged same-named sections. Report it: "Items General and Same each appear twice in ZZ Dup.
Spectora exports adjacent sections with the same name as one section; if you had two, split
them." Do not split automatically; a section that genuinely lists `General`, `Same`, `General`
would be split wrongly. Two adjacent same-named *items* leave no trace at all: `Same` + `Same`
with two comments each is indistinguishable from one `Same` with four.

Evidence the first half of the block is Spectora's section copy: its 10 comments all carry the
same save time, `09/23/2026 00:46:57`, while the hand-made section's comments carry ten
different times. The copy was exported before the original.

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

**Item order follows a persisted order that the file cannot verify.** Three observations.
The first export ordered `Exterior` as `... Eaves, Walkways, Vegetation` while a UI screenshot
showed Vegetation first. The second export showed Vegetation first, matching the UI. Then
Walkways was deliberately dragged above Vegetation in the UI and a third export showed Walkways
first, **matching the UI again**. So the export does track a persisted item order, and the one
mismatch is unexplained and may have been an accidental drag in a drag-and-drop interface. The
engineering conclusion does not change: there is no order column above the comment level, so
the importer cannot confirm from the file alone that first-appearance order is the current
display order. Section order matched the UI in every export examined.

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
- **The single `style` attribute is an empty YouTube embed wrapper.** `<div
  class="youtube-embed-wrapper" style="position:relative;padding-bottom:56.25%;…">&nbsp;</div>`
  with no `<iframe>` inside. Seven identical empty shells in Room-by-Room. **These are artifacts
  of the stock template, not export loss**: a round-trip test proved the export preserves
  Froala video embeds intact. See `docs/design/preservation.md` section 4.
- **Names that contain `<letter…>` are corrupted on export.** `<x>` becomes `<x></x>` in the HTML
  export and is stripped in the Plain export. The UI shows them correctly. See `docs/format/column-map.md`,
  "Name columns".
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
  `docs/format/column-map.md`.

---

## 6a. The Plain Text export, measured

Same template exported as Plain Text seconds after the HTML export. Differs in columns A (118
rows), B (156), C (1) and D (213), not in D alone.

What it does to `Comment Text`:

- Removes every tag. Zero rows retain any markup.
- **Drops all 43 link URLs.** Link text survives; the `href` does not. Unrecoverable.
- Flattens tables by concatenating cell text with **no separator at all**:
  `Headline 1Headline 2Headline 3RedBluePurpleone1two2`.
- Converts `&amp;` to a bare `&` (31 to 0), keeps every U+00A0 (194 to 194), and drops about a
  sixth of the newlines (306 to 252), so paragraph breaks partly survive and block boundaries do
  not.

What it does to names: strips anything tag-shaped, leaving the surrounding whitespace, and
single-encodes `&` where the HTML export double-encodes it.

Detection signals, all measured: no `<` followed by a letter anywhere in column D; no `&amp;` in
column D after XML decoding; names in A and B carrying a bare `&` after XML decoding rather than
`&amp;`. Any one is sufficient; check all three and report which fired.

## 6b. Default Location is a flattened multi-select

Confirmed from Spectora's Location picker: tags from three groups (level, direction, room) are
space-joined into one string with a leading space, in picker order. Tag labels themselves contain
spaces, so the string cannot be split back into tags without the account's tag vocabulary, which
is not in the export. A custom tag with a bare comma as its label was added as a test and
survived the round trip, so tag labels can be arbitrary punctuation and no delimiter is safe.
Store verbatim.
Details in `docs/format/column-map.md` under column O.

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
