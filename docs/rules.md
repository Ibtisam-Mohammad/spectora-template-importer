# Rules

Every rule the importer follows about Spectora's export format, in one place. This file is the
single source of truth for format behaviour. The documents under `docs/format/` and
`docs/design/` are the evidence log that these rules were derived from; where they disagree
with this file, this file wins.

**Rule zero.** The importer may depend on Spectora's file *format*. It must never depend on a
*template's content*: no section, item, comment or value names, no pattern matching on text an
inspector typed, and no lookup tables built from what one template happened to contain.

**How the rules are checked.** Tests declare the rules they verify with
`@pytest.mark.rule("S2")`. A meta-test fails if a rule below has no test, if a test cites an ID
that is not below, or if an ID appears twice. Rules in the File, Text, Structure, Order,
Values, Detection and HTML groups must be covered by a unit test that needs no database. Run
`pytest --rules-report` to regenerate `docs/rules-status.md`, which lists each rule with its
tests and their result. A tag records that a test claims a rule; the test's assertions are what
prove it.

Each rule gives its evidence and the module that implements it.

---

## File

- **F1** Identify an upload by its content, an OOXML zip signature, never by its `.xls` extension.
  Evidence: `docs/format/spectora-format.md`, "The file, verified". Module: `app/spectora/workbook.py`.
- **F2** Treat every uploaded file as hostile: parse XML with `defusedxml`, and cap the zip's entry count and total uncompressed size, refusing rather than expanding past the caps.
  Evidence: the upload is customer-supplied. Module: `app/spectora/workbook.py`.
- **F3** Find the worksheet through `workbook.xml` and its relationships, not a hard-coded path. If there is more than one sheet, raise an issue and read the first.
  Evidence: every export seen has one sheet, `Sheet1`; a hard-coded path would be template knowledge. Module: `app/spectora/workbook.py`.
- **F4** Locate every cell by its `r` reference. An absent `<c>` and a present `<c>` with no value both mean empty, and the difference is kept in the raw row.
  Evidence: `docs/format/eda-findings.md` §1; all twenty photo columns have no `<c>` at all. Module: `app/spectora/workbook.py`.
- **F5** Read string cells in every OOXML form: `t="str"`, `t="inlineStr"` and shared strings.
  Evidence: exports use `t="str"` with no shared-strings part; other writers use the other two. Module: `app/spectora/workbook.py`.
- **F6** The header is row 1. Map columns by exact header text against the 42 known headers. An unknown header raises `UNKNOWN_HEADER` and its values stay in the source row. A missing header raises `MISSING_HEADER`. Refuse the file only when Section Name or Item Name is missing, because no tree can be built without them.
  Evidence: `docs/format/spectora-format.md`, "The 42 headers". Module: `app/spectora/columns.py`, `app/spectora/detect.py`.
- **F7** Keep every cell of every row verbatim in the source row, as strings, never cast.
  Evidence: `docs/design/preservation.md` §3. Module: `app/spectora/workbook.py`, `app/db/imports.py`.
- **F8** Never drop a row silently. A row with a blank Section Name or Item Name raises `ROW_SKIPPED` with its row number. Fully empty rows are counted.
  Evidence: the brief, "do not quietly drop or rewrite it". Module: `app/spectora/parse.py`.
- **F9** Cap an upload at 4 MB by reading one byte past the limit, and answer with a clear message rather than the platform's own error.
  Evidence: Vercel rejects request bodies over 4.5 MB with its own error page. Module: `app/web/routes/library.py`.

## Text

- **T1** Decode entities in section, item and comment names exactly once, strictly: only semicolon-terminated entities are decoded, and `html.unescape` is never used.
  Evidence: `docs/format/column-map.md`, "Name columns"; `html.unescape` turns `Heat &not working` into `Heat ¬ working`. Module: `app/spectora/columns.py`.
- **T2** Store Comment Text byte-for-byte as it comes out of XML parsing: never entity-decoded, trimmed or whitespace-normalised.
  Evidence: `docs/format/column-map.md`, column D; bodies carry CR, LF and U+00A0. Module: `app/spectora/parse.py`.
- **T3** Split Multiple Choice Options and Unit Type Options on commas and trim each item. No entity decoding. The raw string stays in the source row.
  Evidence: `docs/format/column-map.md`, column G; Spectora splits choices on every comma at input time, so no choice can contain one. Module: `app/spectora/columns.py`.
- **T4** Store every other value exactly as parsed and never trim it. Default Location keeps its leading space.
  Evidence: `docs/format/column-map.md`, column O. Module: `app/spectora/parse.py`.
- **T5** Store export artefacts in names, such as the closing tag Spectora appends to `<x>`, as exported. Never repair them.
  Evidence: `docs/format/column-map.md`, "Name columns"; the importer cannot know what the inspector typed. Module: `app/spectora/parse.py`.

## Structure

- **S1** One row is one comment.
  Evidence: `docs/format/spectora-format.md`, "The file, verified". Module: `app/spectora/parse.py`.
- **S2** A section is a contiguous block of rows sharing a Section Name. A new block starts a new section even when the name repeats.
  Evidence: `docs/format/eda-findings.md`, "Duplicate names". Module: `app/spectora/parse.py`.
- **S3** An item is a contiguous block of rows sharing an Item Name within its section block, under the same rule.
  Evidence: `docs/format/eda-findings.md`, "Duplicate names"; Room-by-Room has 62 item names across 136 items. Module: `app/spectora/parse.py`.
- **S4** Comments are identified by surrogate keys. Every row becomes a comment, including same-named comments in one item.
  Evidence: `Fireplace / Damper Doors` holds two comments named `Damper Inoperable`. Module: `app/spectora/parse.py`.
- **S5** The template name is the uploaded file name without its extension, and it can be edited.
  Evidence: the export has no template-name column. Module: `app/spectora/parse.py`.
- **S6** When an item name recurs as a separate block inside one section block, raise `MERGED_SECTIONS_SUSPECTED` naming the section and items. Never split the section automatically.
  Evidence: `docs/format/eda-findings.md`, "Duplicate names", measured on `probe-duplicate.xls`. Module: `app/spectora/checks.py`.

## Order

- **O1** Sections take block order. Items take block order within their section. The report states that item order is best-effort.
  Evidence: `docs/format/eda-findings.md` §3. Module: `app/spectora/parse.py`.
- **O2** Within an item, comments are grouped Informational, Limitations, Deficiencies, then any unknown type. Inside a group they sort numerically by Order (w/i item); ties and non-numeric values keep source-row order.
  Evidence: `docs/format/eda-findings.md` §3; the counter restarts per comment type. Module: `app/spectora/parse.py`.
- **O3** Keep the raw Order (w/i item) value.
  Evidence: `docs/design/schema.md`, Layer 2. Module: `app/spectora/parse.py`.
- **O4** Duplicate Order values within one group raise `AMBIGUOUS_ORDER` at info level.
  Evidence: Room-by-Room has duplicates in 120 of 220 groups. Module: `app/spectora/parse.py`.
- **O5** After import, position belongs to the app. Reordering edits it, and nothing re-derives it from the file.
  Evidence: `docs/design/schema.md`, Layer 2. Module: `app/db/editing.py`.

## Values

- **V1** Store Comment Type verbatim. A value outside `info`, `limit`, `defect` raises `UNEXPECTED_VALUE`, is still imported, and is shown under "Other".
  Evidence: `docs/format/column-map.md`, column E. Module: `app/spectora/parse.py`.
- **V2** Store Answer Type verbatim. Seven values are known, `signature` included. Spectora's UI labels map to export values for display and editing only; the UI's "Checkbox" is `boolean` and its "Multiple Choices" is `checkbox`.
  Evidence: `docs/format/column-map.md`, column K. Module: `app/spectora/columns.py`.
- **V3** Store Category verbatim. Show it as Low, Med or High for `-1`, `0`, `1`, and only on deficiencies.
  Evidence: `docs/format/column-map.md`, column F. Module: `app/spectora/columns.py`.
- **V4** Check the two measured invariants and report violations as `INVARIANT_VIOLATED`; never enforce them. Category is present if and only if the comment is a deficiency. Choices are present if and only if the Answer Type is `checkbox`.
  Evidence: `docs/format/eda-findings.md` §4. Module: `app/spectora/checks.py`.
- **V5** Store Default Value and Default Value 2 as text and never coerce them.
  Evidence: `true` and `f` both occur for booleans in one file. Module: `app/spectora/parse.py`.
- **V6** Store Recommendation verbatim and display it as-is. No lookup table, and no value is special.
  Evidence: `docs/format/column-map.md`, column I; slugs are not derivable from labels. Module: `app/spectora/parse.py`.
- **V7** Store Default Location verbatim and never tokenise it.
  Evidence: `docs/format/column-map.md`, column O; tags are space-joined and contain spaces. Module: `app/spectora/parse.py`.
- **V8** Every one of the 42 known columns maps to a field. No column is dropped because the templates seen so far left it empty or constant.
  Evidence: `docs/design/schema.md`, Layer 3; Spectora's TREC export warns of locked sections and items. Module: `app/spectora/columns.py`.
- **V9** Store Last Modified as the exported text.
  Evidence: `docs/format/column-map.md`, column AP. Module: `app/spectora/parse.py`.

## Photos

- **PH1** Each Default Photo N and Caption pair with a value becomes a photo record, in export order, with its URL. Spectora writes photos newest first.
  Evidence: `docs/format/column-map.md`, columns V–AO. Module: `app/spectora/parse.py`.
- **PH2** Fetch each photo into storage at import: only over `https` from `cdn.spectora.com`, following no redirects, with size and time caps. A failure raises `PHOTO_FETCH_FAILED` and the URL is kept.
  Evidence: `docs/design/preservation.md` §4; the URL stops working when the customer leaves Spectora, and it comes from an uploaded file. Module: `app/services/photos.py`.
- **PH3** An image inside Comment Text that Spectora hosts raises `INLINE_IMAGE_NOT_COPIED` on its comment. It is not copied, because that would mean rewriting the stored text; it is shown from where it is hosted.
  Evidence: the holdout run, `fixtures/holdout/README.md`; one template's text holds 13 images on `cdn.spectora.com/editor_assets`. Module: `app/services/photos.py`.

## HTML

- **H1** Sanitise stored HTML only when rendering it. The renderer never changes what is stored.
  Evidence: `docs/design/preservation.md` §4. Module: `app/render.py`.
- **H2** The editor kitchen-sink fixture renders with every tag, class, allowed attribute and allowed CSS property intact; only the editor-state attributes `contenteditable`, `draggable` and `fr-original-style` are removed.
  Evidence: `fixtures/editor/spectora-editor-kitchen-sink.html`, round-tripped through a real export. Module: `app/render.py`.
- **H3** An iframe keeps its `src` only when the host is YouTube, youtube-nocookie or Vimeo. Any other iframe is neutralised and counted.
  Evidence: `docs/design/preservation.md` §4. Module: `app/render.py`.
- **H4** Every link is rendered with `rel="noopener noreferrer"`.
  Evidence: of the 43 stock links, 39 set `target` and none set `rel`. Module: `app/render.py`.
- **H5** Classes are kept, and Froala's table and video classes render through a shim stylesheet.
  Evidence: `docs/design/preservation.md` §4; `fr-alternate-rows` and `fr-dashed-borders` carry visual meaning. Module: `app/render.py`, `app/web/static/froala-shim.css`.
- **H6** Report the markup inventory of an import and what the render policy will neutralise.
  Evidence: the brief asks how rich content is handled, "including any limits". Module: `app/render.py`, `app/services/reporting.py`.

## Detection

- **D1** Every upload gets exactly one verdict: `SPECTORA_HTML`; `SPECTORA_PLAIN`, imported with a `PLAIN_TEXT_EXPORT` warning; `UNKNOWN_SPREADSHEET`, refused with the header differences listed; or `NOT_A_SPREADSHEET`, refused.
  Evidence: `docs/design/preservation.md` §5; `probe-plain.xls`. Module: `app/spectora/detect.py`.
- **D2** The verdict never changes how a file is parsed.
  Evidence: one strict decode is correct for both export variants. Module: `app/spectora/parse.py`.

## Provenance and report

- **R1** An import is one database transaction. A failure leaves nothing behind.
  Evidence: `docs/design/preservation.md` §3. Module: `app/services/importer.py`.
- **R2** Each import records the file name, its SHA-256, the verdict, the parser version and the counts.
  Evidence: `docs/design/schema.md`, Layer 5. Module: `app/db/imports.py`.
- **R3** Before committing, verify that the stored raw rows equal what the reader produced, and that the tree read back through the editor's own query equals the parsed tree. On a mismatch, roll back.
  Evidence: `docs/design/preservation.md` §3. This proves storage, not parser correctness; the parser is checked by unit tests against hand-verified facts. Module: `app/services/importer.py`.
- **R4** Record a column ledger: each column is consumed, empty, constant or unrecognised, with its cell count.
  Evidence: `docs/design/preservation.md` §2. Module: `app/spectora/columns.py`.
- **R5** Every report shows what is missing from Spectora's export, separately from what this importer does not support.
  Evidence: the brief, "Distinguish information missing from the export from information your importer does not support". Module: `app/services/reporting.py`.
- **R6** Every issue names its source row and column where they apply.
  Evidence: the brief, "Make skipped or unsupported content visible". Module: `app/spectora/model.py`.

## Editing and copying

- **E1** The template, sections and items can be renamed; every comment field can be edited; sections, items and comments can be added, deleted and reordered. Every change persists and updates the template's modified time.
  Evidence: the brief, "Edit", and the agreed editor scope. Module: `app/services/editing.py`, `app/db/editing.py`.
- **E2** A comment body is saved only when it differs from what the editor loaded. A request without a body field leaves the body unchanged.
  Evidence: TinyMCE rewrites styles and wrapping on load. Module: `app/web/static/editor.js`, `app/services/editing.py`.
- **E3** Any comment can be reverted to the values it was imported with, read from its source row.
  Evidence: the source row keeps the original. Module: `app/services/editing.py`.
- **E4** Duplicating a template is a deep copy in one transaction, with new ids at every level and a link to the original. Editing either one never changes the other.
  Evidence: the brief, "Copy". Module: `app/db/copying.py`.
- **E5** Edits run the same value checks as import and show their warnings. Nothing is blocked.
  Evidence: `docs/design/schema.md`, Layer 4, "validate and report, never reject". Module: `app/services/editing.py`.
- **E6** A comment whose body was edited is marked as edited.
  Evidence: an edited body is no longer byte-identical to the import. Module: `app/services/editing.py`.

## Meta

- **Z1** Nothing in `app/spectora/` depends on template content. A test fails if any string literal in that package equals a section, item or comment name, or a value, found in the fixtures.
  Evidence: rule zero. Module: `tests/unit/test_rule_zero.py`.
- **Z2** The held-out templates are run once, after the parser is complete. A failure is fixed by correcting a general rule, never by adding a case for one template, and the result is recorded in `fixtures/holdout/README.md`.
  Evidence: `fixtures/holdout/README.md`. Module: `tests/holdout/`.
