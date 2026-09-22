# Data model

Built in the order the problem actually resolves.

**Model layers** — what the data *is*: hierarchy, ordering, node types, variance tolerance,
provenance. Each one has to be settled before the next makes sense.

**Features** — what the app *does*: import, edit, copy, report. These sit on top. They are not
layers, and the only thing the model owes them is that identity is surrogate and nothing is
shared between templates.

Every decision below is justified by a measurement in `EDA-FINDINGS.md` or a column definition
in `COLUMN-MAP.md`.

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
| Section | `name` within a template | 13 unique names, no collisions |
| Item | **`(section, name)`** | 62 names resolve to 136 items in Room-by-Room; name alone collapses 74 items |
| Comment | **surrogate key** | `Fireplace / Damper Doors` has two comments named `Damper Inoperable` |

The template itself has no row in the export. Its name survives only in the filename.

---

## Layer 2 — Ordering

**Reframe: ordering is not a fact to recover, it is a value to assign and then own.**

The EDA showed the export does not reliably encode display order. Item order contradicts the
Spectora UI in both files examined. `Order (w/i item)` is dense in your file and largely
constant in the other, with 120 of 220 groups carrying duplicate values. File position runs
forward in one file and reverse in the other.

So: every node gets an explicit integer `position`, assigned at import from the best available
signal, and mutable thereafter. Once the inspector reorders anything, `position` is your data,
not Spectora's, and you would need the column regardless.

**Assignment rules at import:**

- Section `position` — first appearance in the file. Matched the Spectora UI exactly in both
  files.
- Item `position` — first appearance in the file. **Known to be approximate.** Record it as an
  import issue.
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
  id                    uuid primary key default gen_random_uuid(),
  name                  text not null,              -- from filename, editable
  source_filename       text,
  source_sha256         text,                       -- exact bytes imported
  origin                text not null,              -- 'spectora_xlsx' | 'copy'
  copied_from_id        uuid references template(id) on delete set null,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create table section (
  id           uuid primary key default gen_random_uuid(),
  template_id  uuid not null references template(id) on delete cascade,
  name         text not null,
  position     integer not null
);

create table item (
  id          uuid primary key default gen_random_uuid(),
  section_id  uuid not null references section(id) on delete cascade,
  name        text not null,
  position    integer not null
);

create table comment (
  id              uuid primary key default gen_random_uuid(),
  item_id         uuid not null references item(id) on delete cascade,
  name            text not null,
  body_html       text,                -- nullable: 83/392 legitimately empty
  comment_type    text not null,       -- info | limit | defect
  severity        smallint,            -- -1 | 0 | 1, defect rows only
  answer_type     text not null,       -- boolean|checkbox|date|number|range|text
  choices         text[] not null default '{}',
  unit_options    text[] not null default '{}',
  recommendation  text,                -- opaque slug, e.g. 'pro', 'monitor'
  default_value   text,
  default_value_2 text,
  position        integer not null,
  source_row      integer,             -- row in the spreadsheet
  source_order    integer              -- raw Order (w/i item), kept verbatim
);
```

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
- **`date` and `range` answer types**, documented but absent from both files.
- **Recommendation slugs** beyond the two observed.
- **Scale**: a mature library runs one to two thousand narratives against this file's 392.
- Possibly non-English content, and item names longer than the 62-character maximum here.

**The design response is one rule: validate and report, never validate and reject.** Every
surprise becomes an `import_issue` and the row still lands. Store `body_html` byte-for-byte as
it arrives and sanitise with an allowlist at render time, so the customer's bytes are never
mutated by your parser and a malformed fragment cannot break the page.

---

## Layer 5 — Provenance and proof of fidelity

> Expanded in `PRESERVATION.md`, including cell-level coverage numbers, the markup
> inventory, and format detection for non-Spectora files.

The brief grades "how you checked preservation", so preservation has to be checkable, which is
a schema decision rather than a test-suite decision.

```sql
create table import_run (
  id               uuid primary key default gen_random_uuid(),
  template_id      uuid not null references template(id) on delete cascade,
  source_filename  text not null,
  source_sha256    text not null,
  parser_version   text not null,
  rows_total       integer not null,
  rows_imported    integer not null,
  sections_created integer not null,
  items_created    integer not null,
  comments_created integer not null,
  started_at       timestamptz not null default now(),
  finished_at      timestamptz
);

-- every row of the source, verbatim, all 42 columns
create table source_row (
  import_run_id uuid not null references import_run(id) on delete cascade,
  row_number    integer not null,
  raw           jsonb not null,
  primary key (import_run_id, row_number)
);

create table import_issue (
  id             uuid primary key default gen_random_uuid(),
  import_run_id  uuid not null references import_run(id) on delete cascade,
  kind           text not null,
  severity       text not null,     -- info | warning | error
  column_letter  text,
  row_number     integer,
  detail         text not null
);
```

**Keeping `source_row` is the single highest-value table here.** It means nothing is ever truly
dropped, an unmodelled column is still retrievable, and preservation can be *demonstrated* by
re-deriving from the stored rows and diffing against what was written. That is a far better
answer on camera than "I checked and it looked right."

**`import_issue.kind` carries the distinction the brief asks for**, and the two must never be
merged:

| Kind | Meaning |
| --- | --- |
| `MISSING_FROM_EXPORT` | Spectora never put it in the file. Template settings, section icons, item order, photo binaries. |
| `NOT_MODELLED` | Present in the file, deliberately not stored. Name the column. |
| `UNEXPECTED_VALUE` | Outside a documented enum, or an invariant violated. |
| `AMBIGUOUS_ORDER` | Duplicate or constant `Order` values in a type group. |
| `DUPLICATE_NAME` | Two comments sharing a name inside one item. |
| `ROW_SKIPPED` | Only for genuinely unusable rows, with the reason. |

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

A copy does not inherit `source_row` or an `import_run`; it inherits `position` only. Row
numbers belong to an import, not to a template.

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
