"""Command line.

python -m app.cli parse <file>    parse an export and print what was found, no database
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from app.spectora.analysis import Analysis, analyse
from app.spectora.model import Refusal


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
    print(f"issues    {len(analysis.issues)}")
    for issue in analysis.issues:
        where = " ".join(
            part for part in (f"row {issue.row}" if issue.row else "", issue.column or "") if part
        )
        print(f"  {issue.severity.value:7s} {issue.kind.value:26s} {where:10s} {issue.detail}")


def _parse_command(arguments: argparse.Namespace) -> int:
    path = Path(arguments.file)
    try:
        analysis = analyse(path.read_bytes(), path.name)
    except Refusal as refused:
        print(f"refused   {refused.verdict.value}: {refused.reason}")
        for detail in refused.details:
            print(f"  {detail}")
        return 1
    _print_analysis(path, analysis)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    parse_parser = commands.add_parser("parse", help="parse an export without a database")
    parse_parser.add_argument("file")
    parse_parser.set_defaults(handler=_parse_command)
    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    sys.exit(main())
