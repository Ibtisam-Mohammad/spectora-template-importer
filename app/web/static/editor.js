// The comment editor: which fields a comment's form shows, and the rich-text editor for its body.
//
// Rule E2: TinyMCE rewrites the HTML it loads, so a body is sent only when its content differs
// from what the editor showed when it opened. A form sent without the body leaves it unchanged.

(() => {
  const TINYMCE_URL = "https://cdn.jsdelivr.net/npm/tinymce@8.9.2/tinymce.min.js";
  const contentCss = document.currentScript.dataset.contentCss;
  const openedWith = new WeakMap(); // editor -> its content when it opened
  let loading = null;

  function loadTinyMce() {
    if (window.tinymce) return Promise.resolve(window.tinymce);
    loading ??= new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = TINYMCE_URL;
      script.referrerPolicy = "origin";
      script.onload = () => resolve(window.tinymce);
      script.onerror = () => {
        loading = null;
        reject(new Error("The text editor could not be loaded."));
      };
      document.head.append(script);
    });
    return loading;
  }

  const editors = () => (window.tinymce ? window.tinymce.get() : []);
  const isDirty = (editor) => editor.getContent() !== openedWith.get(editor);

  function stopEditing(editor) {
    const textarea = editor.getElement();
    const field = textarea.closest(".body-field");
    editor.remove();
    textarea.disabled = true;
    textarea.hidden = true;
    field.querySelector("[data-rendered]").hidden = false;
    field.querySelector("[data-edit-body]").hidden = false;
  }

  async function startEditing(button) {
    const field = button.closest(".body-field");
    const textarea = field.querySelector("textarea[data-body]");
    const tinymce = await loadTinyMce();
    for (const other of editors()) {
      if (other.getElement() === textarea) return;
      if (isDirty(other) && !confirm("Another comment has unsaved text changes. Discard them?")) {
        return;
      }
      stopEditing(other);
    }
    field.querySelector("[data-rendered]").hidden = true;
    button.hidden = true;
    textarea.disabled = false;
    textarea.hidden = false;
    const [editor] = await tinymce.init({
      target: textarea,
      license_key: "gpl",
      menubar: false,
      promotion: false,
      branding: false,
      plugins: "lists link table code autoresize",
      toolbar:
        "undo redo | fontsize | bold italic underline forecolor | bullist numlist | link table | code",
      valid_elements: "*[*]",
      entity_encoding: "raw",
      convert_urls: false,
      content_css: contentCss,
      body_class: "comment-body",
      sandbox_iframes_exclusions: [
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        "vimeo.com",
        "player.vimeo.com",
      ],
      min_height: 220,
    });
    openedWith.set(editor, editor.getContent());
    editor.focus();
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-body]");
    if (button) startEditing(button).catch((error) => alert(error.message));
  });

  document.addEventListener("htmx:configRequest", (event) => {
    const textarea = event.detail.elt.querySelector?.("textarea[data-body]");
    if (!textarea) return;
    const editor = window.tinymce?.get(textarea.id);
    if (editor && isDirty(editor)) {
      event.detail.parameters.body_html = editor.getContent();
    } else {
      delete event.detail.parameters.body_html;
    }
  });

  // Moving to another section or item replaces the comments; ask before losing text changes.
  document.addEventListener("htmx:confirm", (event) => {
    if (!event.detail.elt.matches?.("a[data-select]")) return;
    if (editors().some(isDirty) && !confirm("Leave without saving your text changes?")) {
      event.preventDefault();
    }
  });

  document.addEventListener("htmx:beforeCleanupElement", (event) => {
    if (event.target.matches?.("textarea[data-body]")) window.tinymce?.get(event.target.id)?.remove();
  });

  window.addEventListener("beforeunload", (event) => {
    if (editors().some(isDirty)) event.preventDefault();
  });

  // Which fields a form shows follows Spectora's editor: the answer format decides the answer
  // fields, and severity and recommendation belong to deficiencies. A field that holds a value
  // is always shown. No answer format shows no answer fields; a format Spectora does not
  // document shows them all, since it is unknown which apply.
  function showFields(form) {
    const format = form.querySelector("[data-answer-format]");
    const type = form.querySelector("[data-comment-type]");
    const known = (format.dataset.known || "").split(" ");
    const undocumented = format.value !== "" && !known.includes(format.value);
    for (const field of form.querySelectorAll("[data-formats]")) {
      const applies = field.dataset.formats.split(" ").includes(format.value);
      field.hidden = !(field.hasAttribute("data-keep") || applies || undocumented);
    }
    for (const field of form.querySelectorAll("[data-types]")) {
      const applies = field.dataset.types.split(" ").includes(type.value);
      field.hidden = !(field.hasAttribute("data-keep") || applies);
    }
  }

  document.addEventListener("change", (event) => {
    const form = event.target.closest("form.comment-form");
    if (form && event.target.matches("[data-answer-format], [data-comment-type]")) showFields(form);
  });

  htmx.onLoad((root) => {
    const forms = root.matches?.("form.comment-form") ? [root] : [];
    forms.push(...(root.querySelectorAll?.("form.comment-form") ?? []));
    forms.forEach(showFields);
  });

  // After the comments pane is replaced (a comment moved to another heading, was added, or was
  // reordered), bring the open comment into view.
  document.addEventListener("htmx:afterSettle", (event) => {
    if (event.detail.target?.id !== "comments-pane") return;
    document.querySelector("#comments-pane details.comment[open]")?.scrollIntoView({ block: "nearest" });
  });
})();
