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
function getSpinnerHtml(text = "Loading…", extraClass = "") {
  const template = document.getElementById("global-spinner-template");
  if (!template) {
    return `
      <div class="dashboard-loading ${extraClass}">
        <div class="spinner"></div>
        <p>${escapeHtml(text)}</p>
      </div>
    `;
  }
  const clone = template.content.cloneNode(true);
  const div = clone.querySelector(".dashboard-loading");
  if (extraClass) div.classList.add(...extraClass.split(" ").filter(c => c));
  div.querySelector(".spinner-text").textContent = text;
  const outer = document.createElement("div");
  outer.appendChild(div);
  return outer.innerHTML;
}

function getTableSpinnerHtml(colspan, text = "Loading…", extraClass = "") {
  return `
    <tr>
      <td colspan="${colspan}" class="table-loading-cell">
        ${getSpinnerHtml(text, extraClass)}
      </td>
    </tr>
  `;
}

function getEmptyStateHtml(message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  const template = document.getElementById("global-empty-template");
  if (!template) {
    return `
      <div class="dashboard-empty ${extraClass}">
        <span class="dashboard-state-icon">${icon}</span>
        <p>${escapeHtml(message)}</p>
        ${submessage ? `<p class="dashboard-empty-subtext">${escapeHtml(submessage)}</p>` : ""}
      </div>
    `;
  }
  const clone = template.content.cloneNode(true);
  const div = clone.querySelector(".dashboard-empty");
  if (extraClass) div.classList.add(...extraClass.split(" ").filter(c => c));
  div.querySelector(".dashboard-state-icon").textContent = icon;
  div.querySelector(".empty-message").textContent = message;
  const subEl = div.querySelector(".empty-submessage");
  if (submessage) {
    subEl.textContent = submessage;
    subEl.style.display = "";
  } else {
    subEl.style.display = "none";
  }
  const outer = document.createElement("div");
  outer.appendChild(div);
  return outer.innerHTML;
}

function getTableEmptyStateHtml(colspan, message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return `
    <tr>
      <td colspan="${colspan}">
        ${getEmptyStateHtml(message, submessage, extraClass, icon)}
      </td>
    </tr>
  `;
}

function getErrorStateHtml(message = "Failed to load data. Please try again.", extraClass = "") {
  const template = document.getElementById("global-error-template");
  if (!template) {
    return `
      <div class="dashboard-error ${extraClass}">
        <span class="dashboard-error-icon">⚠️</span>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  }
  const clone = template.content.cloneNode(true);
  const div = clone.querySelector(".dashboard-error");
  if (extraClass) div.classList.add(...extraClass.split(" ").filter(c => c));
  div.querySelector(".error-message").textContent = message;
  const outer = document.createElement("div");
  outer.appendChild(div);
  return outer.innerHTML;
}

function getTableErrorStateHtml(colspan, message = "Failed to load data. Please try again.", extraClass = "") {
  return `
    <tr>
      <td colspan="${colspan}">
        ${getErrorStateHtml(message, extraClass)}
      </td>
    </tr>
  `;
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


// ==============================
// ADMIN LIST CONTROLLER CLASS
// ==============================
class AdminListController {
  constructor(config) {
    this.domain = config.domain;
    this.endpoint = config.endpoint || `/admin/${config.domain}/`;
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
    this.rowTemplateId = config.rowTemplateId || `${config.domain}-row-template`;
    
    this.renderRow = config.renderRow;
    this.onLoaded = config.onLoaded;
    this.colspan = config.colspan || 5;
    this.itemsKey = config.itemsKey || "items";
    
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
    
    fetch(`${this.endpoint}?${params}`)
      .then(res => {
        if (!res.ok) throw new Error("Load error");
        return res.json();
      })
      .then(data => {
        const items = Array.isArray(data) ? data : (data[this.itemsKey] || data.items || []);
        this.totalPages = data.pages || 1;
        const total = data.total !== undefined ? data.total : (Array.isArray(data) ? data.length : 0);
        
        const from = ((this.currentPage - 1) * this.perPage) + 1;
        const to = Math.min(this.currentPage * this.perPage, total);
        
        this.render(items, tbody);
        this.updatePagination(total, from, to);
        if (this.onLoaded) this.onLoaded(data);
      })
      .catch(err => {
        console.error(err);
        tbody.innerHTML = getTableErrorStateHtml(this.colspan, `Failed to load ${this.domain}.`);
      });
  }
  
  render(items, tbody) {
    tbody.innerHTML = "";
    if (items.length === 0) {
      tbody.innerHTML = getTableEmptyStateHtml(this.colspan, `No ${this.domain} found.`, "Adjust your search or filters.", "loading-height-sm");
      return;
    }
    
    const template = document.getElementById(this.rowTemplateId);
    items.forEach(item => {
      let node;
      if (this.renderRow) {
        node = this.renderRow(item);
      } else if (template) {
        node = template.content.cloneNode(true);
      }
      
      if (node) {
        tbody.appendChild(node);
      }
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
  const container = document.getElementById(containerId);
  if (!container) return;

  fetch('/admin/interactions/stats')
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";
      const templateGrid = document.getElementById("overview-breakdown-template");
      if (!templateGrid) return;
      const grid = templateGrid.content.cloneNode(true).querySelector(".overview-breakdown-grid");

      const items = [
        { label: "Views", key: "views", icon: "👁️" },
        { label: "Comments", key: "comments", icon: "💬" },
        { label: "Likes", key: "likes", icon: "👍" },
        { label: "Dislikes", key: "dislikes", icon: "👎" },
        { label: "Saves", key: "saves", icon: "🔖" },
        { label: "Item Clicks", key: "item_clicks", icon: "🛒" },
      ];
      const total = data.total || 1;
      const templateRow = document.getElementById("overview-breakdown-row-template");

      items.forEach(it => {
        const val = data[it.key] || 0;
        const pct = Math.round((val / total) * 100);

        const clone = templateRow.content.cloneNode(true);
        clone.querySelector(".overview-breakdown-icon").textContent = it.icon;
        clone.querySelector(".overview-breakdown-label").textContent = it.label;
        clone.querySelector(".overview-breakdown-bar").style.width = `${pct}%`;
        clone.querySelector(".overview-breakdown-val").textContent = val.toLocaleString();
        clone.querySelector(".overview-breakdown-pct").textContent = `${pct}%`;
        grid.appendChild(clone);
      });

      container.appendChild(grid);
    })
    .catch(() => {
      container.innerHTML = getErrorStateHtml("Could not load interaction data.");
    });
}

