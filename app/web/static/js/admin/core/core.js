// ==============================
// UTILITIES
// ==============================
function getUrlQueryParams() {
  const params = {};
  const searchParams = new URLSearchParams(window.location.search);
  for (const [key, value] of searchParams.entries()) {
    params[key] = value;
  }
  return params;
}

function applyUrlFilters(filterMap) {
  const params = getUrlQueryParams();
  for (const [paramKey, elementId] of Object.entries(filterMap)) {
    if (params[paramKey] !== undefined) {
      const el = document.getElementById(elementId);
      if (el) {
        el.value = params[paramKey];
      }
    }
  }
}

function formatDate(str, includeTime = false) {
  if (!str) return "—";
  try {
    const d = new Date(str);
    const dateStr = d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    if (includeTime) {
      return dateStr + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }
    return dateStr;
  } catch {
    return str;
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "—";
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}



// ==============================
// STATE TEMPLATE HELPERS
// ==============================
function addClasses(el, classNames = "") {
  if (classNames) el.classList.add(...classNames.split(" ").filter(Boolean));
}

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
    addClasses(div, extraClass);
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
    addClasses(div, extraClass);
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
    addClasses(div, extraClass);
    div.querySelector(".error-message").textContent = message;
  });
}

function getTableErrorStateHtml(colspan, message = "Failed to load data. Please try again.", extraClass = "") {
  return getTableStateHtml(colspan, getErrorStateHtml(message, extraClass));
}

function showToast(msg, type = "success") {
  const toast = document.getElementById("settings-toast");
  if (!toast) return;

  toast.textContent = msg;
  toast.className = `settings-toast settings-toast-${type} settings-toast-show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove("settings-toast-show");
  }, 3200);
}

function fetchAndInjectHtml(url, targetElementId, loadingText = "Loading...", colspan = null, options = {}) {
  const container = document.getElementById(targetElementId);
  if (!container) return Promise.resolve();

  if (container.tagName === 'TBODY' && colspan) {
    container.innerHTML = getTableSpinnerHtml(colspan, loadingText);
  } else {
    container.innerHTML = getSpinnerHtml(loadingText);
  }

  return fetch(url)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load ${url}`);
      const isEmpty = res.headers.get("X-Empty") === "true";
      return res.text().then(html => ({ html, isEmpty }));
    })
    .then(({ html, isEmpty }) => {
      if (isEmpty && options.hideElementIdOnEmpty) {
        const elToHide = document.getElementById(options.hideElementIdOnEmpty);
        if (elToHide) {
          elToHide.style.display = "none";
        }
      } else {
        if (options.hideElementIdOnEmpty) {
          const elToShow = document.getElementById(options.hideElementIdOnEmpty);
          if (elToShow) {
            elToShow.style.display = options.displayStyle || "block";
          }
        }
        container.innerHTML = html;
      }
    })
    .catch(err => {
      console.error(err);
      if (container.tagName === 'TBODY' && colspan) {
        container.innerHTML = getTableErrorStateHtml(colspan, "Failed to load data.");
      } else {
        container.innerHTML = getErrorStateHtml("Failed to load data.");
      }
    });
}


// ==============================
// ADMIN LIST CONTROLLER CLASS
// ==============================
class AdminListController {
  constructor(config) {
    this.domain = config.domain;
    this.rowsEndpoint = config.rowsEndpoint;
    this.tbodyId = config.tbodyId || `${config.domain}-table-body`;
    this.searchId = config.searchId || `${config.domain}-search`;
    this.filterIds = config.filterIds || [];
    this.perPageId = config.perPageId || `${config.domain}-per-page`;
    this.prevBtnId = config.prevBtnId || `${config.domain}-prev-btn`;
    this.nextBtnId = config.nextBtnId || `${config.domain}-next-btn`;
    this.indicatorId = config.indicatorId || `${config.domain}-page-indicator`;
    this.infoId = config.infoId || `${config.domain}-pagination-info`;
    this.countId = config.countId || `${config.domain}-count`;
    this.clearBtnId = config.clearBtnId || `clear-${config.domain}-filters-btn`;
    this.refreshBtnId = config.refreshBtnId || `refresh-${config.domain}-btn`;

    this.onLoaded = config.onLoaded;
    this.colspan = config.colspan || 5;

    this.currentPage = 1;
    this.totalPages = 1;
    this.perPage = config.defaultPerPage || 20;
    this.searchDebounce = null;

    if (config.autoInit !== false) {
      document.addEventListener("DOMContentLoaded", () => this.init());
    }
  }

  init() {
    this.bindEvents();
    this.load(1);
  }

  getFilters() {
    const filters = {};
    const searchEl = document.getElementById(this.searchId);
    if (searchEl && searchEl.value.trim()) {
      filters.search = searchEl.value.trim();
    }
    this.filterIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        const cleanKey = id.replace(/^(filter-item-|filter-|item-sort-|item-)/, '').replace(/-/g, '_');
        filters[cleanKey] = el.value;
      }
    });
    return filters;
  }

  load(page) {
    this.currentPage = page || 1;
    const tbody = document.getElementById(this.tbodyId);
    if (!tbody) return;

    tbody.innerHTML = getTableSpinnerHtml(this.colspan, `Loading ${this.domain}...`, "loading-height-sm");

    const filters = this.getFilters();
    const params = new URLSearchParams({
      page: this.currentPage,
      per_page: this.perPage,
      ...filters
    });

    if (!this.rowsEndpoint) {
      console.error(`rowsEndpoint is required for ${this.domain} controller.`);
      tbody.innerHTML = getTableErrorStateHtml(this.colspan, `Configuration error.`);
      return;
    }

    // JS only fetches + injects. All row HTML is rendered by Jinja on the server.
    fetch(`${this.rowsEndpoint}?${params}`)
      .then(res => {
        if (!res.ok) throw new Error("Load error");
        const total = parseInt(res.headers.get("X-Total") || "0", 10);
        const pages = parseInt(res.headers.get("X-Pages") || "1", 10);
        this.totalPages = pages;
        return res.text().then(html => ({ html, total }));
      })
      .then(({ html, total }) => {
        tbody.innerHTML = html;
        const from = total > 0 ? ((this.currentPage - 1) * this.perPage) + 1 : 0;
        const to = Math.min(this.currentPage * this.perPage, total);
        this.updatePagination(total, from, to);
        if (this.onLoaded) this.onLoaded({ total });
      })
      .catch(err => {
        console.error(err);
        tbody.innerHTML = getTableErrorStateHtml(this.colspan, `Failed to load ${this.domain}.`);
      });
  }

  updatePagination(total, from, to) {
    const countEl = document.getElementById(this.countId);
    const infoEl = document.getElementById(this.infoId);
    const pageEl = document.getElementById(this.indicatorId);
    const prevBtn = document.getElementById(this.prevBtnId);
    const nextBtn = document.getElementById(this.nextBtnId);

    if (countEl) countEl.textContent = total.toLocaleString();
    if (infoEl) infoEl.textContent = `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} ${this.domain}`;
    if (pageEl) pageEl.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
    if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
    if (nextBtn) nextBtn.disabled = this.currentPage >= this.totalPages;
  }

  bindEvents() {
    const searchEl = document.getElementById(this.searchId);
    if (searchEl) {
      searchEl.addEventListener("input", () => {
        clearTimeout(this.searchDebounce);
        this.searchDebounce = setTimeout(() => this.load(1), 400);
      });
    }

    this.filterIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener("change", () => this.load(1));
      }
    });

    const perPageEl = document.getElementById(this.perPageId);
    if (perPageEl) {
      perPageEl.addEventListener("change", e => {
        this.perPage = parseInt(e.target.value, 10);
        this.load(1);
      });
    }

    const prevEl = document.getElementById(this.prevBtnId);
    if (prevEl) {
      prevEl.addEventListener("click", () => {
        if (this.currentPage > 1) this.load(this.currentPage - 1);
      });
    }

    const nextEl = document.getElementById(this.nextBtnId);
    if (nextEl) {
      nextEl.addEventListener("click", () => {
        if (this.currentPage < this.totalPages) this.load(this.currentPage + 1);
      });
    }

    const clearEl = document.getElementById(this.clearBtnId);
    if (clearEl) {
      clearEl.addEventListener("click", () => {
        if (searchEl) searchEl.value = "";
        this.filterIds.forEach(id => {
          const el = document.getElementById(id);
          if (el) el.value = el.dataset.defaultValue || "";
        });
        this.load(1);
      });
    }

    const refreshEl = document.getElementById(this.refreshBtnId);
    if (refreshEl) {
      refreshEl.addEventListener("click", () => this.load(this.currentPage));
    }
  }
}



// ==============================
// MODAL SYSTEM
// ==============================
let activeModalCallback = null;

function initModalSystem() {
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (!overlay || overlay._initialized) return;

  const cancelBtn = document.getElementById("modal-cancel");
  const confirmBtn = document.getElementById("modal-confirm");

  if (cancelBtn) cancelBtn.onclick = closeModal;
  if (confirmBtn) {
    confirmBtn.onclick = () => {
      if (activeModalCallback) activeModalCallback();
      closeModal();
    };
  }

  overlay.onclick = (e) => {
    if (e.target === overlay) closeModal();
  };

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  overlay._initialized = true;
}

function showModal(title, body, callback) {
  initModalSystem();
  const titleEl = document.getElementById("modal-title");
  const bodyEl = document.getElementById("modal-body");
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (titleEl) titleEl.textContent = title;
  if (bodyEl) bodyEl.textContent = body;
  activeModalCallback = callback;
  if (overlay) overlay.classList.add("active");
}

function closeModal() {
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (overlay) overlay.classList.remove("active");
  activeModalCallback = null;
}

// ==============================
// GLOBAL MODAL EVENT DELEGATION
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("click", (e) => {
    // Backdrop click
    if (e.target.classList.contains("dashboard-modal-overlay")) {
      e.target.classList.remove("active");
      return;
    }
    // Dismiss button click
    const dismissBtn = e.target.closest("[data-dismiss='modal'], .dashboard-modal-close-x");
    if (dismissBtn) {
      const modal = dismissBtn.closest(".dashboard-modal-overlay");
      if (modal) {
        modal.classList.remove("active");
      }
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const activeModal = document.querySelector(".dashboard-modal-overlay.active");
      if (activeModal) {
        activeModal.classList.remove("active");
      }
    }
  });
});

function renderInteractionBreakdown(containerId) {
  fetchAndInjectHtml('/admin/dashboard/widget/interactions-breakdown', containerId, 'Loading breakdown...');
}
