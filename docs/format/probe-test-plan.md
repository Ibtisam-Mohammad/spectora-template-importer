# Remaining unknowns, and the one session that closes them

> **Status after `probe-html.xls` and `probe-plain.xls`: every item in section A is closed, and
> every item in section B except B4 (`Uses`, needs a published report). Results are recorded
> inline below and in `docs/format/column-map.md`, `docs/format/eda-findings.md` and `docs/design/preservation.md`.
> Every documented claim is re-asserted by `tools/verify_claims.py probe-html.xls`: 75/75 pass.**

Everything verified so far comes from three real exports and one round-trip. What follows is
what is still unobserved, ranked by whether it changes code or only fills in the map. Each item
names the exact edit to make in Spectora. Make all of them in one session on a handful of
throwaway comments, then export **twice**: once as HTML Text, once as Plain Text.

---

## A. Changes parser or model. Must test.

### A1. Do empty sections and empty items export at all? — **CLOSED, no.** `ZZ Empty` and `ZZ Empty Item` are absent from both exports.
Rows are comments. A section with no items, or an item with no comments, produces zero rows.
If so, the export cannot represent them and the customer's structure is silently truncated.
**Test:** add one new section with no items, and one new item under an existing section with no
comments. Export. Look for them.
**If absent:** `MISSING_FROM_EXPORT`, and the import report must say "sections and items that
contain no comments cannot be exported by Spectora".

### A2. Can a multiple-choice option contain a comma? — **CLOSED, no**
Spectora splits Answer Choices on every comma at input time. `1,000 sq ft` became two choices,
`1` and `000 sq ft`. No escape syntax exists. `split(',')` on column G is therefore correct.
Quotes survive. Details in `docs/format/column-map.md` under column G.

### A3b. What does the `Signature` answer format export as? — **CLOSED: `signature`.**
Spectora's Answer Format dropdown has seven options; the column header documents six values.
`Signature` has no known export value.
**Test:** create one comment with Answer Format `Signature`. Export.
**Outcome decides:** whether the answer-type vocabulary is open-ended, and confirms the
"store unknown enums verbatim" decision.

### A3. What do `range` and `date` answer types look like? — **CLOSED.** `range`: L=`10`, M=`20`, H=`inches, feet`, N empty. `date`: L empty, no default field exists. N has no UI control.
Never observed. They are the only documented answer types not yet seen, and `range` is the only
consumer of column M `Default Value 2` and one of two consumers of column N `Default Unit Type`.
**Test:** set one comment to `range` with Default Value 10, Default Value 2 50, Default Unit Type
`inches`. Set another to `date` with a default date chosen. Export.
**Outcome decides:** the type and format of L, M, N, and whether `date` has a serialised format
that needs parsing.

### A4. Encoding depth of `Comment Name`, and non-ampersand characters everywhere. — **CLOSED.** C matches A and B. `&` double, `<>` single, `"` bare, in the HTML export. Names containing `<letter` are auto-closed on export.
Columns A, B, D are double-encoded; G is single. Column C has never contained an ampersand, so
its depth is untested. Characters other than `&` are untested in every column.
**Test:** rename one comment to `Smith & Sons <test> "quoted"`, one item to `Attic & Eaves`,
one section to `Roof <main>`. Export. Inspect raw XML.
**Outcome decides:** the per-column decode table, and whether `<`, `>`, `"` are entity-encoded
consistently with `&`.

### A5. The Plain Text export. — **CLOSED.** Differs in A, B, C and D. Single-encodes names. Drops all URLs and table structure. See `docs/format/eda-findings.md` 6a.
Never seen. The detection heuristic for "you exported the wrong variant" is currently "no row
contains markup", which is a guess.
**Test:** export the same template as Plain Text. Diff against the HTML export.
**Outcome decides:** whether the only difference is column D, what plain-text D looks like
(stripped tags? converted to newlines? entities?), and whether any other column differs.

---

## B. Fills in the map. Worth doing, does not change code.

### B1. `Locked`, `Disable Photos`, `Simple Format` — **CLOSED, not in the UI**
No control for any of the three exists in the comment create dialog or edit view, across all
seven answer formats, nor in the Deficiency dialog. Legacy or API-only. Expect them permanently
empty for UI-authored templates.

### B2. Multiple default photos. — **CLOSED.** Fill V, X, Z in order, captions W, Y, AA. **Newest first.**
Only `Default Photo 1` has been observed.
**Test:** add three photos with captions to one comment. Export. Confirm they fill V, X, Z in
order with captions in W, Y, AA, and that the URL pattern is stable.

### B3. `Recommendation` vocabulary — **CLOSED.** `carpetcleaner`, `appliance`, `cabinet`; No Recommendation is blank; `pro` is the system default on non-deficiency rows. Not derivable.
Deficiency-only. List begins `No Recommendation`, `Appliance Repair`, `Builder`,
`Cabinet Contractor`, `Carpentry Contractor`, `Carpet Cleaner` and scrolls further.
`Cabinet Contractor` → `cabinet`, so the slug looks like the first word lowercased.
**Remaining test:** set three deficiencies to three different recommendations and export, to
confirm the derivation rather than assuming it.

### B4. `Uses`.
`0` on every row. Presumably increments when a comment is used in a published report.
**Test:** if a sample inspection is run in Spectora anyway, publish it using two or three
comments, then export. See whether `Uses` moved.

### B5. `Default Value` for `number`, `text` and `checkbox`. — **CLOSED.** `42`, `hello`, and no field for Multiple Choices.
Only observed once, as `true` on a boolean. Unknown whether a checkbox default is one choice, a
list, or an index.
**Test:** set a default on one comment of each type. Export.

### B6. Item reorder. — **CLOSED.** Export tracked the UI drag. Still no column to verify it from the file.
Item order differed between two exports with no edits. Unknown whether export order is random,
creation-order, or tracks the UI after some trigger.
**Test:** drag two items to swap them in the UI. Export twice, a few minutes apart. Compare item
order in both to the UI.
**Outcome:** either "export order is unrelated to UI order" or "export order tracks UI order but
lags", which changes the wording of the import warning, not the code.

---

## C. Already known to be unrecoverable from the export. No test can help.

- Section and item display order (no column; confirmed unstable across exports).
- Section icons, optional/required flags, Standards of Practice references, reminders, info-only
  flags, overview-grid membership.
- Template-level settings: Header Text, Display Options, Item Ratings configuration, Defect
  Categories, Reinspection Categories and Header Text.
- The Location Tags vocabulary. Only the composed per-comment string is exported.
- Attachments.
- Image binaries. Photo columns are URLs into `cdn.spectora.com`.
- The template's own name. Filename only.

---

## D. What the map already has, for contrast

Verified from real files and one round-trip: file mechanics (OOXML in `.xls`, one sheet, 42
columns, sparse cells, `t="str"`), the three-level hierarchy and its identity rules, per-column
entity depth for A, B, D and G, full HTML round-trip fidelity including Froala video and table
markup, all three `Comment Type` values, all three `Category` values, four of six `Answer Type`
values, `Multiple Choice Options` format, `Order (w/i item)` semantics, `Last Modified` as a real
per-comment save time, `Default Location` as a flattened multi-select, `Default Photo 1` URL
format, and the non-determinism of item order.

**After section A is done, the parser has no remaining unknowns.** Section B is for the column
map and the walkthrough. Section C is the missing-from-export list, already written.
