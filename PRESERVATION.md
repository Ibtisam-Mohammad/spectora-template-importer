# Preservation and provenance

The brief's hardest requirements are all one requirement wearing three hats:

- "Preserve the template's text, hierarchy, and ordering."
- "Make skipped or unsupported content visible; do not quietly drop or rewrite it."
- "Distinguish information missing from the export from information your importer does not
  support."
- "Show how you checked preservation."

None of that is satisfied by asserting it. It has to be **measured, stored and displayed.**

---

## 1. Three coverage numbers, not one

A single "we imported it" figure hides the interesting part. Measured on the committed file:

| Measure | Value | Meaning |
| --- | --- | --- |
| **Capture coverage** | **100%** | Every one of 16,464 cells is stored verbatim in `source_row`. Nothing is discarded, ever. |
| **Model coverage** | **66.0%** | 3,043 of 4,611 non-empty cells are promoted into typed columns. |
| **Varying-data coverage** | **91.5%** | Of the 1,568 non-empty cells not modelled, all but 392 are constant system defaults. |

The third number is the honest one, and it decomposes cleanly:

```
non-empty cells not modelled           1,568
  Default Estimate Min = 10  (392)     constant, system default
  Default Estimate Max = 1000 (392)    constant, system default
  Uses = 0                    (392)    constant, system default
  Last Modified               (392)    varies (9 distinct values)
```

**Unmodelled is not the same as lost.** Three of those four columns hold a single value on every
row, so nothing about the customer's template is expressible in them. The only unmodelled column
that varies is `Last Modified`, which the EDA showed records export time rather than content
time. Storing it takes one column and pushes varying-data coverage to **100%** — every non-empty
cell whose value differs anywhere in the file is represented in the model.

Same shape on the second export: 33,516 cells, 68.7% model coverage, the identical four
unmodelled columns.

Quoting all three numbers, and saying which one you think matters, is a far stronger answer than
"nothing was dropped."

---

## 2. The cell ledger

Every cell gets an outcome. This is the mechanism behind the numbers above.

```sql
create type cell_outcome as enum (
  'consumed',        -- read and stored in a typed column
  'empty',           -- nothing there to preserve
  'constant',        -- non-empty but identical on every row; a system default
  'not_modelled',    -- non-empty, varies, deliberately not stored. Must be justified.
  'unrecognised'     -- column not in the known 42. Always reported.
);

create table cell_ledger (
  import_run_id uuid not null references import_run(id) on delete cascade,
  column_letter text not null,
  outcome       cell_outcome not null,
  cell_count    integer not null,
  target_field  text,             -- e.g. 'comment.body_html', null unless consumed
  note          text,             -- why, when not_modelled
  primary key (import_run_id, column_letter, outcome)
);
```

Aggregated per column rather than per cell, so it is 42 rows per import rather than 16,464, and
still answers "which cells did you read, and what happened to the rest" exactly.

`unrecognised` is the one that earns its keep on a future export. If Spectora adds a 43rd column,
the importer does not crash and does not silently ignore it; it reports a column it has never
seen, with its values still safe in `source_row`.

---

## 3. Proving preservation by re-derivation

Because `source_row` holds all 42 columns as JSON, preservation is checkable rather than
claimed:

1. Read the file, write `source_row` and the typed model in one transaction.
2. **Re-derive** the typed model from the stored rows alone, without touching the file.
3. Diff the re-derived result against what was written.

A mismatch means the parser is not deterministic. An empty diff means the model is a pure
function of the stored bytes, which is the actual claim you want to make on camera. It also means
a re-import after a parser fix can be replayed against the original bytes with no need for the
customer to re-export.

Store `source_sha256` so "this is the same file" is a fact, not a filename.

**The independent check** is the structural count: 13 sections, 69 items, 392 comments, types
splitting 302 defect / 78 info / 12 limit. Those numbers come from the file and must survive to
the screen. Show them side by side, source against imported.

---

## 4. Rich content: preserve everything, render safely

The brief asks how formatting, links and other rich content are handled "including any limits."
The answer has two halves that must not be confused.

**Parsing and storing: everything, untouched.** `body_html` is stored byte-for-byte as it
arrives after XML decoding. No tag is stripped, no attribute removed, no entity rewritten. The
customer's four years of formatting is never at risk from the importer, because the importer
does not touch it. This is also what makes every rendering decision below **reversible**: a
render policy can be loosened later without re-importing anything. Stripping at import time
would be permanent.

**Rendering: sanitise, which is not the same as strip.** HTML from an uploaded file is
untrusted input. Spectora's editor has a code view, so a customer can type literally any markup
into a comment, and rendering it raw means one `<script>` or `onerror=` in a template becomes
code running in the reviewer's browser. That is a security fail in a take-home, not a nuance.
But a sanitiser that allows only four tags throws away real formatting, which is the opposite
fail.

**The policy is a broad allowlist and a narrow denylist.** Allow everything Spectora's own
editor can produce, plus the common Word-paste tags, and remove only the constructs that can
execute or escape.

The minimum allowlist comes straight from Spectora's editor toolbar, which offers text style,
bold, italic, underline, colour, ordered and unordered lists, link, image, video, table, code
view and clear formatting:

| Construct | Allowed | Handling |
| --- | --- | --- |
| Block: `p`, `div`, `br`, `h1`–`h6`, `blockquote`, `pre` | yes | as-is |
| Inline: `strong`, `b`, `em`, `i`, `u`, `s`, `span`, `sub`, `sup`, `code` | yes | as-is |
| Lists: `ul`, `ol`, `li` | yes | as-is |
| Tables: `table`, `thead`, `tbody`, `tr`, `th`, `td` | yes | as-is |
| `a` with `href`, `target` | yes | `href` must be `http`, `https`, `mailto`; add `rel="noopener noreferrer"` |
| `img` with `src`, `alt`, `width`, `height` | yes | `src` must be `https:` or `data:image/*` |
| `iframe` for video | yes, restricted | `src` host must be YouTube or Vimeo; otherwise replaced by a visible link |
| `style` attribute | **yes, sanitised** | keep `color`, `background-color`, `font-weight`, `font-style`, `text-decoration`, `text-align`; drop `position`, `expression()`, `url()`, `behavior` |
| `class` attribute | yes | harmless without a stylesheet; keeping it is more faithful |
| `font` with `color`, `face` | yes | legacy but Spectora's colour picker may emit it |
| Word noise: `o:p`, `w:*`, MSO conditional comments | unwrapped | contents kept, wrapper removed |
| `script`, `object`, `embed`, `form`, `input`, `link`, `meta` | **no** | removed |
| `on*` event handlers, `javascript:` URLs, `srcdoc` | **no** | removed |

Measured on the committed file, that policy renders **100% of the markup present**: `p`, `a`,
`strong`, `div`, `href`, `target`, `class`, and the single `style`. Nothing in either export
falls into the denylist.

**Report what will be neutralised, per import.** The sanitiser runs at display time, but the
*inventory* runs at import time and knows the policy. So the import report can say, before the
customer ever opens a comment, "your template contains 2 `<script>` tags and 1 `onclick`
attribute; these will not render, and the original text is preserved." That keeps rendering
decisions inside "do not quietly drop" rather than outside it.

The inventory for the committed file:

```
tags       p 244 | a 43 | strong 1 | div 1        zero unbalanced
attributes href 43 | target 39 | class 1 | style 1
links      43, to 20 external hosts, none Spectora-hosted
entities   31 &amp; that must survive as entities
denylisted 0
```

Second export: `p 445 | a 81 | div 7`, attributes `href 81 | target 65 | class 7 | style 7`,
denylisted 0.

**Implementation note.** Do not write the sanitiser. DOMPurify on the client, or an equivalent
server-side library, is the correct tool, configured with the allowlist above. A hand-rolled
regex sanitiser is the single most common way this goes wrong.

**One real limitation to state rather than solve:** `Multiple Choice Options` is comma-separated
with no escaping, so a choice value containing a comma is unrecoverable by construction. None
occur in either file. That is a property of Spectora's format, not of this importer, and it
belongs in the `MISSING_FROM_EXPORT` bucket.

---

## 5. Other software: detect, name, refuse well

The brief scopes this to Spectora and warns that another export "in the same HTML-text format"
may be tested. Building a HomeGauge or Palm-Tech importer is out of scope and would cost the
deadline. **Showing the boundary is cheap and is worth more than pretending it does not exist.**

Make detection an explicit step with a named verdict, not an exception:

```
SPECTORA_HTML_XLSX   OOXML zip, one sheet, 42 headers matched
SPECTORA_PLAIN_TEXT  headers match but Comment Text contains no markup in any row
                     -> accept, warn: "this looks like the Plain Text export; links,
                        images and styling were stripped by Spectora before you
                        downloaded it. Re-export with Export HTML Text."
SPREADSHEET_UNKNOWN  readable spreadsheet, headers do not match
                     -> refuse, list which of the 4 required headers were found
NOT_A_SPREADSHEET    magic bytes are not a zip / not OOXML
                     -> refuse, say what was detected
```

The plain-text case is the valuable one. It is the mistake a real customer makes, Spectora's own
documentation is ambiguous enough to cause it, and the data loss happened *before* your importer
ran. Detecting it and saying so is the difference between being blamed and being trusted.

A short **supported formats** table in the UI does the rest of the work: Spectora HTML Text
supported, Spectora Plain Text accepted with a warning, HomeGauge / Palm-Tech / Home Inspector Pro
not supported, with a one-line reason. The architecture should make that visible too: the parse
step sits behind a format adapter interface, so "not supported" means "no adapter registered",
not "would need a rewrite".

---

## 6. What the user actually sees

The import report is one screen, and it is the chosen improvement made concrete:

- **Structure**, source against imported: 13 sections, 69 items, 392 comments.
- **Coverage**, the three numbers, with the varying-data one foregrounded.
- **Per column**, the ledger: consumed and where it went, constant, not modelled and why,
  unrecognised.
- **Missing from the export**, quoting Spectora: template settings, section icons, item ordering,
  photo binaries, conditional show/hide behaviour.
- **Warnings that need a human**: duplicate comment names inside one item, ambiguous ordering,
  values outside a documented enum.
- **Markup**, the inventory, and anything the render policy will neutralise.

Two of those deserve to be prominent because they are true and nobody else will say them:

> Item display order is best-effort. Spectora's export carries no ordering column above the
> comment level, and two independent exports disagree with Spectora's own editor.

> Three columns were not imported because they hold the same value on all 392 rows. They are
> Spectora system defaults, not your configuration.
