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

  // Where a field sits follows Spectora's editor: the answer format decides the answer fields,
  // and severity and recommendation belong to deficiencies. Those fields sit in the main grid;
  // the rest wait under "Other fields", so every field can still be filled. A field holding a
  // value always stays in the main grid. A format Spectora does not document keeps every answer
  // field there, since it is unknown which apply. CSS order keeps each grid in a fixed order.
  function showFields(form) {
    const format = form.querySelector("[data-answer-format]");
    const type = form.querySelector("[data-comment-type]");
    const main = form.querySelector("[data-main-fields]");
    const other = form.querySelector("[data-other-fields]");
    const known = (format.dataset.known || "").split(" ");
    const undocumented = format.value !== "" && !known.includes(format.value);
    for (const field of form.querySelectorAll("[data-order]")) {
      field.style.order = field.dataset.order;
      let belongs = field.hasAttribute("data-keep");
      if (field.dataset.formats) {
        belongs ||= undocumented || field.dataset.formats.split(" ").includes(format.value);
      }
      if (field.dataset.types) belongs ||= field.dataset.types.split(" ").includes(type.value);
      const home = belongs ? main : other;
      if (field.parentElement !== home) home.append(field);
    }
    form.querySelector("[data-other-count]").textContent = other.children.length;
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

  // Pick lists: a text field with a dropdown of the values this template already uses (from a
  // datalist in the comments pane), most used first. The arrow or a click shows them all; typing
  // narrows them; anything typed is kept, so a new value is always possible.
  function comboValues(input) {
    const source = document.getElementById(input.dataset.combo);
    return source ? [...source.options].map((o) => ({ value: o.value, count: o.dataset.count })) : [];
  }

  function comboOption(value, count, selected) {
    const option = document.createElement("span");
    option.className = "combo-option";
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(selected));
    option.dataset.value = value;
    const label = document.createElement("span");
    label.textContent = value.trim();
    const uses = document.createElement("span");
    uses.className = "combo-count";
    uses.textContent = count === "1" ? "1 comment" : count + " comments";
    option.append(label, uses);
    return option;
  }

  function openCombo(combo, narrow) {
    const input = combo.querySelector("input");
    const list = combo.querySelector(".combo-list");
    const query = narrow ? input.value.trim().toLowerCase() : "";
    const values = comboValues(input).filter((v) => v.value.trim().toLowerCase().includes(query));
    list.replaceChildren(...values.map((v) => comboOption(v.value, v.count, v.value === input.value)));
    if (!values.length) {
      const empty = document.createElement("span");
      empty.className = "combo-empty";
      empty.textContent = query
        ? "Not used elsewhere in this template. What you typed is kept."
        : "No values used in this template yet. Type one.";
      list.append(empty);
    }
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }

  function closeCombos(except) {
    for (const combo of document.querySelectorAll(".combo")) {
      if (combo === except) continue;
      combo.querySelector(".combo-list").hidden = true;
      combo.querySelector("input").setAttribute("aria-expanded", "false");
    }
  }

  function pick(option) {
    const input = option.closest(".combo").querySelector("input");
    input.value = option.dataset.value;
    closeCombos();
    input.focus();
  }

  document.addEventListener("mousedown", (event) => {
    const option = event.target.closest(".combo-option");
    if (option) {
      event.preventDefault();
      pick(option);
      return;
    }
    const combo = event.target.closest(".combo");
    closeCombos(combo);
    if (!combo) return;
    const list = combo.querySelector(".combo-list");
    if (event.target.closest(".combo-toggle")) {
      event.preventDefault();
      if (list.hidden) openCombo(combo, false);
      else closeCombos();
      combo.querySelector("input").focus();
    } else if (event.target.matches("input") && list.hidden) {
      openCombo(combo, false);
    }
  });

  document.addEventListener("input", (event) => {
    const combo = event.target.closest?.(".combo");
    if (combo) openCombo(combo, true);
  });

  document.addEventListener("keydown", (event) => {
    const combo = event.target.closest?.(".combo");
    if (!combo) return;
    const list = combo.querySelector(".combo-list");
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (list.hidden) openCombo(combo, false);
      const options = [...list.querySelectorAll(".combo-option")];
      const active = list.querySelector(".combo-option.active");
      const step = event.key === "ArrowDown" ? 1 : -1;
      const next = options[(options.indexOf(active) + step + options.length) % options.length];
      active?.classList.remove("active");
      next?.classList.add("active");
      next?.scrollIntoView({ block: "nearest" });
    } else if (event.key === "Enter" && !list.hidden) {
      const active = list.querySelector(".combo-option.active");
      event.preventDefault();
      if (active) pick(active);
      else closeCombos();
    } else if (event.key === "Escape" && !list.hidden) {
      event.preventDefault();
      closeCombos();
    } else if (event.key === "Tab") {
      closeCombos();
    }
  });

  // After the comments pane is replaced (a comment moved to another heading, was added, or was
  // reordered), bring the open comment into view.
  document.addEventListener("htmx:afterSettle", (event) => {
    if (event.detail.target?.id !== "comments-pane") return;
    document.querySelector("#comments-pane details.comment[open]")?.scrollIntoView({ block: "nearest" });
  });
})();
