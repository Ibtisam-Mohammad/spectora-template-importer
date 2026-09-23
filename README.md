# Spectora template importer

Take-home for Hive Inspect. Upload a Spectora **Export HTML Text** spreadsheet, get a structured
template you can browse, edit and duplicate, with a report of exactly what was imported and
what was not. Decisions and limits are in `NOTES.md`.

**Live app, opened on the seeded template:**
https://spectora-template-importer-mu.vercel.app/t/e3eabef9-0cdd-4c09-aef3-bd8e46e569d4

- Its template report, covering what happened during the import:
  https://spectora-template-importer-mu.vercel.app/runs/c2e444de-ebbd-49bc-82a0-02c7cd52cfdd
- The library, with the upload form: https://spectora-template-importer-mu.vercel.app
- There is no login.

**The input file.** InterNACHI Residential, loaded from Spectora's Template Center and
exported with Export to spreadsheet, then Export HTML Text, on 22 September 2026. It is
`fixtures/spectora/internachi-residential-2026-09-22.xls`; its provenance, and the other
exports used, are in `fixtures/spectora/README.md`.

## Stack

Python 3.12, FastAPI, Jinja2 and htmx, with TinyMCE for comment text. PostgreSQL on Supabase
through psycopg 3, with Supabase Storage for copied photos. The display sanitiser is nh3.
Tests use pytest; linting and formatting use ruff. Hosted on Vercel.

## Setup

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```
uv sync
cp .env.example .env        # then fill it in, see below
```

**Environment variables.** Set them in `.env` locally and in the Vercel project settings.
Never commit real values.

| Variable | What it is |
| --- | --- |
| `DATABASE_URL` | Supabase Postgres through the **transaction pooler** (port 6543). Dashboard, Connect, Transaction pooler. The direct connection is IPv6-only and Vercel cannot reach it. |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SECRET_KEY` | A secret key (`sb_secret_...`), used only on the server to copy photos into Storage. Optional: without it, photos keep their Spectora links and the report says so. |
| `PHOTO_BUCKET` | Storage bucket for photos. Default `template-photos`. |
| `TEST_DATABASE_URL` | A disposable database for the integration tests. They drop and recreate the app's tables in it. Never point it at real data. |

## Database initialisation

```
uv run --env-file .env python -m app.cli migrate    # tables, and the public photo bucket
uv run --env-file .env python -m app.cli seed       # imports the committed export if the library is empty
```

`migrate` applies `supabase/migrations/*.sql` in order, each once, tracked in
`schema_migrations`. Row-level security is on for every table, with no policies, so Supabase's
public Data API can read nothing. The app connects as the tables' owner.

## Run

```
uv run --env-file .env uvicorn app.main:app --reload
```

Other commands:

```
uv run python -m app.cli parse fixtures/spectora/probe-html.xls     # parse only, no database
uv run --env-file .env python -m app.cli import <file.xls>         # import from the command line
```

## Tests

```
uv run pytest                                              # unit tests, no database
TEST_DATABASE_URL=postgresql://... uv run pytest           # plus the integration tests
TEST_DATABASE_URL=postgresql://... uv run pytest --holdout # plus the four held-out templates
TEST_DATABASE_URL=postgresql://... uv run pytest --holdout --rules-report  # rewrites docs/rules-status.md
uv run ruff check . && uv run ruff format --check .
```

Every rule in `docs/rules.md` is tagged on the tests that check it. pytest ends with a
one-line rule tally, and `--rules-report` writes the per-rule table to `docs/rules-status.md`.
Run it with a database and `--holdout`, or the rules those tests cover show as skipped.
`docs/rules-status.md` is the last full run.

The comment editor's "send the text only if it changed" rule runs in the browser, so it has
its own check, driven through Edge or Chrome with Playwright. It needs the app running and the
rich-comment export (`fixtures/spectora/internachi-residential-rich-comment.xls`) imported. It
edits one comment and then reverts it, so the comment ends as imported:

```
uv run --env-file .env --with playwright python tools/browser_check.py http://127.0.0.1:8000
```

## Deploy

1. Create a Supabase project, in us-east-1 to sit next to Vercel's default region.
2. Run `migrate` and `seed` against it from your machine, as above.
3. Import the repository into Vercel. It detects FastAPI and finds `app` in `app/main.py`
   (`pyproject.toml` also names it under `[tool.vercel]`). `vercel.json` keeps fixtures, docs
   and tests out of the function.
4. Set `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the Vercel project, and
   deploy. Preview deployments sit behind Vercel's login, so review the production URL.

Uploads are capped at 4 MB, under Vercel's 4.5 MB request limit, and the page checks the size
before sending. A free Supabase project pauses after 7 days without activity; restore it from
the dashboard if the live app shows a database error.

## Layout

```
app/
  spectora/     the format core: bytes in, a parsed template and its issues out. Pure.
  render.py     the display policy for comment HTML (nh3). Pure.
  db/           SQL, one module per concern: imports, templates, editing, copying, runs
  services/     import, photos, editing, reporting; they own the transactions
  web/          routes, Jinja templates and static files; no SQL, and format rules only
                through app/spectora
  cli.py        parse, migrate, import, seed
supabase/migrations/   the schema
tests/
  unit/         no database needed
  integration/  need TEST_DATABASE_URL
  holdout/      the four sealed templates, only with --holdout
docs/
  rules.md      every rule the importer follows; tests are tagged with rule IDs
  format/       what a Spectora export contains, measured (the evidence log)
  design/       schema.md and preservation.md
fixtures/
  spectora/     the exports, with provenance; the committed input is
                internachi-residential-2026-09-22.xls
  editor/       HTML copied from Spectora's comment editor
  holdout/      four templates kept unseen until the parser was finished, and the results
tools/          the analysis scripts and the browser check
```

The analysis scripts in `tools/` need only the Python standard library, for example
`python tools/verify_claims.py fixtures/spectora/probe-html.xls`. The exception is
`browser_check.py`, which runs as shown above.
