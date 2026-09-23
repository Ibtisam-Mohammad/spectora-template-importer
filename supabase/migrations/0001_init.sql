-- Template library, and the provenance of every import.
-- Design and rationale: docs/design/schema.md. Format rules: docs/rules.md.
--
-- Columns that hold values from a Spectora export are text with no CHECK constraints: an
-- unfamiliar value must be stored and reported, never rejected (rules V1 to V8).

create table template (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  origin          text not null check (origin in ('import', 'copy')),
  copied_from_id  uuid references template (id) on delete set null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- One upload. A run exists only if its verification passed, because a failed verification
-- rolls the whole import back (rules R1 to R3). It outlives its template while a copy's
-- comments still point at its source rows.
create table import_run (
  id                uuid primary key default gen_random_uuid(),
  template_id       uuid references template (id) on delete set null,
  source_filename   text not null,
  source_sha256     text not null,
  verdict           text not null,
  parser_version    text not null,
  rows_total        integer not null,
  empty_rows        integer not null,
  rows_skipped      integer not null,
  sections_created  integer not null,
  items_created     integer not null,
  comments_created  integer not null,
  photos_found      integer not null,
  photos_stored     integer not null,
  started_at        timestamptz not null,
  verified_at       timestamptz
);

create table section (
  id                uuid primary key default gen_random_uuid(),
  template_id       uuid not null references template (id) on delete cascade,
  name              text not null,
  position          integer not null,
  source_first_row  integer
);

create table item (
  id                uuid primary key default gen_random_uuid(),
  section_id        uuid not null references section (id) on delete cascade,
  name              text not null,
  position          integer not null,
  source_first_row  integer
);

create table comment (
  id                    uuid primary key default gen_random_uuid(),
  item_id               uuid not null references item (id) on delete cascade,
  position              integer not null,
  name                  text not null,
  body_html             text not null default '',
  comment_type          text not null default '',
  category              text not null default '',
  choices               text[] not null default '{}',
  unit_options          text[] not null default '{}',
  recommendation        text not null default '',
  source_order          text not null default '',
  answer_type           text not null default '',
  default_value         text not null default '',
  default_value_2       text not null default '',
  default_unit_type     text not null default '',
  default_location      text not null default '',
  estimate_min          text not null default '',
  estimate_max          text not null default '',
  locked                text not null default '',
  simple_format         text not null default '',
  disable_photos        text not null default '',
  uses                  text not null default '',
  source_last_modified  text not null default '',
  body_edited_at        timestamptz,
  import_run_id         uuid references import_run (id) on delete set null,
  source_row_number     integer
);

create table comment_photo (
  id            uuid primary key default gen_random_uuid(),
  comment_id    uuid not null references comment (id) on delete cascade,
  position      integer not null,
  source_url    text not null default '',
  caption       text not null default '',
  stored_path   text
);

-- Every row of the uploaded sheet, header included as row 1, cell text exactly as read and
-- keyed by column letter. A key holding null is a cell with no value; a missing key is no cell.
create table source_row (
  import_run_id  uuid not null references import_run (id) on delete cascade,
  row_number     integer not null,
  raw            jsonb not null,
  primary key (import_run_id, row_number)
);

-- Issues are the record of the import, so deleting a node unlinks its issues and keeps them.
create table import_issue (
  id             uuid primary key default gen_random_uuid(),
  import_run_id  uuid not null references import_run (id) on delete cascade,
  position       integer not null,
  kind           text not null,
  severity       text not null,
  scope          text not null,
  row_number     integer,
  column_letter  text,
  detail         text not null,
  section_id     uuid references section (id) on delete set null,
  item_id        uuid references item (id) on delete set null,
  comment_id     uuid references comment (id) on delete set null
);

create table cell_ledger (
  import_run_id  uuid not null references import_run (id) on delete cascade,
  column_letter  text not null,
  header         text not null,
  outcome        text not null,
  cell_count     integer not null,
  target_field   text,
  primary key (import_run_id, column_letter)
);

create index section_template_position on section (template_id, position);
create index item_section_position on item (section_id, position);
create index comment_item_position on comment (item_id, position);
create index comment_import_run on comment (import_run_id);
create index comment_photo_comment on comment_photo (comment_id, position);
create index import_run_template on import_run (template_id, started_at desc);
create index import_issue_run on import_issue (import_run_id, position);

-- The app connects as the tables' owner, which row-level security does not restrict. Enabling
-- it with no policies closes these tables to Supabase's public Data API.
alter table template enable row level security;
alter table import_run enable row level security;
alter table section enable row level security;
alter table item enable row level security;
alter table comment enable row level security;
alter table comment_photo enable row level security;
alter table source_row enable row level security;
alter table import_issue enable row level security;
alter table cell_ledger enable row level security;
