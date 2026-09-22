# NOTES

Notes for the Hive Inspect template-importer assignment.

> Status: in progress. Sections marked TODO are not yet written and must not ship as-is.

---

## Product exploration

### Hive Inspect

TODO: trial signup, sample inspection, published report, template-import walkthrough.

**What the documentation says about importing from Spectora.** The public docs at
`docs.hiveinspect.com/templates/inspection-templates` cover the Spectora path in a single
sentence: *"If transitioning from Spectora or another company, select the option to import.
Ensure to export files in HTML format for proper text formatting."* There are no Spectora-side
menu paths, no named export type, no statement of what survives the import, and no list of
limitations.

That matters because the instruction is ambiguous against Spectora's actual UI. Spectora
offers **Export to spreadsheet** with two variants, **Export Plain Text** and **Export HTML
Text**, and both produce an `.xlsx`, not an HTML file. A user following Hive's docs literally
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

TODO: connect the above to specific design decisions once the app exists.

---

## Supported input

TODO. Must state: exact Spectora export variant accepted, file extension, which sheet and
columns are read, and what a valid file looks like.

---

## Known limitations

TODO. Must distinguish clearly between:

- information that is **missing from the Spectora export itself**, and
- information the export contains that **this importer does not yet support**.

Also cover formatting, links and other rich content in the export, and where the limits are.

---

## What I cut, and why

TODO.

---

## How I checked my work

TODO. Must cover: preservation of text, hierarchy and ordering; edits persisting across a
restart; a copy being edited without affecting the original; behaviour on at least one
failure case; and behaviour on a second, different export in the same format.

---

## Time spent

TODO.

---

## Credits

TODO. Any starter, library or open-source project this builds on, and what is my own work.
