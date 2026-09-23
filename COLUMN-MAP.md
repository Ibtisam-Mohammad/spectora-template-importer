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
→ Maps to `section.name`. Section identity is this string.

### B — `Item Name`
Second-level grouping, scoped to its section. Plain text. 100% filled, **61 distinct names
resolving to 69 items**, because some names repeat across sections. `General` alone appears
under 8 different sections.
**Double entity-encoded.**
→ Maps to `item.name`. **Item identity is (Section Name, Item Name), never the name alone.**

### Name columns: special characters are accepted

Spectora accepts `&`, `<`, `>` and `"` in section, item and comment names. Verified by creating
a section `ZZ Probe & Test <x>`, an item `Item & <angle> "quote"` and a comment
`Smith & Sons <test> "quoted"`, all of which saved and display correctly. Their encoding depth in
the export is pending a round trip.

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
so the mapping to `-1` / `0` / `1` is positional. Confirmed by opening the create dialog for each
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
choices, and the export faithfully carries the damage. Worth surfacing in the import report as an
observation, not an error, when a choice list contains a bare numeric fragment.

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
scrolls well beyond those: it is a full trade directory. `Cabinet Contractor` is the source of
the `cabinet` slug, which suggests first-word-lowercased, but `Chimney Repair Contractor` and
`Chimney Sweep` would collide under that rule, so the real key is something else or Spectora
tolerates collisions. Either way: **derive nothing, store the slug verbatim, and treat the
vocabulary as open.** A lookup table from slug to display label is a convenience seeded from
observed values, never a precondition for import, and an unknown slug displays as itself.

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
| `Date` | `date` | none | assumed |
| `Number` | `number` | "Unit Type Choices (comma-separated)" | strong |
| `Numeric Range` | `range` | "Unit Type Choices (comma-separated)" | assumed |
| `Signature` | **unknown** | none | **untested** |
| `Text` | `text` | none | assumed |

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

**`Signature` is a seventh format with no documented export value.** It appears in the dropdown
but not in the column header's list of six. Until observed, treat any unknown `Answer Type` as
an `UNEXPECTED_VALUE` import issue and store it verbatim; this is exactly the case the "text,
not a Postgres enum" decision was made for.
→ Maps to `comment.answer_type`. Accept at least seven values, and do not reject an eighth.

### L — `Default Value`
Filled on 1 row only (0.3%), value `true`.

**This is the UI's per-format default, and its meaning depends on `Answer Type`.** For the
`Checkbox (Yes/No)` format the edit view shows a single "Default to checked?" tick, which is the
source of the lone `true`. The defaults for Number, Numeric Range, Date and Text have not been
observed and are not present in the create dialog, so they are presumably on the edit view of a
comment of that format.
→ Store verbatim as text. Do not coerce to boolean; the same column holds a number for
`number`, a date for `date`, and a range floor for `range`.

### M — `Default Value 2 (for "range" types)`
**Empty on all 392 rows.** Only meaningful for `range`, which this template never uses.

### N — `Default Unit Type (for "number" and "range" types)`
**Empty on all 392 rows.**

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
`https://cdn.spectora.com/default_photos/images/.../original/<name>.png?<cachebuster>`, with the
caption in the adjacent column. **No image binary is carried by the export**, and the URL dies
with the customer's Spectora account. Fetch at import. See `PRESERVATION.md` section 4.
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

- **Template name.** No column. Survives only in the filename.
- **The Location Tags vocabulary.** Account-level under Settings > Location Tags. Only the
  composed per-comment string is exported, and it cannot be decomposed without the list.
- **Section and item ordering.** No order column above the comment level. See the finding
  below.
- **Section and item attributes**: icons, optional or required flags, Standards of Practice
  references, reminders, info-only flags, overview-grid participation. The Spectora UI shows a
  distinct icon per section; none of it is in the file.
- **Attachments.** The UI has an Attachments panel per template; no column exists.
- **All template-level settings**: Header Text, Display Options, Item Ratings configuration,
  Defect Categories, Reinspection Categories, Reinspection Header Text.
- **Image and video binaries.**
- **Embedded videos, even as references.** The `<iframe>` is stripped from `Comment Text`; only
  an empty `youtube-embed-wrapper` div survives. One occurrence here, seven in Room-by-Room.

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
