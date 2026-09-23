# Data model

Built in the order the problem actually resolves.

**Model layers** — what the data *is*: hierarchy, ordering, node types, variance tolerance,
provenance. Each one has to be settled before the next makes sense.

**Features** — what the app *does*: import, edit, copy, report. These sit on top. They are not
layers, and the only thing the model owes them is that identity is surrogate and nothing is
shared between templates.

Every decision below is justified by a measurement in `docs/format/eda-findings.md` or a column definition
in `docs/format/column-map.md`. The format rules themselves are maintained in `docs/rules.md`.

## Rule zero: know the format, never the template

The importer may depend on **Spectora's file format**: the 42 column headers, what each column
means, that one row is one comment, that sections and items are contiguous blocks, how text is
encoded. That is the contract every export shares, verified identical across every file examined.

The importer must **never** depend on **template content**: no section, item, comment, class or
value names; no pattern matching on text the inspector typed; no lookup tables built from what
one template happened to contain. The committed exports are test fixtures, not a specification.
Anything a customer can type is data to store, never a signal to branch on.

Concretely, this rules out several ideas proposed earlier and since withdrawn: detecting empty
video wrappers by their class name, flagging "numeric-looking" multiple-choice fragments, a
slug-to-label table for recommendations, warning on names that contain `</`, and prefix or
pattern matching on column headers. Headers are matched exactly against the known 42, and a
mismatch is reported rather than guessed around.

---

## Layer 1 — Hierarchy

**Fixed at three levels: Template → Section → Item → Comment.** Not a generic parent-pointer
tree.

The export expresses exactly three levels, Spectora's own glossary names them "Column 1, 2, 3",
and Hive Inspect's editor shows the same three panes. A generic node table would buy flexibility
nothing is asking for and would cost the clarity the brief explicitly grades. If a fourth level
ever appears, that is a migration, not a reason to blur the model now.

**Identity rules, forced by the data:**

| Level | Identity | Why |
| --- | --- | --- |
| Section | **contiguous block of rows** | two adjacent same-named sections export as one block; name alone cannot tell them apart |
| Item | **contiguous block within its section block** | 62 names resolve to 136 items in Room-by-Room; the same name can recur as a separate block inside one section |
| Comment | **surrogate key** | `Fireplace / Damper Doors` has two comments named `Damper Inoperable` |

A new block starts a new node even if its name repeats, so the model never merges what the
file keeps separate. Adjacent same-named nodes are already merged in the file and cannot be
recovered; see `docs/format/eda-findings.md`, "Duplicate names".

The template itself has no row in the export. Its name survives only in the filename.

---

## Layer 2 — Ordering

**Reframe: ordering is not a fact to recover, it is a value to assign and then own.**

The EDA showed the export does not reliably encode display order. There is no order column
above the comment level, so item order in the file cannot be verified against Spectora's editor.
`Order (w/i item)` is dense in one template and largely constant in another, with 120 of 220
groups carrying duplicate values.

So: every node gets an explicit integer `position`, assigned at import from the best available
signal, and mutable thereafter. Once the inspector reorders anything, `position` is your data,
not Spectora's, and you would need the column regardless.

**Assignment rules at import:**

- Section `position` — block order in the file. Matched the Spectora UI in every export.
- Item `position` — block order in the file. The report states that item order is best-effort.
- Comment `position` — sort by type group (Informational, Limitations, Deficiencies), then by
  `Order (w/i item)`, then by source row as a stable tie-break.

Keep the raw `Order` value in `source_order` rather than discarding it once `position` is
computed. It is the customer's data even where it is useless.

---

## Layer 3 — Node types

Typed data lives almost entirely on the comment. Sections and items carry only a name in this
format.

```sql
create table template (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,              -- from the file name, editable
  origin          text not null,              -- 'import' | 'copy'
  copied_from_id  uuid references template(id) on delete set null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table section (
  id                uuid primary key default gen_random_uuid(),
  template_id       uuid not null references template(id) on delete cascade,
  name              text not null,
  position          integer not null,
  source_first_row  integer                   -- the block's first row in the file
);

create table item (
  id                uuid primary key default gen_random_uuid(),
  section_id        uuid not null references section(id) on delete cascade,
  name              text not null,
  position          integer not null,
  source_first_row  integer
);

create table comment (
  id                    uuid primary key default gen_random_uuid(),
  item_id               uuid not null references item(id) on delete cascade,
  position              integer not null,
  name                  text not null,
  body_html             text not null default '',   -- 83/392 legitimately empty
  comment_type          text not null default '',   -- info | limit | defect, verbatim
  category              text not null default '',   -- '-1' | '0' | '1' verbatim, defects only
  choices               text[] not null default '{}',
  unit_options          text[] not null default '{}',
  recommendation        text not null default '',   -- opaque slug, e.g. 'pro', 'monitor'
  source_order          text not null default '',   -- raw Order (w/i item)
  answer_type           text not null default '',   -- boolean|checkbox|date|number|range|signature|text
  default_value         text not null default '',   -- never coerced: 'true' and 'f' both occur
  default_value_2       text not null default '',
  default_unit_type     text not null default '',
  default_location      text not null default '',   -- verbatim, including the leading space
  estimate_min          text not null default '',
  estimate_max          text not null default '',
  locked                text not null default '',
  simple_format         text not null default '',
  disable_photos        text not null default '',
  uses                  text not null default '',
  source_last_modified  text not null default '',   -- MM/DD/YYYY HH:MM:SS, as exported
  body_edited_at        timestamptz,                -- set when the body is edited; TinyMCE rewrites HTML
  import_run_id         uuid references import_run(id) on delete set null,
  source_row_number     integer                     -- with import_run_id, points at the source row
);

create table comment_photo (
  id           uuid primary key default gen_random_uuid(),
  comment_id   uuid not null references comment(id) on delete cascade,
  position     integer not null,          -- 1..10, the export's slot (Spectora writes newest first)
  source_url   text not null default '',  -- cdn.spectora.com; dies with the Spectora account
  caption      text not null default '',
  stored_path  text                       -- our copy of the bytes; null if it was not copied
);
```

`supabase/migrations/0001_init.sql` is the authoritative version of every table here.

Text columns from the export default to `''` rather than allowing null. At the value level an
empty cell and a missing cell mean the same thing; the source row keeps the difference.

**Every one of the 42 columns has a field.** Some have never held anything but a default or
nothing at all in the exports we have. That is a fact about those templates, not about the
format, so no column is dropped on the strength of it. Unknown meaning is not a reason to
discard; it is a reason to store as text.

**`comment_type` and `answer_type` are `text`, not Postgres enums.** A native enum cannot store
a value it has not seen, so an unfamiliar export would either fail the insert or force the
importer to rewrite the value. Both violate "do not quietly drop or rewrite it." Validate in
the application, report the unknown, store it as it arrived.

**The two measured invariants are validation rules, not database constraints.** Across 1,190
rows of two files, `severity` is populated if and only if type is `defect`, and `choices` is
populated if and only if answer type is `checkbox`. Both are strong enough to check and report
on, and not strong enough to reject a customer's template over. A `CHECK` here converts a
surprising import into a failed one.

---

## Layer 4 — Variance between real templates

**This is the open risk, and the committed fixture actively understates it.** The file in this
repo is a stock InterNACHI template. 29 of its 42 columns are constant or empty, its HTML uses
only four tags, and it has zero unbalanced tags. The brief's customer has a template tuned for
four years. That template will exercise columns this one never touches.

What a real template plausibly contains that the fixture does not:

- **Word-pasted HTML.** `<span style=…>`, `<font>`, `<o:p>`, MSO conditional comments, inline
  `data:` images, unbalanced tags. The fixture's clean markup is the best case, not the normal
  case.
- **Populated photo columns**, all twenty of which are empty here.
- **`Locked`, `Simple Format`, `Disable Photos`** actually set, all empty here.
- **`Default Location`** in use, tied to Spectora's account-level Location Tags.
- **Answer types and recommendation slugs** beyond those observed; `signature` was already
  missing from the header's own list.
- **Scale**: a mature library runs one to two thousand narratives against this file's 392.
- Possibly non-English content, and item names longer than the 62-character maximum here.

**The design response is one rule: validate and report, never validate and reject.** Every
surprise becomes an `import_issue` and the row still lands. Store `body_html` byte-for-byte as
it arrives and sanitise with an allowlist at render time, so the customer's bytes are never
mutated by your parser and a malformed fragment cannot break the page.

---

## Layer 5 — Provenance and proof of fidelity

> Expanded in `docs/design/preservation.md`, including cell-level coverage numbers, the markup
> inventory, and format detection for non-Spectora files.

The brief grades "how you checked preservation", so preservation has to be checkable, which is
a schema decision rather than a test-suite decision.

```sql
-- One upload. It exists only if verification passed, because a failed verification rolls
-- the whole import back. It outlives its template while a copy still points at its rows.
create table import_run (
  id                uuid primary key default gen_random_uuid(),
  template_id       uuid references template(id) on delete set null,
  source_filename   text not null,
  source_sha256     text not null,       -- exact bytes imported
  verdict           text not null,       -- SPECTORA_HTML | SPECTORA_PLAIN; a warning, never parsing
  parser_version    text not null,
  rows_total        integer not null,
  empty_rows        integer not null,
  rows_skipped      integer not null,
  sections_created  integer not null,
  items_created     integer not null,
  comments_created  integer not null,
  comment_types     jsonb not null,    -- Comment Type value -> count, as imported
  photos_found      integer not null,
  photos_stored     integer not null,
  started_at        timestamptz not null,
  verified_at       timestamptz          -- set inside the import transaction, after verification
);

-- every row of the source, header included as row 1, verbatim
create table source_row (
  import_run_id uuid not null references import_run(id) on delete cascade,
  row_number    integer not null,
  raw           jsonb not null,          -- column letter -> text; null = cell with no value
  primary key (import_run_id, row_number)
);

-- the record of the import: deleting a node unlinks its issues and keeps them
create table import_issue (
  id             uuid primary key default gen_random_uuid(),
  import_run_id  uuid not null references import_run(id) on delete cascade,
  position       integer not null,
  kind           text not null,
  severity       text not null,     -- info | warning | error
  scope          text not null,     -- file | section | item | comment
  row_number     integer,
  column_letter  text,
  detail         text not null,
  section_id     uuid references section(id) on delete set null,
  item_id        uuid references item(id) on delete set null,
  comment_id     uuid references comment(id) on delete set null
);

-- one row per column per import: where each column's cells went
create table cell_ledger (
  import_run_id  uuid not null references import_run(id) on delete cascade,
  column_letter  text not null,
  header         text not null,
  outcome        text not null,     -- consumed | empty | constant | unrecognised
  cell_count     integer not null,
  target_field   text,
  primary key (import_run_id, column_letter)
);
```

An issue about a comment is linked to the comment, its item and its section, so the editor can
badge every level without walking the tree.

Row-level security is enabled on every table, with no policies. The app connects as the tables'
owner, which row-level security does not restrict; Supabase's public Data API, which it does
restrict, gets nothing.

**Keeping `source_row` is the single highest-value table here.** It means nothing is ever truly
dropped, an unmodelled column is still retrievable, and preservation can be *demonstrated* by
re-deriving from the stored rows and diffing against what was written. That is a far better
answer on camera than "I checked and it looked right."

**`import_issue.kind` carries the distinction the brief asks for**, and the two must never be
merged:

| Kind | Meaning |
| --- | --- |
| `MISSING_HEADER` | A known header is absent. Refused only for Section Name or Item Name. |
| `MULTIPLE_SHEETS` | The workbook has more than one sheet; only the first was read. |
| `UNKNOWN_HEADER` | A header outside the known 42, or a repeat of one. Its values stay in the source row. |
| `ROW_SKIPPED` | A row with no Section Name or Item Name, with its row number. |
| `UNEXPECTED_VALUE` | A Comment Type, Answer Type or Category outside the known values. Imported anyway. |
| `INVARIANT_VIOLATED` | Category without a deficiency, or choices without `checkbox`, or the reverse. |
| `MERGED_SECTIONS_SUSPECTED` | An item name recurs as a separate block inside one section. |
| `AMBIGUOUS_ORDER` | Duplicate Order values inside one comment-type group. |
| `PHOTO_FETCH_FAILED` | A photo could not be copied; its URL is kept. |
| `INLINE_IMAGE_NOT_COPIED` | An image inside the comment text is hosted by Spectora and was not copied. |
| `PLAIN_TEXT_EXPORT` | The file is Spectora's Plain Text export; links and formatting were already lost. |
| `RENDER_NEUTRALISED` | Markup that the render policy will not display, such as an iframe from another host. |

What is missing from Spectora's export, and what this importer does not support, are fixed
properties of the format and of this code, so they are shown on every report rather than stored
per import.

---

---

# Features

## Editing and copying

Not layers. Both are user-facing capabilities, and their correctness is decided entirely by
the identity rules in Layer 1: surrogate keys, and no rows shared between templates. Get that
wrong and no amount of feature work makes copy independent.

**Copy is a deep copy.** New rows at every level with fresh ids, `origin = 'copy'`, and
`copied_from_id` set for lineage. No shared rows, no copy-on-write. Independence then holds by
construction rather than by discipline, and it is provable on camera in fifteen seconds.

A copy keeps each comment's link to the source row it was imported from, so a copy can also be
reverted to imported values. It gets no import run of its own.

**Editable at baseline:** section name, item name, comment name, comment body. **Worth adding:**
reordering, since ordering is something the import explicitly could not guarantee and the
inspector is the only one who knows the right answer.

`updated_at` on `template` is touched by any descendant edit, so the library list can show
genuine recency.

---

## What I would not build

- A generic tree. Three levels is the truth of both products.
- Database `CHECK` constraints on the measured invariants. They would turn a surprising customer
  template into a failed import.
- Native Postgres enums on the two type columns, for the same reason.
- HTML rewriting at import. Sanitise at render, store verbatim.
- Merge-into-existing-template semantics. Spectora's own importer cannot do it either, and the
  format does not express it.
