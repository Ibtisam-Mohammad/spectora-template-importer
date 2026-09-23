"""Display stored comment HTML safely. Pure: HTML in, HTML out; nothing stored is changed.

Rules: H1 (sanitise only at render), H2 (everything Spectora's editor produces survives),
H3 (iframes only from video hosts), H4 (links get rel="noopener noreferrer"),
H5 (classes kept, for the Froala shim stylesheet).

The allowlist is broad on purpose: it is everything Spectora's Froala editor can write, plus
common pasted markup. What it removes is only what can run code or escape the page.
"""

from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit

import nh3

_BLOCK = {"p", "div", "br", "hr", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}
_INLINE = {"strong", "b", "em", "i", "u", "s", "strike", "span", "sub", "sup", "code", "font"}
_LISTS = {"ul", "ol", "li"}
_TABLES = {"table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col"}
_MEDIA = {"a", "img", "iframe"}
TAGS = _BLOCK | _INLINE | _LISTS | _TABLES | _MEDIA

ATTRIBUTES = {
    "*": {"class", "style", "title"},
    "a": {"href", "target", "name"},
    "img": {"src", "alt", "width", "height"},
    "iframe": {"src", "width", "height", "frameborder", "allowfullscreen", "allow"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "col": {"span", "width"},
    "colgroup": {"span"},
    "ol": {"start", "type"},
    "li": {"value"},
    "font": {"color", "face", "size"},
}

_BOX_SIDES = ("", "-top", "-right", "-bottom", "-left")
_BORDER_PARTS = ("", "-width", "-style", "-color")
STYLE_PROPERTIES = {
    "color",
    "background-color",
    "font-size",
    "font-weight",
    "font-style",
    "font-family",
    "line-height",
    "text-align",
    "text-decoration",
    "vertical-align",
    "width",
    "max-width",
    "height",
    "display",
    "clear",
    "overflow",
    *(f"padding{side}" for side in _BOX_SIDES),
    *(f"margin{side}" for side in _BOX_SIDES),
    *(f"border{side}{part}" for side in _BOX_SIDES for part in _BORDER_PARTS),
    "border-collapse",
}

VIDEO_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "player.vimeo.com",
}
# Attributes Froala writes to track its own editing state. They carry no formatting, so
# removing them is not a loss worth reporting.
EDITOR_STATE_ATTRIBUTES = frozenset({"contenteditable", "draggable", "fr-original-style"})

_IMAGE_DATA_PREFIXES = tuple(
    f"data:image/{kind};" for kind in ("png", "jpeg", "jpg", "gif", "webp")
)


def _filter_attribute(tag: str, attribute: str, value: str) -> str | None:
    """Per-value checks nh3 cannot express. It keeps the original value if this raises, so
    every path returns explicitly and any error removes the attribute."""
    try:
        if tag == "iframe" and attribute == "src":
            parts = urlsplit(value)
            is_video = parts.scheme == "https" and parts.hostname in VIDEO_HOSTS
            return value if is_video else None
        if attribute in ("src", "href") and value.strip().lower().startswith("data:"):
            is_image = tag == "img" and value.strip().lower().startswith(_IMAGE_DATA_PREFIXES)
            return value if is_image else None
        return value
    except Exception:
        return None


_CLEANER = nh3.Cleaner(
    tags=TAGS,
    attributes=ATTRIBUTES,
    attribute_filter=_filter_attribute,
    url_schemes={"http", "https", "mailto", "tel", "data"},
    link_rel="noopener noreferrer",
    filter_style_properties=STYLE_PROPERTIES,
)


def render_comment_html(stored_html: str) -> str:
    """Safe HTML for display. The stored value is never modified."""
    return _CLEANER.clean(stored_html)


# ---------------------------------------------------------------- inventory


class _Inventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.counts[f"tag <{tag}>"] += 1
        for name, value in attrs:
            self.counts[f"attribute {name} on <{tag}>"] += 1
            if name == "style" and value:
                for declaration in value.split(";"):
                    prop = declaration.split(":", 1)[0].strip().lower()
                    if prop:
                        self.counts[f"style {prop}"] += 1
            if tag == "iframe" and name == "src" and value:
                self.counts[f"iframe from {urlsplit(value).hostname or 'unknown host'}"] += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_comment(self, data: str) -> None:
        self.counts["html comment"] += 1


def markup_inventory(html: str) -> Counter[str]:
    """Counts of tags, attributes, style properties and iframe hosts in some HTML."""
    parser = _Inventory()
    parser.feed(html)
    parser.close()
    return parser.counts


def neutralised(stored_html: str) -> Counter[str]:
    """What rendering removes: the stored markup's inventory minus the rendered markup's.

    Derived from nh3's actual output, so it cannot disagree with the policy above.
    """
    return markup_inventory(stored_html) - markup_inventory(render_comment_html(stored_html))


def neutralised_content(stored_html: str) -> Counter[str]:
    """What rendering removes, leaving out Froala's editing-state attributes."""
    return Counter(
        {
            entry: count
            for entry, count in neutralised(stored_html).items()
            if not (
                entry.startswith("attribute ") and entry.split(" ")[1] in EDITOR_STATE_ATTRIBUTES
            )
        }
    )
