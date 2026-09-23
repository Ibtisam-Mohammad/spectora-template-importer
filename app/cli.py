"""Command line.

python -m app.cli parse <file>     parse an export and print what was found, no database
python -m app.cli migrate          apply database migrations and create the photo bucket
python -m app.cli import <file>    import an export into the configured database
python -m app.cli seed             import the primary fixture if the library is empty
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from app.config import Settings, get_settings
from app.db.migrations import apply_migrations
from app.db.pool import connect
from app.db.templates import list_templates
from app.services.importer import VerificationFailed, import_file
from app.services.photos import configured_copier, configured_storage
from app.spectora.analysis import Analysis, analyse
from app.spectora.model import Refusal

ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = ROOT / "fixtures" / "spectora" / "internachi-residential-2026-09-22.xls"
# The name Spectora gave the download, before it was renamed in this repository.
SEED_FILENAME = "InterNACHI Residential -2026-09-22.xls"


def _print_analysis(path: Path, analysis: Analysis) -> None:
    template = analysis.template
    types = Counter(comment.comment_type for comment in template.comments())
    print(f"file      {path.name}")
    print(f"verdict   {analysis.detection.verdict.value}")
    print(f"template  {template.name}")
    print(f"sections  {len(template.sections)}")
    print(f"items     {len(template.items())}")
    print(
        f"comments  {len(template.comments())}  "
        + "  ".join(f"{kind or '(blank)'}={count}" for kind, count in sorted(types.items()))
    )
    print(f"rows      {len(analysis.workbook.rows)} data rows, {template.empty_rows} empty")
    outcomes = Counter(entry.outcome for entry in analysis.ledger)
    print("columns   " + "  ".join(f"{outcome}={n}" for outcome, n in sorted(outcomes.items())))


def _print_issues(issues) -> None:
    print(f"issues    {len(issues)}")
    for issue in issues:
        where = " ".join(
            part for part in (f"row {issue.row}" if issue.row else "", issue.column or "") if part
        )
        print(f"  {issue.severity.value:7s} {issue.kind.value:26s} {where:10s} {issue.detail}")


def _print_refusal(refused: Refusal) -> None:
    print(f"refused   {refused.verdict.value}: {refused.reason}")
    for detail in refused.details:
        print(f"  {detail}")


def _database_url(settings: Settings) -> str:
    if settings.database_url is None:
        raise SystemExit("DATABASE_URL is not set. See .env.example.")
    return settings.database_url


def _import(data: bytes, filename: str) -> int:
    settings = get_settings()
    photos = configured_copier(settings)
    with connect(_database_url(settings)) as conn:
        try:
            outcome = import_file(conn, data, filename, photos)
        except Refusal as refused:
            _print_refusal(refused)
            return 1
        except VerificationFailed as failed:
            print(f"rolled back: verification failed: {failed}")
            return 1
        finally:
            if photos:
                photos.close()
    _print_analysis(Path(filename), outcome.analysis)
    _print_issues(outcome.issues)
    print(f"stored    template {outcome.template_id}, import run {outcome.run_id}")
    return 0


def _parse_command(arguments: argparse.Namespace) -> int:
    path = Path(arguments.file)
    try:
        analysis = analyse(path.read_bytes(), path.name)
    except Refusal as refused:
        _print_refusal(refused)
        return 1
    _print_analysis(path, analysis)
    _print_issues(analysis.issues)
    return 0


def _migrate_command(_: argparse.Namespace) -> int:
    settings = get_settings()
    with connect(_database_url(settings)) as conn:
        applied = apply_migrations(conn)
    print("applied   " + (", ".join(applied) if applied else "nothing; already up to date"))
    storage = configured_storage(settings)
    if storage is None:
        print("photos    storage not configured; set SUPABASE_URL and SUPABASE_SECRET_KEY")
    else:
        created = storage.ensure_bucket()
        print(f"photos    bucket '{settings.photo_bucket}' {'created' if created else 'exists'}")
    return 0


def _import_command(arguments: argparse.Namespace) -> int:
    path = Path(arguments.file)
    return _import(path.read_bytes(), arguments.name or path.name)


def _seed_command(_: argparse.Namespace) -> int:
    with connect(_database_url(get_settings())) as conn:
        existing = list_templates(conn)
    if existing:
        print(f"skipped   the library already holds {len(existing)} templates")
        return 0
    return _import(SEED_FILE.read_bytes(), SEED_FILENAME)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    parse_parser = commands.add_parser("parse", help="parse an export without a database")
    parse_parser.add_argument("file")
    parse_parser.set_defaults(handler=_parse_command)
    migrate_parser = commands.add_parser("migrate", help="apply database migrations")
    migrate_parser.set_defaults(handler=_migrate_command)
    import_parser = commands.add_parser("import", help="import an export into the database")
    import_parser.add_argument("file")
    import_parser.add_argument("--name", help="file name to record, which names the template")
    import_parser.set_defaults(handler=_import_command)
    seed_parser = commands.add_parser("seed", help="import the primary fixture if empty")
    seed_parser.set_defaults(handler=_seed_command)
    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    sys.exit(main())
