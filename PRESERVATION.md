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
| **Capture coverage** | **100%** | Every cell is stored verbatim in `source_row`. Nothing is discarded, ever. |
| **Model coverage** | **74.6%** | 3,544 of 4,753 non-empty cells are promoted into typed columns (`probe-html.xls`, schema as written). |
| **Varying-data coverage** | **100%** | Every non-empty cell whose value differs anywhere in the file is in the model. The 1,209 unconsumed cells are the three constant system-default columns. |

The third number is the honest one, and it decomposes cleanly:

```
non-empty cells not consumed           1,209
  Default Estimate Min = 10  (403)     constant on every row, system default
  Default Estimate Max = 1000 (403)    constant on every row, system default
  Uses = 0                    (403)    constant on every row, usage counter
```

**Unconsumed is not the same as lost.** All three columns hold a single value on every row, so
nothing about the customer's template is expressible in them. `Last Modified`, which an earlier
draft of this document left out, is a genuine per-comment save time and is now modelled, which
is what takes varying-data coverage to 100%. These numbers come from `tools/coverage.py`, whose
"constant" test requires one non-empty value on *every* row; a column populated on a single row
is sparse customer data, not a default, and is consumed.

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

**Spectora's editor is Froala.** Confirmed from a live comment authored with every toolbar
control, saved as `fixtures/spectora-editor-kitchen-sink.html`: the markup carries `fr-video`,
`fr-draggable`, `fr-dashed-borders`, `fr-alternate-rows`, `fr-highlighted` and `fr-thick`
classes. That fixture is the golden test for the renderer: **everything in it must survive
sanitisation.** The first draft of this policy failed it in six CSS properties and six
attributes, which is why the table below exists.

What the editor actually emits, and how the policy handles it:

| Construct | Editor output | Handling |
| --- | --- | --- |
| Headings | `<span style="font-size:2rem; line-height:2.25rem">`, **not** `<h1>` | allow `font-size`, `line-height` |
| Bold, italic, underline | `<strong>`, `<em>`, `<u>` | as-is |
| Colour | `<span style="color: rgb(213, 54, 54)">` | allow `color`; **accept `rgb()`**, a hex-only sanitiser strips it |
| Lists | `<ol>`, `<ul>`, `<li>`; empty item is `<li><br></li>` | as-is |
| Links | `<a href rel="noopener noreferrer" target="_blank">` | allow; `href` must be `http`, `https`, `mailto`; add `rel` if absent. Note the 43 legacy links in the export have `target` on 39 and `rel` on none |
| Video | `<span class="fr-video" style="display:block; clear:both; text-align:center"><iframe width height src frameborder allowfullscreen>` | allow `iframe` when `src` host is `youtube.com`, `youtube-nocookie.com`, `player.vimeo.com`; otherwise replace with a visible link. Allow `display`, `clear`, `frameborder`, `allowfullscreen`, `width`, `height` |
| Tables | `<table class style="width:100%"><thead><th colspan><tbody><td colspan rowspan style>` | allow `colspan`, `rowspan`, `width`, `background-color`, `text-align`, `vertical-align` |
| Empty cell | `<td><br></td>` | as-is |
| Editor state | `contenteditable="false"`, `draggable="true"`, `fr-original-style=""` | **strip**; harmless but they are editor chrome, not content. Note Froala also injects `style="color: rgb(53, 119, 168)"` on links at save time |
| Froala classes | `fr-dashed-borders`, `fr-alternate-rows` on table; `fr-highlighted`, `fr-thick` on cells | **keep, and ship a stylesheet shim** |
| `&nbsp;` | entity in the editor, **U+00A0 in the export** | preserve the character |

**Froala classes are not cosmetic, and this changes an earlier claim.** I said `class` was
harmless without a stylesheet. Wrong in the useful direction: `fr-alternate-rows` is the
alternating row shading, `fr-dashed-borders` is the border style, `fr-highlighted` and
`fr-thick` are per-cell borders. Drop the class or omit the stylesheet and a table the customer
formatted renders as a plain grid. Keeping the attribute is necessary and not sufficient. A
shim of roughly ten CSS rules mapping those four classes to their visual meaning makes the render
faithful, and its absence is a render-coverage gap to report, not to hide.

**Two video structures exist.** Froala emits `<span class="fr-video"><iframe ...></span>` and
the export preserves it intact, confirmed by round trip. The stock template's empty
`<div class="youtube-embed-wrapper">` is an older, different structure that arrived empty. Both
must be handled: render the first, placeholder the second.

Full allowlist after correction:

| Class | Allowed |
| --- | --- |
| Block tags | `p`, `div`, `br`, `h1`–`h6`, `blockquote`, `pre`, `hr` |
| Inline tags | `strong`, `b`, `em`, `i`, `u`, `s`, `span`, `sub`, `sup`, `code`, `font` |
| Lists, tables | `ul`, `ol`, `li`, `table`, `thead`, `tbody`, `tfoot`, `tr`, `th`, `td`, `caption` |
| Media | `a`, `img`, `iframe` (host-restricted) |
| Attributes | `href`, `target`, `rel`, `src`, `alt`, `title`, `width`, `height`, `colspan`, `rowspan`, `frameborder`, `allowfullscreen`, `class`, `style` |
| CSS properties | `color`, `background-color`, `font-size`, `font-weight`, `font-style`, `font-family`, `line-height`, `text-align`, `text-decoration`, `vertical-align`, `width`, `max-width`, `height`, `display`, `clear`, `overflow`, `padding*`, `margin*`, `border*`, `position: relative` only |
| **Denied** | `script`, `object`, `embed`, `form`, `input`, `button`, `link`, `meta`, `base`, `svg`, `math`; `on*` handlers; `javascript:` and `data:` URLs except `data:image/*` on `img`; `srcdoc`; `contenteditable`, `draggable`; CSS `expression()`, `url()`, `behavior`, `position: absolute/fixed`, `z-index` |

**Tested mechanically against the fixture:** zero tags, zero attributes and zero CSS properties
outside the allowlist, after stripping the two editor-state attributes.

Measured on the committed file, that policy renders **100% of the markup present**: `p`, `a`,
`strong`, `div`, `href`, `target`, `class`, and the single `style`. **Scanned both exports for
every denylisted construct**: no `script`, `iframe`, `img`, `object`, `form`, event handler,
`javascript:` URL or CSS `expression()` occurs in either file. Denylisted count is zero, measured
rather than assumed.

**Retraction: the HTML export does not strip embedded videos.** An earlier version of this
document claimed it did, based on empty `<div class="youtube-embed-wrapper">` shells in the
stock template. That was tested directly: a comment authored in Spectora with a Vimeo embed, a
formatted table and every toolbar control was exported and diffed against the editor's own
source (`fixtures/spectora-editor-kitchen-sink.html`). **Every tag, attribute, class and CSS
property survived.** The `<iframe>` is intact. The only changes Spectora made were additive:
`&nbsp;` became U+00A0, and the `<a>` tag gained `fr-original-style=""` and
`style="color: rgb(53, 119, 168);"` on save.

So the empty `youtube-embed-wrapper` divs, one in this template and seven in Room-by-Room, are
**pre-existing artifacts in the stock template**, most likely a legacy embed format from before
Froala or a removed video whose wrapper was left behind. The export reproduces them faithfully.
They still deserve detection and a placeholder at render, because painted literally they are a
large blank rectangle, but the cause is the template, not the export.

**Finding that replaced it: default photos are Spectora-hosted URLs.** The first populated
`Default Photo 1` observed reads:

```
https://cdn.spectora.com/default_photos/images/005/621/179/original/image_created_with_a_mobile_phone.png?1790095571
```

The export carries a link, not the image. The link is publicly fetchable today (HTTP 200,
`image/png`, 966 KB, no authentication). It will not be fetchable after the customer closes
their Spectora account. **An importer that stores the URL has not preserved the photo.** Fetch
the bytes at import time, store them, and record the original URL alongside. If a fetch fails,
that is an `import_issue`, named by comment, not a silent broken image later.

The same applies to any `<img src="https://cdn.spectora.com/...">` inside `Comment Text`, which
this template does not contain but a tuned one may.

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
denylisted 0 | empty video wrappers 1
```

Second export: `p 445 | a 81 | div 7`, attributes `href 81 | target 65 | class 7 | style 7`,
denylisted 0, empty video wrappers 7.

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
SPECTORA_PLAIN_TEXT  headers match; no tag in any Comment Text; no &amp; in Comment
                     Text after XML decode; bare & in section names after XML decode
                     -> accept, warn: "this is the Plain Text export. Spectora removed
                        every link URL, every table structure and all formatting
                        before you downloaded it, and stripped tag-like text from
                        names. Re-export with Export HTML Text." Then decode names
                        ONCE (XML only), not twice.
SPREADSHEET_UNKNOWN  readable spreadsheet, headers do not match
                     -> refuse, list which of the 4 required headers were found
NOT_A_SPREADSHEET    magic bytes are not a zip / not OOXML
                     -> refuse, say what was detected
```

The plain-text case is the valuable one. It is the mistake a real customer makes, Spectora's own
documentation is ambiguous enough to cause it, and the data loss happened *before* your importer
ran. Measured on a real pair: the Plain export loses **43 of 43 link URLs**, every table
structure, and all formatting, and it also strips tag-shaped text from section, item and
comment names. Detecting it and saying so is the difference between being blamed and being
trusted.

**Detection also decides decoding.** The HTML export double-encodes `&` in every text column;
the Plain export single-encodes it. A parser that always applies one extra HTML decode is
correct on HTML exports and corrupts a legitimately typed `&amp;` on Plain exports. Detect
first, then decode to the variant's depth. Record the variant on `import_run`.

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
- **Missing from the export**, quoting Spectora and measured: empty sections and items, template
  settings, section icons, item ordering, photo binaries, the Location Tags vocabulary, and
  auto-closed tags appended to any name containing `<letter`.
- **Warnings that need a human**: duplicate comment names inside one item, ambiguous ordering,
  values outside a documented enum.
- **Markup**, the inventory, and anything the render policy will neutralise.

Two of those deserve to be prominent because they are true and nobody else will say them:

> Item display order is best-effort. Spectora's export carries no ordering column above the
> comment level, and two independent exports disagree with Spectora's own editor.

> Three columns were not imported because they hold the same value on all 392 rows. They are
> Spectora system defaults, not your configuration.
