import ast
from pathlib import Path

import pytest

from app.render import markup_inventory, neutralised, render_comment_html
from tests.helpers import analysed
from tests.paths import KITCHEN_SINK, PRIMARY, PROBE_HTML, RICH_COMMENT, ROOT

EDITOR_STATE = {"contenteditable", "draggable", "fr-original-style"}


def kitchen_sink() -> str:
    return KITCHEN_SINK.read_text("utf-8")


# ---------------------------------------------------------------- H1 only at render time


@pytest.mark.rule("H1")
def test_the_format_core_never_sanitises():
    for path in (ROOT / "app" / "spectora").glob("*.py"):
        imported = {
            alias.name
            for node in ast.walk(ast.parse(path.read_text("utf-8")))
            if isinstance(node, ast.Import | ast.ImportFrom)
            for alias in node.names
        } | {
            node.module
            for node in ast.walk(ast.parse(path.read_text("utf-8")))
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not imported & {"nh3", "app.render"}, path.name


@pytest.mark.rule("H1")
def test_rendering_leaves_the_parsed_body_as_stored():
    comments = analysed(PROBE_HTML).template.comments()
    before = [c.body_html for c in comments]
    for comment in comments:
        render_comment_html(comment.body_html)
    assert [c.body_html for c in comments] == before


@pytest.mark.rule("H1")
@pytest.mark.parametrize(
    ("hostile", "must_not_contain"),
    [
        ("<p>x</p><script>alert(1)</script>", "script"),
        ('<img src="x.png" onerror="alert(1)">', "onerror"),
        ('<a href="javascript:alert(1)">x</a>', "javascript"),
        ('<a href="data:text/html,<script>alert(1)</script>">x</a>', "data:"),
        ('<iframe srcdoc="<script>alert(1)</script>"></iframe>', "srcdoc"),
        ('<div style="position: fixed; top: 0">x</div>', "position"),
        ('<div style="background: url(https://evil.example/x.png)">x</div>', "url("),
        ("<object data=x.swf></object>", "object"),
        ("<form><input name=q></form>", "input"),
    ],
)
def test_constructs_that_can_run_or_escape_are_removed(hostile, must_not_contain):
    assert must_not_contain not in render_comment_html(hostile)


# ---------------------------------------------------------------- H2 the golden fixture


@pytest.mark.rule("H2")
def test_everything_spectoras_editor_produces_survives_except_editor_state():
    lost = neutralised(kitchen_sink())
    unexpected = {
        entry
        for entry in lost
        if entry.split(" on ")[0].removeprefix("attribute ") not in EDITOR_STATE
    }
    assert not unexpected, f"rendering removed real formatting: {sorted(unexpected)}"
    # The editor source carries contenteditable and draggable; Spectora adds
    # fr-original-style only when it saves, so that one appears in exports, not here.
    assert {entry.split(" ")[1] for entry in lost} == {"contenteditable", "draggable"}


@pytest.mark.rule("H2")
def test_every_style_property_in_the_fixture_is_kept():
    before = {k for k in markup_inventory(kitchen_sink()) if k.startswith("style ")}
    after = {
        k for k in markup_inventory(render_comment_html(kitchen_sink())) if k.startswith("style ")
    }
    assert before == after
    assert {"style font-size", "style color", "style width", "style background-color"} <= after


@pytest.mark.rule("H2")
@pytest.mark.parametrize("path", [PRIMARY, RICH_COMMENT, PROBE_HTML], ids=lambda p: p.name)
def test_real_exports_lose_nothing_but_editor_state_and_unsafe_positioning(path):
    lost: set[str] = set()
    for comment in analysed(path).template.comments():
        lost |= set(neutralised(comment.body_html))
    allowed_losses = {
        f"attribute {name} on <{tag}>" for name in EDITOR_STATE for tag in ("a", "span", "iframe")
    }
    allowed_losses |= {"style position"}
    assert lost <= allowed_losses, sorted(lost - allowed_losses)


# ---------------------------------------------------------------- H3 iframes


@pytest.mark.rule("H3")
@pytest.mark.parametrize(
    "src",
    [
        "https://player.vimeo.com/video/76073568",
        "https://www.youtube.com/embed/abc",
        "https://www.youtube-nocookie.com/embed/abc",
    ],
)
def test_video_hosts_keep_their_iframe(src):
    assert f'src="{src}"' in render_comment_html(f'<iframe src="{src}"></iframe>')


@pytest.mark.rule("H3")
@pytest.mark.parametrize(
    "src",
    [
        "https://evil.example/embed",
        "http://player.vimeo.com/video/1",
        "https://player.vimeo.com.evil.example/video/1",
    ],
)
def test_other_iframes_lose_their_source_and_are_counted(src):
    html = f'<iframe src="{src}"></iframe>'
    assert "src=" not in render_comment_html(html)
    assert neutralised(html)["attribute src on <iframe>"] == 1


# ---------------------------------------------------------------- H4 links


@pytest.mark.rule("H4")
def test_every_link_gets_noopener_noreferrer():
    rendered = render_comment_html('<p><a href="https://example.com" target="_blank">x</a></p>')
    assert 'rel="noopener noreferrer"' in rendered
    replaced = render_comment_html('<a href="https://example.com" rel="opener">x</a>')
    assert 'rel="noopener noreferrer"' in replaced
    assert 'opener"' not in replaced.replace('noopener noreferrer"', "")


@pytest.mark.rule("H4")
def test_stock_links_render_with_rel():
    bodies = [c.body_html for c in analysed(PRIMARY).template.comments() if "<a " in c.body_html]
    assert bodies
    assert all('rel="noopener noreferrer"' in render_comment_html(body) for body in bodies)


# ---------------------------------------------------------------- H5 classes and the shim


@pytest.mark.rule("H5")
def test_froala_classes_are_kept():
    rendered = render_comment_html(kitchen_sink())
    for class_name in (
        "fr-dashed-borders",
        "fr-alternate-rows",
        "fr-highlighted",
        "fr-thick",
        "fr-video",
    ):
        assert class_name in rendered


@pytest.mark.rule("H5")
def test_the_shim_styles_every_froala_class_the_editor_writes():
    shim = Path(ROOT / "app" / "web" / "static" / "froala-shim.css").read_text("utf-8")
    for class_name in (
        "fr-dashed-borders",
        "fr-alternate-rows",
        "fr-highlighted",
        "fr-thick",
        "fr-video",
    ):
        assert f".{class_name}" in shim


def test_inventory_counts_tags_attributes_styles_and_iframe_hosts():
    inventory = markup_inventory(
        '<p style="color: red; font-size: 2rem">x</p><iframe src="https://player.vimeo.com/v"></iframe>'
    )
    assert inventory["tag <p>"] == 1
    assert inventory["style color"] == 1
    assert inventory["style font-size"] == 1
    assert inventory["iframe from player.vimeo.com"] == 1
