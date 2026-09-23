# NOTES

Notes for the Hive Inspect template-importer assignment.

---

## Product exploration

### Hive Inspect

**What I did.** I signed up for the trial, ran a sample inspection and published a report.
Then I imported two of this repo's exports through Hive's own importer and compared what arrived
with what the files contain:

- `internachi-residential-rich-comment.xls`, the stock template plus one comment written with
  every control in Spectora's editor;
- `probe-html.xls`, which adds every answer format, special characters and three photos.

**The import dialog.** It names four sources:

- Spectora;
- Home Inspector Pro;
- HomeGauge;
- Horizon (Carson Dunlop).

For anything else it offers help through chat. It accepts `.xls` and `.xlsx`, but does not say
which Spectora export to use, HTML Text or Plain Text.

An **Import cost estimates** option warns that stock Spectora templates repeat one default
range on every comment. That matches what we measured: 10 to 1000 on every row. While the
import runs, a screen says it is downloading and uploading images, so default photos are
copied, as they are here.

**What Hive's importer got right**

- Structure: 13 sections, 69 subsections and 392 comments, in the file's order. Both comments
  named "Damper Inoperable" were kept.
- Rich text: sized and coloured text, bold, italic, underline, links and lists. Tables keep
  their merged cells, cell colours and alignment.
- Answer choices, such as the four options of "In Attendance".
- A Checkbox comment whose default is `true` becomes a Checkbox Item with "Auto-select"
  ticked.
- Severity maps onto Hive's own categories: Low became Maintenance Items.
- Recommendation codes become names: `cabinet` shows as Cabinet Contractor, and
  `carpetcleaner` as Carpet Cleaner. Hive must hold Spectora's standard list. This app shows
  the code, because the export carries no names.
- Default photos arrive, in the export's order.

**What it lost or changed, without saying so**

| In the export | In Hive |
| --- | --- |
| A Vimeo embed inside a comment | Gone. Its list item is empty. |
| Table styling from Spectora's editor: dashed borders, alternate-row shading, highlighted and thick cells, header shading | A plain grid. |
| A Number answer with units ("Temperature": Fahrenheit, Celsius) | A Text field. The units are gone. |
| A Numeric Range with units (10 to 20, inches or feet) | A Text field with default 10. The upper value and the units are gone. |
| A comment name containing `&` (the export double-encodes it) | The list shows `Smith & Sons`, but the edit field shows `Smith &amp; Sons`. Item names with the same encoding are decoded correctly. |

After the upload, the only message is "Template Saved". Nothing tells the inspector what was
changed or dropped, so they would find out one comment at a time.

**Not checked:**

- whether default locations and photo captions arrive, since neither showed in the edit form;
- the Date and Signature answer formats.

**What Hive could do better**

1. **Say what the import did.** Show counts in and out, and every change or loss, named by
   comment. This app's template report is that idea.
2. **Keep the answer formats.** Number and Numeric Range should keep their units and both
   defaults, not become Text.
3. **Decode comment names the way item names already are**, so no `&amp;` reaches an
   inspector.
4. **Keep embeds and the table styling Spectora's editor writes,** or say that they were
   dropped.
5. **Name the export in the dialog and the docs:** Export to spreadsheet, then Export HTML
   Text.

**What the documentation says about importing from Spectora.** The public docs at
`docs.hiveinspect.com/templates/inspection-templates` cover the Spectora path in a single
sentence: *"If transitioning from Spectora or another company, select the option to import.
Ensure to export files in HTML format for proper text formatting."* There are no Spectora-side
menu paths, no named export type, no statement of what survives the import, and no list of
limitations.

That matters because the instruction is ambiguous against Spectora's actual UI. Spectora
offers **Export to spreadsheet** with two variants, **Export Plain Text** and **Export HTML
Text**, and both download as a spreadsheet: a file named `.xls` that is really an `.xlsx`
workbook, not an HTML file. A user following Hive's docs literally
would look for an HTML export, not a spreadsheet, and the assignment itself has to specify
"Export to spreadsheet → Export HTML Text" and warn against the plain-text variant. Naming
the exact path in the docs would remove the most likely first-run failure.

**Documented template model** (from the same page, for reference while designing the schema):

| Concept | Notes |
| --- | --- |
| Template name / customer viewing name | Two separate names, internal and client-facing |
| Rating flags | `IN` and `INP`, toggled on or off per template |
| Sections | Reorderable by drag-and-drop; controls client report order |
| Comment types | Three: Information, Limitations, Defects or deficiencies |
| Report introduction / summary | Rich text, supports brand colours and images |
| Attached documents | PDF, PNG and other files |
| Template hub | Prebuilt templates, e.g. Hive Inspection Residential, Concave Residential Inspection Report, Sewer Lateral from All-Star Home Inspection |

Primary UI actions named in the docs: Import, Save Changes, New Field, Save to Template.

The docs do not describe subsection hierarchy, comment tags or types beyond the three
categories above, which is a gap worth confirming in the product rather than the docs.

### Binsr comparison

Explored Binsr alongside Hive. Observations are from the trial, not from documentation.

**Where Binsr is ahead**

- **Onboarding.** Binsr opens with a better introductory video, and its tooltips are more
  helpful throughout. You learn the product faster without leaving it.
- **AI-powered importer.** Binsr's import is AI-driven, and it offers both a manual and an
  AI-powered path so the user can choose how much to trust the automation.
- **Types and Tags.** Binsr's types and tags system is noticeably more feature-rich. The
  trade-off is that it is also more likely to confuse a new user, so the extra power is not
  free.
- **Scope beyond inspection.** Binsr also builds the inspector's website, which widens what
  the subscription covers.

**Where Hive is ahead**

- **Template editing UI.** Hive's side-by-side view of sections and subsections is the better
  editing surface. You can see the structure and the content at the same time, which is
  exactly what matters when checking a migrated template.
- **Toggle controls.** The toggle buttons in Hive's UI are a clearer interaction than the
  equivalents in Binsr.
- **Named import sources.** Hive offers a default import option for other providers such as
  Spectora. Binsr has no provider-specific default import at all. For a customer switching off
  four years of tuned Spectora templates, that is the difference between a path and a blank
  page.

**Comparable in both**

- **Comment editing** is close to equivalent, and both offer AI-assisted comment editing.

**What Hive could learn from Binsr**

1. **Offer the manual path next to the automated one.** Binsr letting the user pick between
   manual and AI import is a trust affordance, not a feature duplication. An inspector
   migrating a library they will not retype wants the option to drive it themselves.
2. **Teach inside the product.** The opening video and the tooltips do more for a
   non-technical inspector than documentation does, and Hive's own docs are thin on exactly
   the workflow a new customer hits first.
3. **Borrow the richer types and tags carefully.** More structure is genuinely useful, but
   Binsr shows the cost. If Hive adds it, it should be progressive rather than exposed to a
   first-time user on day one.

**What Binsr could learn from Hive**

1. **Provider-specific import defaults.** Not having a Spectora path at all is the single
   biggest gap for a switching customer.
2. **The side-by-side structural view** while editing.

### Influence on this build

- **Three panes, like Spectora and Hive.** Sections, items and comments side by side is the
  surface both Spectora and Hive use, and the one I rated Hive ahead on. An inspector checking
  a migrated template needs to see where a comment sits while reading it.
- **Trust before automation.** Binsr's choice between manual and AI import says the user wants
  to see and control what the importer did. This importer takes the other half of that idea:
  no model, a deterministic parser, and a report that shows its working.
- **Hive's own importer confirms the gap.** It parses well, but changed answer formats and
  dropped an embed without a word. What is missing there is not parsing; it is telling the
  inspector what happened, which is the improvement this app chose.
- **Name the export path.** Hive's docs say "export in HTML format" and never name the menu. The
  upload form here names it: Export to spreadsheet, then Export HTML Text. If the Plain Text
  export arrives anyway, it is recognised and flagged.

---

## The improvement: an import report you can trust

In the app it is the **Template report**: the report on what happened when the template was
imported.

**The customer problem.** This customer has four years of tuned comments and will not retype
them. What stops them switching is doubt: did the import get everything, and would they notice
if it had not? A green "import complete" message does not answer that, and checking 392
comments, or 1,248 in a mature library, by eye is not realistic.

**What it is.** Every upload lands on a report, which stays linked from the library and the
editor:

- **Verification.** Inside the import transaction, every cell of every source row and every
  field of the tree, read back through the editor's own query, is compared with the parse. A
  mismatch rolls the whole import back.
- **Re-derivation.** When the report opens, the stored rows are parsed again, without the
  upload. Its counts, rows, sections, items and comments by type, are compared with those
  recorded at import.
- **Structure side by side.** The file against what was imported, down to the comment types.
- **Three coverage numbers.** Cells captured, modelled, and varying data modelled, with the
  ledger for all 42 columns behind them.
- **Import notes.** Grouped by kind, each naming its row and column and linking to the node in
  the editor. The same notes badge the sections, items and comments they concern.
- **Markup.** An inventory of the HTML in the comments, and what the display policy holds back.
- **Two separate lists.** What is missing from Spectora's export, and what this importer does
  not support.

**Why this one, and not the other two.**

- **Trust comes first.** A friendlier editor does not help a customer who suspects the import
  lost something, because they will not start editing.
- **Difficult cases are covered here too.** The difficult cases this format actually produces
  are the Plain Text export, merged same-named sections, photos and images that live on
  Spectora's servers, and markup that cannot be shown safely. The report is where the customer
  sees each of them, named by row, instead of discovering them months later.
- **The time went on proving, not claiming.** The report is only worth trusting if its numbers
  are real, so most of the time on it went into the checks behind it, not into the page.

---

## How far the editor goes

The brief asks for renaming sections and items and editing comment text, and leaves the rest
as a decision. I went further in one direction only: so that the inspector never has to go back
to Spectora to fix something the import could not settle.

- **Reorder.** Item order is best-effort from the file, so the inspector is the only one who
  knows the right order and needs to be able to set it.
- **Add and delete.** Empty sections and items never leave Spectora, so re-creating them has
  to be possible here.
- **Every comment field.** Answer format, choices, defaults, severity, recommendation and
  location, laid out as Spectora's own editor lays them out, so the form is familiar on day
  one.
- **Revert to imported.** An inspector trying things out on four years of work needs a way
  back.
- **Guidance where it is needed.** A "?" on each pane and comment heading and on most fields
  explains it in plain words,
  including the ones Spectora's export leaves cryptic, such as the recommendation code `pro`.
  Import notes appear above the items or comments they concern, not only in the report.
- **Pick lists from the template itself.** Recommendation, location and default unit open a
  dropdown of the values this template already uses, most used first, and anything else can
  still be typed. Spectora keeps the full lists in the account, not in the export, so a fixed
  list would be invented. Location is offered as the whole value each comment uses, because
  Spectora joins tags with spaces and tags themselves contain spaces (rule V7).
- **No field out of reach.** Fields the chosen answer format does not use wait under "Other
  fields" rather than disappearing, so the inspector can still fill them.
- **The file's own row, on every comment.** Each card lists every filled cell of its source
  row as exported, and marks any cell that did not go into a field. Nothing from the file is
  shown as an empty field.

It is a working surface, not the chosen improvement. It is kept to what migration needs: no
AI writing help, no search, no bulk edit (see below).

---

## Supported input

- **Accepted:** Spectora's **Export to spreadsheet, then Export HTML Text**. The file is named
  `.xls` but is an OOXML workbook. It is recognised by its content, not its extension.
- **Read:** the first worksheet, header on row 1. Columns are matched by exact header text
  against the 42 Spectora writes, not by position. One row is one comment; sections and items
  are contiguous blocks of rows.
- **Accepted with a warning:** Spectora's Plain Text export. It is detected from the file and
  imported, and the report says links and formatting were lost before the file was downloaded.
- **Refused, nothing stored:** anything that is not an `.xlsx`-format workbook, CSV files and
  old binary `.xls` files included, and workbooks missing a Section Name or an Item Name
  column. The refusal lists the header differences.
- **Tolerated and reported:** unknown or missing columns, blank rows, values Spectora does not
  document, and unusual combinations. Nothing is refused for those, and every cell of the sheet
  is kept with the import.
- **Warned about, not read:** sheets after the first. The warning names them.
- **Size:** up to 4 MB per upload. The largest export seen is 183 KB, with 1,248 comments.

The rules behind all of this are in `docs/rules.md`. The measurements they rest on are in
`docs/format/`.

---

## Formatting, links and rich content

**Stored exactly.** Comment Text is stored exactly as the spreadsheet's XML reader returns it.
It is never entity-decoded, trimmed or cleaned at import, so no display decision can damage
it, and every one can be changed later without re-importing.

**Displayed safely.** HTML from an uploaded file is untrusted, so it is sanitised when it is
displayed, with nh3. The policy allows everything Spectora's editor (Froala) produces:

- sized and coloured text, bold, italic and underline;
- lists and links;
- tables with merged cells;
- images, and YouTube or Vimeo embeds;
- Froala's table classes, styled by a small shim stylesheet.

It is an allowlist: it keeps what Froala writes and holds back everything else. That covers
everything that can run code or escape the comment's box: scripts, event handlers, forms,
frames from other hosts, `javascript:` links, and CSS such as `position`. It also covers
harmless markup that is simply not on the list, such as `align` or `data-*` attributes. Every
link opens with `rel="noopener noreferrer"`.

A golden test holds the policy to the HTML of a comment written with every control in
Spectora's editor.

**Limits.**

- Markup the policy holds back is kept but not shown. The report lists it per comment, with
  counts.
- Editing a comment's text in TinyMCE rewrites its HTML. So the text is sent only if it
  changed, an edited comment is marked, and Revert brings back the original from the source
  row.
- Images inside comment text are shown from where they are hosted. Spectora-hosted ones are
  flagged, because they stop working when the account closes; they are not copied.
- Default photos are copied into Supabase Storage at import. Only https links on Spectora's
  CDN are fetched, with no redirects and with size and time caps. A failure is reported and
  the original link is kept.

---

## Known limitations

**Missing from Spectora's export.** No importer can bring these in:

- sections and items with no comments;
- section and item settings: icons, Standards of Practice, reminders, optional and
  information-only flags, and the overview grid;
- the template's name and settings (the name here comes from the file name);
- an order column for sections and items. Both follow file order. Section order matched
  Spectora's editor in every export examined, and item order in two of three, so the report
  calls item order best-effort;
- the photos themselves, which are links to Spectora's servers;
- the account's Location Tags and Recommendation lists. Defaults arrive as text, and the
  editor suggests the values the template already uses;
- where one of two neighbouring same-named sections ends. Spectora writes them as one, and
  the importer flags the likely case;
- name text that looks like an HTML tag, such as `<x>`, which Spectora exports with an added
  closing tag.

**Not supported by this importer:**

- exports from other inspection software, which are refused;
- restoring what the Plain Text export removed;
- sheets after the first;
- displaying the markup listed under "Formatting" above;
- copying images inside comment text;
- splitting a section Spectora merged, merging into an existing template, and exporting back
  to Spectora;
- editing photos: default photos are shown, not added, removed or reordered;
- moving an item to another section;
- import notes on copies. They stay with the imported template; a copy links to the report.

**Of the app, not the import:**

- **No accounts and no CSRF protection.** Anyone with the URL can edit or delete. That is
  acceptable for a review demo, and the first thing to add for real use.
- **Last write wins.** There is no locking or edit history beyond Revert.

---

## What I cut, and why

The test for every cut: does this customer need it to move their template across intact? If
not, it waited.

**Cut from the import**

- **A model in the import path.** The input is a fixed 42-column format that can be parsed
  exactly, and verified exactly. A model could invent sections or drop comments, and the
  report would then be checking a guess. A model would be worth its risk for other vendors'
  exports, which have no fixed format; those are out of scope.
- **Other vendors' formats.** The brief scopes this to Spectora. They are refused cleanly,
  with the reason, rather than half-supported.
- **Re-importing into an existing template.** A customer who keeps editing in Spectora during
  the switch would want a newer export merged in, with a diff. That needs matching rules the
  format cannot support, since names are not unique. Today each upload becomes a new template.
- **Copying images inside comment text.** It would mean rewriting the stored text. They are
  flagged instead (rule PH3).
- **Section and item settings.** The export does not carry them, so there would be nothing to
  import into them.

**Cut from the editor**

- **AI help writing comments.** Hive and Binsr both have it, but it is report writing, which
  the brief puts out of scope, and it does nothing for migration fidelity.
- **Search and bulk find-and-replace.** Useful in a 1,248-comment library, for example to
  change a company name everywhere. It is the first editor feature I would add next.
- **Drag-and-drop reordering.** Move up and move down cover the need with far less code.
- **Photo editing, moving items between sections, and version history.** Revert-to-imported
  covers the undo that matters most: going back to what Spectora had.

**Cut from the app**

- **Login and teams.** It would put a step between the reviewer and the app. It is the first
  thing to add for real use.
- **Handing the template over to Hive.** The real end of this workflow is a template inside
  Hive. This app stands in for that. Its schema maps onto Hive's documented model (sections,
  three comment types), which is where I would take it next.

---

## How I checked my work

**Preservation.**

- `tools/verify_claims.py` re-asserts 75 measured facts about the probe export. Many of the
  same facts are also unit tests.
- Every import is verified before it commits: every source row cell for cell, and the tree
  read back through the editor's query field for field. Five tests tamper with a different
  stored table mid-import and confirm the import rolls back and leaves nothing.
- Every comment of every fixture re-parses on its own from its stored source row, exactly.
  That is what Revert relies on.
- The committed export imports as 13 sections, 69 items and 392 comments, split 302 / 78 / 12,
  and the report shows those numbers on both sides. 100% of filled cells are captured and
  modelled.

**A different export.** Four stock templates were sealed, unopened, before the parser
existed. Their hashes were recorded at the time. They were run once, blind, after the
parser was finished, and again after the two fixes below:

- All four imported and verified, up to 1,248 comments.
- The run found two general gaps: Spectora-hosted images inside comment text, and `float`.
  Both were fixed as general rules, in their own commit.
- One of the four was not fully blind. The results and that caveat are in
  `fixtures/holdout/README.md`.

A test fails if any string in the format core matches a name or value from the fixtures, so
the parser cannot quietly learn one template.

**Saved edits.** Integration tests make every kind of edit through the service and the web
routes, then read it back. Renames, adds, deletes, section and item moves and text edits are
read on a new connection, which proves they were committed. They also check two things:

- saving an untouched form leaves the comment byte-identical;
- edits run the import's checks without being blocked.

`tools/browser_check.py` drives Edge through the one rule that lives in JavaScript: an
untouched TinyMCE save sends no body, an edit is stored and marked, and Revert restores the
original exactly.

**Independent copies.**

- Edits to a copy never reach the original, and edits to the original never reach the copy.
  A copy outlives its deleted original and can still be reverted.
- A drift test gives every column a value, copies, and compares every copied row as JSON. I
  checked it by dropping a column from the copy list: the test failed.

**Failure cases.**

- A non-spreadsheet is refused. A spreadsheet with other headers is refused with the
  differences listed. In both cases nothing is stored.
- The Plain Text export is imported with a warning.
- Merged same-named sections are flagged.
- A database error mid-import leaves nothing behind.
- An upload over 4 MB gets a clear message.

**Totals.** 293 tests pass with a database and the holdout: 193 unit, 80 integration and 20
holdout. Without a database, the 193 unit tests run. All 59 rules in `docs/rules.md` are
covered; `docs/rules-status.md` is the last full run.

---

## How I used AI tools

Built with Claude Code as a pair. I directed the analysis, the probes and every decision; it
wrote most of the code and documents, and I reviewed them.

What kept the output honest:

- **A rules checklist tied to tests.** `docs/rules.md` lists every rule; a meta-test fails on a
  rule with no test.
- **Rule zero, enforced by a test.** Know the format, never the template.
- **Probe exports.** I made exports in Spectora specifically to settle open questions,
  instead of assuming.
- **The sealed holdout.** Four templates sealed before the parser existed, and run blind once
  it was finished. One had been seen before as an outside copy, as its README says.

The analysis scripts in `tools/` are part of the repo for that reason.

---

## Time spent

About 15 hours over two days, 22 and 23 September 2026. Most of it went into understanding
Spectora's format before writing code; with the rules, fixtures and probe exports settled
first, the build itself took about 90 minutes.

---

## Credits

**Libraries used, not modified:**

- FastAPI with Starlette and pydantic, uvicorn, python-multipart, Jinja2, htmx, and TinyMCE
  (GPL build, from jsDelivr);
- psycopg and psycopg-pool, defusedxml, nh3 (the Rust ammonia sanitiser), and httpx;
- pytest, ruff, uv, and Playwright for the browser check.

No starter template was used. The format analysis, the probes, the schema, the parser, the
importer and its verification, the report, the editor, the copy and the tests are this
project's own work.
