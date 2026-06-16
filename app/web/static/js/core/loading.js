function templateToHtml(templateId, selector, update) {
  const template = document.getElementById(templateId);
  if (!template) return "";
  const clone = template.content.cloneNode(true);
  const root = clone.querySelector(selector);
  if (!root) return "";
  update(root);
  const outer = document.createElement("div");
  outer.appendChild(root);
  return outer.innerHTML;
}

function getSpinnerHtml(text = "Loading…", extraClass = "") {
  return templateToHtml("global-spinner-template", ".dashboard-loading", div => {
    if (extraClass) div.classList.add(...extraClass.split(" ").filter(Boolean));
    div.querySelector(".spinner-text").textContent = text;
  });
}

function getTableStateHtml(colspan, stateHtml, cellClass = "") {
  return `
    <tr>
      <td colspan="${colspan}"${cellClass ? ` class="${cellClass}"` : ""}>
        ${stateHtml}
      </td>
    </tr>
  `;
}

function getTableSpinnerHtml(colspan, text = "Loading…", extraClass = "") {
  return getTableStateHtml(colspan, getSpinnerHtml(text, extraClass), "table-loading-cell");
}

function getEmptyStateHtml(message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return templateToHtml("global-empty-template", ".dashboard-empty", div => {
    if (extraClass) div.classList.add(...extraClass.split(" ").filter(Boolean));
    div.querySelector(".dashboard-state-icon").textContent = icon;
    div.querySelector(".empty-message").textContent = message;
    const subEl = div.querySelector(".empty-submessage");
    subEl.textContent = submessage || "";
    subEl.style.display = submessage ? "" : "none";
  });
}

function getTableEmptyStateHtml(colspan, message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return getTableStateHtml(colspan, getEmptyStateHtml(message, submessage, extraClass, icon));
}

function getErrorStateHtml(message = "Failed to load data. Please try again.", extraClass = "") {
  return templateToHtml("global-error-template", ".dashboard-error", div => {
    if (extraClass) div.classList.add(...extraClass.split(" ").filter(Boolean));
    div.querySelector(".error-message").textContent = message;
  });
}

function getTableErrorStateHtml(colspan, message = "Failed to load data. Please try again.", extraClass = "") {
  return getTableStateHtml(colspan, getErrorStateHtml(message, extraClass));
}
