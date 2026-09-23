"""Check the comment editor in a real browser: the part of rule E2 that lives in JavaScript.

Opens a comment with rich text, opens TinyMCE, saves without touching it, then types and saves,
then reverts, and checks the database after each step:

  untouched save  body not sent, stored body byte-identical, not marked edited
  edited save     body sent, stored body changed, marked edited
  revert          stored body byte-identical to the import again, mark cleared

Needs a running app, its DATABASE_URL, a template imported from
fixtures/spectora/internachi-residential-rich-comment.xls, and Microsoft Edge or Chrome.
Playwright is not a project dependency; run it with:

  uv run --with playwright python tools/browser_check.py http://127.0.0.1:8000

The last step reverts, so the comment ends as imported.
"""

import os
import sys

import psycopg
from playwright.sync_api import sync_playwright

FIND_RICH_COMMENT = """
select t.id, s.id, i.id, c.id from template t
join section s on s.template_id = t.id join item i on i.section_id = s.id
join comment c on c.item_id = i.id
where c.body_html like '%%<table%%' and c.source_row_number is not null
order by t.created_at desc limit 1
"""
BODY_STATE = "select md5(body_html), body_edited_at is not null from comment where id = %s"


def main(base: str) -> int:
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True, prepare_threshold=None) as db:
        found = db.execute(FIND_RICH_COMMENT).fetchone()
        if found is None:
            print("no imported comment with a table; import the rich-comment fixture first")
            return 2
        template, section, item, comment = found

        def state() -> tuple[str, bool]:
            return db.execute(BODY_STATE, [comment]).fetchone()

        imported = state()
        failures = []
        with sync_playwright() as playwright:
            browser = _launch(playwright)
            page = browser.new_page()
            posted = []
            page.on("request", lambda r: posted.append(r.post_data or "") if r.method == "POST" else None)
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(f"{base}/t/{template}?section={section}&item={item}")
            card = f"#comment-{comment}"
            page.locator(f"{card} > summary").click()

            _open_editor(page, card, comment)
            page.locator(f"{card} button[type=submit]", has_text="Save").click()
            page.wait_for_selector(f"{card} .saved")
            _check(failures, "untouched save sends no body", not any("body_html" in p for p in posted))
            _check(failures, "untouched save leaves the body and its mark", state() == imported)

            posted.clear()
            _open_editor(page, card, comment)
            page.evaluate(f"tinymce.get('body-{comment}').insertContent(' edited in the browser ')")
            page.locator(f"{card} button[type=submit]", has_text="Save").click()
            page.wait_for_selector(f"{card} .badge:text('Edited')")
            digest, edited = state()
            _check(failures, "an edit sends the body", any("body_html" in p for p in posted))
            _check(failures, "an edit is stored and marked", digest != imported[0] and edited)

            page.locator(f"{card} button", has_text="Revert to imported").click()
            page.wait_for_selector(f"{card} .saved:text('Put back')")
            _check(failures, "revert restores the imported body exactly", state() == imported)
            browser.close()
    return 1 if failures else 0


def _launch(playwright):
    for channel in ("msedge", "chrome"):
        try:
            return playwright.chromium.launch(channel=channel, headless=True)
        except Exception:
            continue
    return playwright.chromium.launch(headless=True)


def _open_editor(page, card: str, comment: str) -> None:
    page.locator(f"{card} [data-edit-body]").click()
    page.wait_for_function(f"window.tinymce?.get('body-{comment}')?.initialized === true")


def _check(failures: list[str], label: str, ok: bool) -> None:
    print(f"{'pass' if ok else 'FAIL'}  {label}")
    if not ok:
        failures.append(label)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"))
