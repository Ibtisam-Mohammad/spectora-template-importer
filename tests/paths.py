from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECTORA = ROOT / "fixtures" / "spectora"
EDITOR = ROOT / "fixtures" / "editor"
HOLDOUT = ROOT / "fixtures" / "holdout"

PRIMARY = SPECTORA / "internachi-residential-2026-09-22.xls"
RICH_COMMENT = SPECTORA / "internachi-residential-rich-comment.xls"
PROBE_HTML = SPECTORA / "probe-html.xls"
PROBE_PLAIN = SPECTORA / "probe-plain.xls"
PROBE_DUPLICATE = SPECTORA / "probe-duplicate.xls"
ANALYSED = (PRIMARY, RICH_COMMENT, PROBE_HTML, PROBE_PLAIN, PROBE_DUPLICATE)
KITCHEN_SINK = EDITOR / "spectora-editor-kitchen-sink.html"
