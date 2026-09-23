// Upload: stop a file over the limit before it is sent. The host rejects large request bodies
// with its own error page, so the server's friendlier message would never be seen (rule F9).
document.addEventListener("change", (event) => {
  const input = event.target.closest("form[data-max-bytes] input[type=file]");
  if (!input) return;
  const file = input.files[0];
  const tooLarge = Boolean(file) && file.size > Number(input.form.dataset.maxBytes);
  input.form.querySelector("[data-too-large]").hidden = !tooLarge;
  input.setCustomValidity(tooLarge ? "This file is too large to import." : "");
});

document.addEventListener("submit", (event) => {
  if (!event.target.matches("form.upload")) return;
  const button = event.target.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Importing...";
});

// A page restored from the back-forward cache keeps the disabled button; undo that.
window.addEventListener("pageshow", () => {
  for (const button of document.querySelectorAll("form.upload button[type=submit]")) {
    button.disabled = false;
    button.textContent = "Import";
  }
});

// A link to one comment, such as one from the import report, opens that comment's card.
function openLinkedComment() {
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (target && target.matches("details.comment")) {
    target.open = true;
    target.scrollIntoView({ block: "start" });
  }
}
window.addEventListener("DOMContentLoaded", openLinkedComment);
window.addEventListener("hashchange", openLinkedComment);

// Panes: mark the clicked section or item as selected while the panes beside it load.
document.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-select]");
  if (!link) return;
  for (const other of link.closest("ul").querySelectorAll("a[aria-current]")) {
    other.removeAttribute("aria-current");
  }
  link.setAttribute("aria-current", "page");
});

// Tooltips: any element with data-tip shows its text in one floating box, placed against the
// viewport so a scrolling pane never clips it. Hover or keyboard focus shows it.
const tooltip = document.createElement("div");
tooltip.className = "tooltip";
tooltip.setAttribute("role", "tooltip");
tooltip.hidden = true;
document.body.append(tooltip);

function showTip(target) {
  tooltip.textContent = target.dataset.tip;
  tooltip.hidden = false;
  const box = target.getBoundingClientRect();
  const left = Math.min(
    Math.max(8, box.left + box.width / 2 - tooltip.offsetWidth / 2),
    window.innerWidth - tooltip.offsetWidth - 8,
  );
  const below = box.bottom + 6;
  const top =
    below + tooltip.offsetHeight > window.innerHeight - 8 ? box.top - tooltip.offsetHeight - 6 : below;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

const hideTip = () => {
  tooltip.hidden = true;
};

for (const type of ["mouseover", "focusin"]) {
  document.addEventListener(type, (event) => {
    const target = event.target.closest?.("[data-tip]");
    if (target) showTip(target);
  });
}
for (const type of ["mouseout", "focusout"]) {
  document.addEventListener(type, (event) => {
    if (event.target.closest?.("[data-tip]")) hideTip();
  });
}
document.addEventListener("scroll", hideTip, true);
// A "?" inside a label or a summary should explain, not focus the field or open the section.
document.addEventListener("click", (event) => {
  if (event.target.closest?.(".tip")) event.preventDefault();
});
