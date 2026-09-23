"""Jinja2 environment shared by every route, with the filters the pages use."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.config import get_settings
from app.db.records import StoredPhoto
from app.render import render_comment_html
from app.services.photos import public_url
from app.spectora.columns import ANSWER_TYPE_LABELS, CATEGORY_LABELS

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def comment_html(stored_html: str) -> Markup:
    """A stored comment body, sanitised for display (rule H1)."""
    return Markup(render_comment_html(stored_html))


def answer_label(answer_type: str) -> str:
    """Spectora's own name for an answer format, without its example, e.g. "Checkbox"."""
    label = ANSWER_TYPE_LABELS.get(answer_type)
    return label.split(" (")[0] if label else answer_type or "No answer format"


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def photo_src(photo: StoredPhoto) -> str:
    """Our stored copy when there is one, otherwise Spectora's original address."""
    if photo.stored_path:
        return public_url(get_settings(), photo.stored_path) or photo.source_url
    return photo.source_url


def when(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%d %b %Y, %H:%M UTC")


templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters.update(
    comment_html=comment_html,
    answer_label=answer_label,
    category_label=category_label,
    when=when,
)
templates.env.globals.update(photo_src=photo_src)
