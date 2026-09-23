# Column definition map

Every column of `InterNACHI Residential -2026-09-22.xls`, the Spectora **Export HTML Text**
export committed to this repo.

**All figures below were measured from that file**, not taken from documentation. The file is
42 columns (A–AP) × 392 data rows, header on row 1, one worksheet named `Sheet1`. Despite the
`.xls` extension the file is OOXML: magic bytes `PK\x03\x04`, no `sharedStrings.xml`, all
values inline.

**One row is one comment.** Section and item names repeat on every row, so the hierarchy is
implied by repetition rather than nesting.

Measured structure: **13 sections, 69 items, 392 comments.** Comment types split defect 302,
info 78, limit 12.

---

## Reading order for the three name columns

Spectora's nesting, in its own glossary's words, is Template → Section ("Column 1") → Item
("Column 2") → Comment ("Column 3"). The export has no template row, so the template name
survives only in the filename.

---

## The columns

### A — `Section Name`
Top-level grouping. Plain text. 100% filled, 13 distinct.
**Double entity-encoded**, see the encoding section below.
Largest sections by comment count: Doors, Windows & Interior (54), Exterior (50), Plumbing (43).
→ Maps to `section.name`. **Section identity is the contiguous block of rows, not the string.**
Spectora allows duplicate section names, and two adjacent ones export as a single block. See
`EDA-FINDINGS.md`, "Duplicate names".

Every new section Spectora creates comes with an automatic `General` item. That is why
`General` recurs under eight stock sections, and an unused one never exports because it has no
comments.

### B — `Item Name`
Second-level grouping, scoped to its section. Plain text. 100% filled, **61 distinct names
resolving to 69 items**, because some names repeat across sections. `General` alone appears
under 8 different sections.
**Double entity-encoded.**
→ Maps to `item.name`. **Item identity is the contiguous block within its section block, never
the name alone.** Duplicate item names are allowed inside one section; adjacent ones merge in the
export with no trace.

### Name columns: special characters are accepted

Spectora accepts `&`, `<`, `>` and `"` in section, item and comment names, and the editor
displays them correctly. **The export does not reproduce them faithfully.**

**Finding: the HTML export auto-closes anything that looks like an HTML tag inside a name.**
Typed in the UI, and shown correctly there, versus what the export contains:

| Typed | HTML export | Plain export |
| --- | --- | --- |
| `ZZ Probe & Test <x>` | `ZZ Probe & Test <x></x>` | `ZZ Probe & Test ` |
| `Item & <angle> "quote"` | `Item & <angle> "quote"</angle>` | `Item &  "quote"` |
| `Smith & Sons <test> "quoted"` | `Smith & Sons <test> "quoted"</test>` | `Smith & Sons  "quoted"` |

The names are being run through an HTML parser and re-serialised on the way out: the HTML
variant appends a closing tag, the Plain variant strips the tag and leaves its surrounding
whitespace. Only `<` immediately followed by a letter triggers it, since that is what an HTML
parser treats as a tag; `<50`, `< 50` and `<18 in` are text and pass through. The `</x>` cannot
be removed safely, because the importer cannot know whether the customer typed it. Store the name
exactly as exported. This is a stated limitation of the export, not something the importer
detects.

**Encoding depth differs by export variant, in every text column.** Measured on raw XML:

| Column | HTML export | Plain export |
| --- | --- | --- |
| A, B, C names | `&` double (`&amp;amp;`); `<` `>` single; `"` bare | `&` single; tags stripped |
| D Comment Text | `&` double; tags single-encoded, so real markup after XML decode | `&` single; all tags removed |
| G choices | single | single |

**One decoding rule works for both variants, with no detection.** After XML parsing, decode
entities in the name columns exactly once with a **strict** decoder, one that only decodes
entities terminated by a semicolon (`&amp;`, `&lt;`, `&#39;`). Tested:

| After XML parse | Standard HTML decode | Strict decode |
| --- | --- | --- |
| `Siding, Flashing &amp; Trim` (HTML export) | `Siding, Flashing & Trim` | `Siding, Flashing & Trim` |
| `Siding, Flashing & Trim` (Plain export) | `Siding, Flashing & Trim` | `Siding, Flashing & Trim` |
| `Heat &not working` (typed) | `Heat ¬ working` **corrupted** | `Heat &not working` |
| `Smith&copy Co` (typed) | `Smith© Co` **corrupted** | `Smith&copy Co` |

A standard decoder expands legacy entities with no semicolon, so it silently rewrites text a
customer typed. The strict one does not, and it is a no-op on the Plain export, so the parser
needs no variant branch. `Comment Text` is not decoded at all; it is HTML and is rendered as
HTML. In a TypeScript stack, the `entities` package provides a strict decoding mode; no regex
needed.

### C — `Comment Name`
The label shown in Spectora's comment list. Plain text. 100% filled, 334 distinct. Repeats are
intentional and scoped to their item: `Improper Installation` appears 10 times, `Material` 8.
No ampersands occur in either file examined, so its encoding depth is untested; treat it as A
and B. 11 values carry leading or trailing whitespace.
**Not unique within an item:** `Fireplace / Damper Doors` holds two comments both named
`Damper Inoperable`.
→ Maps to `comment.name`. **Comment identity must be a surrogate key plus row position, never
the name.**

### D — `Comment Text`
**This is the field the Spectora UI labels "Default Text"**, the comment's default narrative
body. It is *not* the comment's label; that is column C.
Filled on 309 of 392 rows (78.8%). The 83 blanks are legitimate: multiple-choice informational
comments carry their content in column G and have no body.
Content is **HTML**: 244 `<p>`, 43 `<a>`, 1 `<strong>`, 1 `<div>`. 111 populated bodies contain
no markup at all.
→ Maps to `comment.body_html`. Store the string, render as HTML, never rewrite it.

### E — `Comment Type (info, limit, defect)`
Enum, 100% filled, exactly 3 values: `defect` 302, `info` 78, `limit` 12.
Maps one-to-one onto Spectora's UI buckets Informational / Limitations / Deficiencies, and onto
Hive Inspect's documented Information / Limitations / Defects or deficiencies. The mapping is
the identity.
→ Maps to `comment.type`. Store as an enum, not free text.

### F — `Category (-1: Low, 0: Med, 1: High)`
Severity, **defect rows only**. Filled on 302 of 392 (77.0%), which is exactly the defect count.
Blank on all 78 info and all 12 limit rows. Observed values `0` (281) and `1` (21) in the stock
file; `-1` confirmed real in the second export after a comment was set to Low.
**The UI control is three icon buttons**, shown only when creating or editing a Deficiency:
a wrench, a minus-in-circle, and a warning triangle. Three buttons, three documented values,
so the mapping is positional and is now **confirmed by export: wrench = `-1`, minus-in-circle
= `0`, warning triangle = `1`.** Confirmed by opening the create dialog for each
type: Informational and Limitation comments show neither this control nor Recommendation, and
their dialogs are otherwise identical, which is why the column is blank on exactly those rows.
All seven Answer Formats are offered on all three comment types.
→ Maps to `comment.severity`, nullable. Do not render a severity chip on info or limit
comments.

### G — `Multiple Choice Options (comma-separated)`
The UI's **Answer Choices**. Filled on 72 of 392 (18.4%), exactly matching the 72 `checkbox`
rows in column K. Comma-separated list, e.g. `Wood, Glass, Steel, Hollow Core, Single Pane,
Fiberglass`.
**Single entity-encoded**, unlike A, B and D. See below.

**A choice can never contain a comma, so splitting on comma is safe.** Verified in the UI:
Spectora splits the field on every comma *at input time*. Typing
`Smith, John, 1,000 sq ft, He said "no", Plain` into Answer Choices produced six choices, not
five: `Smith`, `John`, `1`, `000 sq ft`, `He said "no"`, `Plain`. The value `1,000 sq ft` was
destroyed on entry. There is no escape syntax and the UI offers no way to enter a literal comma.

Two consequences. `split(',')` on column G is correct, not a guess. And this is a **data-entry
trap in Spectora itself**: an inspector typing a thousands separator silently gets two wrong
choices, and the export faithfully carries the damage. The importer cannot tell a damaged
choice from a real one, so it stores what it gets; this is a limitation to state in NOTES.md,
not a pattern to detect.

Quotes survive intact: `He said "no"` round-tripped through the UI unchanged.
→ Maps to `comment.choices[]`. Split on comma, trim. Values can contain `&`, quotes and
parentheses, as in `Knob & Tube` and `Fahrenheit (F)`.

### H — `Unit Type Options (numeric answers only, comma-separated)`
Filled on 3 rows only (0.8%): `Fahrenheit (F), Celsius (C)`, `SEER`, `gallons`. Applies to
numeric answer types.

Confirmed in the UI: both the `Number` and `Numeric Range` formats expose a field labelled
"Unit Type Choices (comma-separated)" with placeholder `kg, lbs`. The `Multiple Choices` format
exposes a differently-labelled field, "Answer Choices (comma-separated)", placeholder
`Concrete, Wood, Metal`, which is column G. Two comma-separated fields, two formats, two columns.
Note the first observed value, `Fahrenheit (F), Celsius (C)`, contains parentheses but no comma
inside a unit.
→ Optional. Map to `comment.unit_options[]` or record as unsupported.

### I — `Recommendation (from list)`
Filled on 4 rows (1.0%). Lowercase slugs from a fixed Spectora list: `pro` ×3, `monitor` ×1,
plus `cabinet` observed in the second export.

**Deficiency-only, and a long alphabetical list.** The Recommendation dropdown appears in the
Deficiency create dialog and not in the Informational one. Its first entries are
`No Recommendation`, `Appliance Repair`, `Builder`, `Cabinet Contractor`, `Carpentry Contractor`,
`Carpet Cleaner`, `Chimney Repair Contractor`, `Chimney Sweep`, `Cleaning Service`, and it
scrolls well beyond those: it is a full trade directory.

**Slugs are not derivable from labels.** Observed pairs from `probe-html.xls`:

| UI label | Export slug |
| --- | --- |
| Cabinet Contractor | `cabinet` |
| Appliance Repair | `appliance` |
| Carpet Cleaner | `carpetcleaner` |
| No Recommendation | *(blank; cell absent)* |
| *(system default)* | `pro` |

First word for two, both words concatenated for the third. There is no rule. **Derive nothing,
store the slug verbatim, treat the vocabulary as open, and display it as it is.** No lookup
table: one built from the slugs seen so far would be a list of this account's choices, not
Spectora's.

**`pro` is a system default applied to every non-deficiency comment.** Every Informational and
Limitation probe comment carries `pro`, although their dialogs show no Recommendation control.
It is the only slug that appears on `info` and `limit` rows. This explains the `pro` on
`Inspection Details / General / Temperature` in the stock file.

Note one observed `pro` sits on an Informational row (`Inspection Details / General /
Temperature`), so the field can carry a value even where the current UI would not offer it.
The vocabulary is not documented, so treat unseen values as opaque.
→ Map verbatim to `comment.recommendation`, or declare unsupported. Do not invent a
display label for a slug you have not seen.

### J — `Order (w/i item)`
Integer, 100% filled, values 0–12 in this file. **The name is misleading: the counter is scoped
per comment type within the item, not per item.** Keyed on (section, item) only 27 of 69 groups
run consecutively from 0; keyed on (section, item, type) 110 of 115 do.

**It is a sort hint, not an index.** On a second export of a different template only 25 of 220
type-groups were dense, 120 contained duplicate values, and the column was often constant: all
ten defects under `Roof / Coverings` carried `Order = 5`.
→ Sort by this **within each type group**, **tie-break on row position**, then render groups as
Informational, Limitations, Deficiencies. Declare ordering as best-effort in the import report.
See `EDA-FINDINGS.md` section 3.

### K — `Answer Type (boolean, checkbox, date, number, range, text)`
Enum, 100% filled. Observed: `boolean` 315, `checkbox` 72, `number` 4, `text` 1. The documented
values `date` and `range` do not occur in this template.
Rendered in Spectora's UI as the small icon beside the comment name; `number` shows `#`,
`checkbox` shows a list glyph.

**The UI labels do not match the export values, and two of them are inverted.** Spectora's
"Answer Format" dropdown offers seven options; the header documents six values. Mapping, with
confidence noted:

| UI "Answer Format" | Export value | Type-specific field in the UI | Confidence |
| --- | --- | --- | --- |
| `Checkbox (i.e. Yes/No, Present/Not Present)` | **`boolean`** | "Default to checked?" on edit | strong |
| `Multiple Choices (i.e. checkboxes)` | **`checkbox`** | "Answer Choices (comma-separated)" | strong |
| `Date` | `date` | none | **confirmed by export** |
| `Number` | `number` | "Unit Type Choices (comma-separated)" | **confirmed by export** |
| `Numeric Range` | `range` | "Unit Type Choices (comma-separated)" | **confirmed by export** |
| `Signature` | **`signature`** | none | **confirmed by export** |
| `Text` | `text` | none | **confirmed by export** |

**Which default fields each format exposes**, confirmed by opening one comment of every format:

| UI format | Choices field | Default Value | Default Value 2 | Comment-list icon |
| --- | --- | --- | --- | --- |
| Checkbox (Yes/No) | none | "Default to checked?" tick | no | green tick |
| Multiple Choices | Answer Choices | **no field at all** | no | green list |
| Number | Unit Type Choices | yes | no | green `#` |
| Numeric Range | Unit Type Choices | yes | **yes** | green `#` |
| Text | none | yes | no | green `A` |
| Date | none | **no field at all** | no | green calendar |
| Signature | none | **no field at all** | no | green pencil |

So column M `Default Value 2` is reachable only from `Numeric Range`, and column L `Default
Value` is unreachable for Multiple Choices, Date and Signature. The icon does not identify the
format uniquely: `#` is shared by Number and Numeric Range.

The inversion is the trap. The export value `checkbox` is **not** the UI's "Checkbox"; it is the
UI's "Multiple Choices". This is confirmed by the measured invariant that `Multiple Choice
Options` is populated on exactly the 72 `checkbox` rows and no others, and the UI shows the
"Answer Choices" field only for the "Multiple Choices" format. Anyone mapping the UI's own
vocabulary onto the export will silently swap two formats.

**`Signature` exports as `signature`, a seventh value the column header does not list.** All
seven are now observed in a real export (`probe-html.xls`). The header's own enumeration is
incomplete, which is the concrete case the "text, not a Postgres enum" decision was made for.
Treat any eighth value the same way: `UNEXPECTED_VALUE` issue, stored verbatim.
→ Maps to `comment.answer_type`. Accept at least seven values, and do not reject an eighth.

### L — `Default Value`
Filled on 1 row only (0.3%), value `true`.

**This is the UI's per-format default, and its meaning depends on `Answer Type`.** Observed in
`probe-html.xls`: `true` for a `boolean` with "Default to checked?" ticked, `10` for a `range`,
`42` for a `number`, `hello` for a `text`. Empty for `date`, `signature` and `checkbox`, whose
edit views have no default field at all.

**Boolean defaults serialise inconsistently.** Across the file the `boolean` rows carry
`true` ×2, **`f` ×1** (row 263, `Damper Inoperable`) and blank ×317. Two spellings of a boolean
in one column, presumably a stringified `true` from one code path and a Postgres-style `f` from
another. Any importer that coerces this column to a boolean on `== 'true'` will read `f` as
false by accident and any future `t` as false by mistake. Keep it as text.
→ Store verbatim as text. Do not coerce to boolean; the same column holds a number for
`number`, a date for `date`, and a range floor for `range`.

### M — `Default Value 2 (for "range" types)`
**Empty on all 392 rows** of the stock file. Observed as `20` on the one `range` comment in
`probe-html.xls`, alongside `Default Value` `10`. The range's upper bound. Only reachable from
the Numeric Range format.

### N — `Default Unit Type (for "number" and "range" types)`
**Empty on all 392 rows, and no control for it exists in the UI.** The Number and Numeric Range
edit views offer "Unit Type Choices" (column H) but no way to pick a default unit. Remained empty
on the probe `range` and `number` comments even with unit choices filled in. Same class as R, S
and T: expect it permanently empty for UI-authored templates.

### O — `Default Location`
**Empty on all 392 rows** of the stock file. Populated in the second export.

**This is a multi-select, flattened into one string.** Spectora's Location picker is a grid of
account-level tags in three groups: level (1st Floor, 2nd Floor, 3rd Floor, Basement,
Crawlspace, Attic, Master), direction (North, South, West, East, Northwest, Northeast,
Southwest, Southeast) and room (Kitchen, Dining Room, Living Room, Bedroom, Bathroom, Garage).
Selecting tags composes them into a single string, **space-joined, with a leading space**, in
the picker's own column order rather than click order. Selecting every tag produced:

```
" 1st Floor 2nd Floor 3rd Floor Basement Crawlspace Attic Master North South West East Northwest Northeast Southwest Southeast Kitchen Dining Room Living Room Bedroom Bathroom Garage,"
```

The earlier observed value `' 1st Floor West Northwest Bedroom'` is therefore **four tags**, not
one location.

**The encoding is unparseable by construction.** The delimiter is a space, and tag labels
contain spaces (`1st Floor`, `Dining Room`, `Living Room`). `1st Floor 2nd Floor` cannot be
split back into its tags without already knowing the tag vocabulary, and that vocabulary is an
account-level setting under Settings > Location Tags that is **not in the export**.

**Custom tags can be any string, including punctuation.** To prove it, a tag whose label is a
bare comma was added to this account's Location Tags and selected; it sits after Garage, renders
in the picker as a dot-sized glyph, and is why the composed string ends in `Garage,`. It is not a
Spectora default. The point stands regardless of who added it: a real customer's account can hold
any label, so no delimiter is safe for decomposing this field, and a tokeniser that splits on
commas or spaces will mis-handle real data.

-> Maps to `comment.default_location` as a **verbatim string**. Do not model it as a tag array.
Tokenising against the 21 stock labels is possible as a best-effort display aid, flagged as
such, and will fail on any account with custom tags. Trim for display only; store the leading
space.

This is the second field in the format that is lossy by design. `Multiple Choice Options` uses
a comma delimiter with no escaping; `Default Location` uses a space delimiter with values that
contain spaces.


### P — `Default Estimate Min` — degenerate
`10` on **all 392 rows**. A system default, not customer data.

### Q — `Default Estimate Max` — degenerate
`1000` on **all 392 rows**. A system default, not customer data.

### R — `Locked`
**Empty on all 392 rows, and no control for it exists anywhere in the comment UI.**
Checked the create dialog and the edit view for all seven answer formats, and the Deficiency
dialog. Likely legacy or API-only. Expect it to stay empty for any template authored through the
web UI. Documented as `true`/`false`.

### S — `Simple Format`
**Empty on all 392 rows, and no control for it exists anywhere in the comment UI.**
Checked the create dialog and the edit view for all seven answer formats, and the Deficiency
dialog. Likely legacy or API-only. Expect it to stay empty for any template authored through the
web UI. Semantics undocumented.

### T — `Disable Photos`
**Empty on all 392 rows, and no control for it exists anywhere in the comment UI.**
Checked the create dialog and the edit view for all seven answer formats, and the Deficiency
dialog. Likely legacy or API-only. Expect it to stay empty for any template authored through the
web UI. Documented as `true`/`false`.

### U — `Uses` — degenerate
`0` on **all 392 rows**. Presumably a usage counter, reset or unused on a stock template.

### V–AO — `Default Photo 1..10` and `Default Photo N Caption`
Twenty columns, interleaved photo then caption. **Every one empty on all 392 rows.**
These are **Spectora CDN URLs**, observed as
`https://cdn.spectora.com/default_photos/images/005/622/660/original/three.jpg?1790141917`, with
the caption in the adjacent column. **No image binary is carried by the export**, and the URL
dies with the customer's Spectora account. Fetch at import. See `PRESERVATION.md` section 4.

Three photos fill V, X, Z with captions in W, Y, AA, as expected. **The order is newest-first.**
Photos added as `one`, `two`, `three` exported as Photo 1 = `three`, Photo 2 = `two`, Photo 3 =
`one`. The original filename survives in the URL path; a phone upload became
`image_created_with_a_mobile_phone.png`.
Note Spectora's published import format documents only Photos 1–3; real exports emit 1–10.

### AP — `Last Modified`
Format `MM/DD/YYYY HH:MM:SS`, 24-hour, no timezone. 100% filled.

**Correction: this is a genuine per-comment modification timestamp.** An earlier version of
this document said it recorded export time. Two exports of this account taken 18 hours apart
carry **identical** values on 382 of 392 rows. The 04:32:57-04:33:05 cluster is when the stock
template was instantiated into the account, which on a freshly loaded template is every row's
last modification. The rows that differ are the ones actually saved since: the test comment at
10:46:10 and one other at 07:40:02.

Two consequences. On a stock template the column looks useless because every row shares the
load time. On a four-year-tuned template it is **the only signal in the file of which comments
the customer has actually touched and when**, which is exactly what a migration reviewer wants to
know. Model it. Also note it reflects last *save*, not last *content change*: row 12 was
re-saved with identical content and picked up a new timestamp.
-> Maps to `comment.source_last_modified`.

---

## Entity encoding, measured per column

Every text value passes through XML decoding first. What you must do *after* that differs by
column, and it is not simply "plain text versus HTML".

| Column | Raw XML | After XML parse | Correct handling |
| --- | --- | --- | --- |
| A `Section Name` | `&amp;amp;` | `&amp;` | **decode once more** → `&` |
| B `Item Name` | `&amp;amp;` | `&amp;` | **decode once more** → `&` |
| D `Comment Text` | `&amp;amp;`, `&lt;p&gt;` | `&amp;`, `<p>` | **leave as-is, render as HTML** |
| G `Multiple Choice Options` | `&amp;` | `&` | **do not decode again** |

Measured counts in this file: 107 cells in A and 145 in B contain `&amp;amp;`; column G contains
`&amp;` and never `&amp;amp;`.

Get this wrong in either direction and it fails silently. Skip the extra decode on A and B and
the inspector sees `Siding, Flashing &amp; Trim` as a heading. Apply it to D and you turn
escaped content into live markup, which corrupts the narrative and is an injection risk. Apply
it to G and `Knob & Tube` is unaffected only by luck; the general case is that G is already
correct.

---

## What is not in this file at all

The "missing from the export" bucket, evidenced rather than assumed.

- **Empty sections and empty items.** Rows are comments, so a section with no items or an item
  with no comments produces no rows and **vanishes from the export**. Confirmed: a section
  `ZZ Empty` and an item `ZZ Empty Item` were created and neither appears in either export
  variant. The customer's structure is silently truncated to whatever holds a comment.
- **The boundary between adjacent same-named sections or items.** They export as one block.
- **Template name.** No column. Survives only in the filename.
- **The Location Tags vocabulary.** Account-level under Settings > Location Tags. Only the
  composed per-comment string is exported, and it cannot be decomposed without the list.
- **Section and item ordering.** No order column above the comment level. See the finding
  below.
- **Section and item settings. Only the name is exported.** Confirmed from Spectora's own
  Add Section and Add Item dialogs, which show every field those records carry:

  | Record | Field | In the UI | In the export |
  | --- | --- | --- | --- |
  | Section | Section Name | text | **yes**, column A |
  | Section | Hide Overview Grid for this section | checkbox | no |
  | Section | Optional/Included | `Included in every report` or `Optional - add on a per-report basis` | no |
  | Section | Icon | one of about 40 glyphs, or `No Icon` | no |
  | Section | Standards of Practice | rich-text editor, shown in the report's Standards tab | no |
  | Section | Reminders | rich-text editor, shown in the mobile app | no |
  | Item | Item Name | text | **yes**, column B |
  | Item | Info Item (No ratings/defects/grid row) | checkbox | no |
  | Item | Optional/Included | same two options as sections | no |
  | Item | Reminders | rich-text editor, shown in the mobile app | no |

  So the export carries one of six section fields and one of four item fields. Two of the
  missing ones are real authored content, not settings. Standards of Practice and Reminders are
  free-form rich text the inspector wrote, and Standards of Practice is printed in every report.
  The file gives no way to tell whether a section had any, so the import report can only say:
  "if you used these fields, they did not come across; re-enter them." Do not infer Info Item
  from a section of all-informational comments; the flag is independent.
- **Attachments.** The UI has an Attachments panel per template; no column exists.
- **All template-level settings**: Header Text, Display Options, Item Ratings configuration,
  Defect Categories, Reinspection Categories, Reinspection Header Text.
- **Image and video binaries.**
- **Not missing: embedded videos.** An earlier version of this list said the export strips
  `<iframe>` embeds. The round-trip test disproved that; a Vimeo embed authored in the editor
  exported intact. The one empty `youtube-embed-wrapper` div in the stock template is an
  artifact of that template, not export loss.

### Finding: item display order is not recoverable

Two independent exports of this template, taken two days apart from different accounts, both
order `Exterior` items as `… Eaves, Soffits & Fascia, Walkways Patios & Driveways, Vegetation
Grading Drainage & Retaining Walls`. The Spectora UI displays the last two the other way round.

Section order matches the UI exactly in both files. Item order does not, and both files agree
with each other, so this is a property of the export rather than drift between accounts.

**Consequence:** first-appearance order reproduces sections faithfully but items only
approximately. Say so in the import report rather than presenting a reordered template as a
faithful copy.

---

## Suggested target schema

```
template   id, name (from filename), source_file, imported_at
section    id, template_id, name, position            -- position = first appearance
item       id, section_id, name, position             -- identity is (section, name)
comment    id, item_id, name, body_html, type, severity,
           answer_type, choices[], unit_options[], recommendation,
           order_in_type, position
import_issue  id, template_id, kind, column, row, detail
```

`import_issue.kind` carries the two buckets the assignment asks you to keep apart:
`MISSING_FROM_EXPORT` for everything in the section above, and `NOT_MODELLED` for columns you
read but deliberately do not store. Never merge them.
