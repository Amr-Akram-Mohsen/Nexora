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
    this.filterKeys = config.filterKeys || {};
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
        let cleanKey;
        if (this.filterKeys && this.filterKeys[id]) {
          cleanKey = this.filterKeys[id];
        } else {
          // Fallback legacy regex mapping
          cleanKey = id.replace(/^(filter-item-|filter-|item-sort-|item-|user-)/, '').replace(/-/g, '_');
        }
        filters[cleanKey] = el.value;
      }
    });
    return filters;
  }

  load(page) {
    this.currentPage = page || 1;
    const tbody = document.getElementById(this.tbodyId);
    if (!tbody) return;

    renderTableSpinner(tbody, this.colspan, `Loading ${this.domain}...`);

    const filters = this.getFilters();
    const params = new URLSearchParams({
      page: this.currentPage,
      per_page: this.perPage,
      ...filters
    });

    if (!this.rowsEndpoint) {
      console.error(`rowsEndpoint is required for ${this.domain} controller.`);
      renderTableErrorState(tbody, this.colspan, `Configuration error.`);
      return;
    }

    // JS only fetches + injects. All row HTML is rendered by Jinja on the server.
    fetch(`${this.rowsEndpoint}?${params}`)
      .then(res => {
        if (!res.ok) throw new Error("Load error");
        const total = parseInt(res.headers.get("X-Total") || "0", 10);
        const pages = parseInt(res.headers.get("X-Pages") || "1", 10);
        this.totalPages = pages;
        return res.text().then(html => ({ html, total, headers: res.headers }));
      })
      .then(({ html, total, headers }) => {
        tbody.innerHTML = html;
        const from = total > 0 ? ((this.currentPage - 1) * this.perPage) + 1 : 0;
        const to = Math.min(this.currentPage * this.perPage, total);
        this.updatePagination(total, from, to);
        if (this.onLoaded) this.onLoaded({ total, headers });
      })
      .catch(err => {
        console.error(err);
        renderTableErrorState(tbody, this.colspan, `Failed to load ${this.domain}.`);
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

  updateStatsUI(stats, mapping) {
    if (!stats || !mapping) return;
    for (const [key, id] of Object.entries(mapping)) {
      const el = document.getElementById(id);
      if (el && stats[key] !== undefined && stats[key] !== null) {
        el.textContent = Number(stats[key]).toLocaleString();
      }
    }
  }
}

// ==============================
// INSPECT MODAL HELPER
// ==============================
window.openInspectModal = function(url, modalId, title) {
  const modal = document.getElementById(modalId);
  const titleEl = document.getElementById(`${modalId}-title`);
  if (titleEl && title) {
    titleEl.textContent = title;
  }
  
  if (modal) {
    modal.classList.add("active");
  }
  
  if (typeof fetchAndInjectHtml === "function") {
    return fetchAndInjectHtml(url, `${modalId}-body`, 'Loading details...');
  } else {
    console.error("fetchAndInjectHtml is not defined");
    return Promise.reject("fetchAndInjectHtml is missing");
  }
};

// ==============================
// GLOBAL INSPECT HANDLER
// ==============================
document.addEventListener("click", e => {
  const btn = e.target.closest('[data-action="global-inspect"]');
  if (!btn) return;
  
  const domain = btn.dataset.domain;
  const id = btn.dataset.id;
  const title = btn.dataset.title;
  let url = btn.dataset.url;
  
  if (!url) {
    if (domain === "rec") {
      const parts = id.split('-');
      url = `/admin/recommendations/matches/${parts[0]}/${parts[1]}/inspect`;
    } else if (["category", "brand", "topic", "section", "attribute", "gender_facet", "intent_facet", "price_tier_facet"].includes(domain)) {
      const plural = domain === "category" ? "categories" : `${domain}s`;
      url = `/admin/taxonomy/${plural}/${id}/inspect`;
    } else if (domain === "comment") {
      url = `/admin/interactions/comments/${id}/inspect`;
    } else {
      url = `/admin/${domain}s/${id}/inspect`;
    }
  }
  
  const modalId = `inspect-${domain}-modal`;
  const modalTitle = title ? `Inspect: ${title}` : `Inspect ${domain.charAt(0).toUpperCase() + domain.slice(1)}`;
  
  if (typeof window.openInspectModal === "function") {
    window.openInspectModal(url, modalId, modalTitle);
  }
});

// ==============================
// GENERIC CRUD BOOTSTRAP
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const crudMarker = document.querySelector('[data-crud-domain]');
  if (crudMarker) {
    const domain = crudMarker.dataset.crudDomain;
    const endpoint = crudMarker.dataset.crudEndpoint || `/admin/${domain}`;
    const rowsEndpoint = crudMarker.dataset.crudRowsEndpoint || `${endpoint}/rows`;
    
    // Only auto-init if there isn't already a script handling this domain
    if (!window[`${domain}Controller`]) {
      const controller = new AdminListController({
        domain: domain,
        endpoint: endpoint,
        rowsEndpoint: rowsEndpoint,
        autoInit: false
      });
      controller.init();
      window[`${domain}Controller`] = controller;
    }
  }
});

// ==============================
// GLOBAL API CONTRACT & UTILITIES
// ==============================
/*
 * Implicit Globals Documentation (provided by base layout / helpers.js):
 * - getTableSpinnerHtml(colspan): Returns HTML string for table loading row
 * - getTableErrorStateHtml(colspan, msg): Returns HTML string for table error row
 * - applyUrlFilters(formId, baseUrl): Redirects browser applying form filters to URL
 * - showToast(msg, type): Displays a toast notification
 * - showModal(title, body, onConfirm): Displays a confirmation modal
 */

/**
 * Shared utility for admin tab switching logic.
 * @param {string} tabsId - The ID of the tabs container
 * @param {function} onSwitch - Callback fired when a tab is selected, receives (tabId)
 */
function initAdminTabs(tabsId, onSwitch) {
  const tabsContainer = document.getElementById(tabsId);
  if (!tabsContainer) return;

  tabsContainer.addEventListener("click", function(e) {
    const btn = e.target.closest(".admin-tab-btn");
    if (!btn || btn.classList.contains("active")) return;

    // Update active tab buttons
    const container = btn.closest(".admin-tabs");
    container.querySelectorAll(".admin-tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    // Update active panels
    const tabId = btn.dataset.tab;
    const wrapper = document.querySelector(".admin-tab-panels") || document;
    wrapper.querySelectorAll(".admin-tab-panel").forEach(p => {
      p.classList.add("is-hidden");
      p.classList.remove("active");
      p.style.display = ""; // clear inline display if it existed
    });
    
    // Look for ID either exactly as tabId, or prefixed with tab-panel-
    const activePanel = document.getElementById(`tab-panel-${tabId}`) || document.getElementById(tabId);
    if (activePanel) {
      activePanel.classList.remove("is-hidden");
      activePanel.classList.add("active");
    }

    if (onSwitch && typeof onSwitch === "function") {
      onSwitch(tabId);
    }
  });
}

/**
 * Initializes sidebar toggle and overlay behavior.
 * Extracted from admin_base.html inline script.
 */
function initSidebar() {
  const sidebar = document.getElementById('admin-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const toggleBtn = document.getElementById('sidebar-toggle');
  const layout = document.querySelector('.admin-layout');
  const isMobile = window.innerWidth <= 768;
  
  if (!sidebar || !layout || !toggleBtn) return;

  // Restore state
  const savedState = localStorage.getItem('admin-sidebar-collapsed');
  if (savedState === 'true' && !isMobile) {
    layout.classList.add('collapsed');
  } else if (isMobile) {
    // On mobile, start collapsed
    layout.classList.add('collapsed');
  }

  function toggleSidebar() {
    layout.classList.toggle('collapsed');
    if (!isMobile) {
      localStorage.setItem('admin-sidebar-collapsed', layout.classList.contains('collapsed'));
    }
  }

  toggleBtn.addEventListener('click', toggleSidebar);

  if (overlay) {
    overlay.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        layout.classList.add('collapsed');
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", initSidebar);

/**
 * Standardized template rendering functions
 */
function renderSpinner(container, text = "Loading…") {
  if (!container) return;
  const tpl = document.getElementById('global-spinner-template');
  if (!tpl) {
      container.innerHTML = `<div class='dashboard-loading'><div class='spinner'></div><p class='spinner-text'>${text}</p></div>`;
      return;
  }
  const clone = tpl.content.cloneNode(true);
  if (text) {
      const textEl = clone.querySelector('.spinner-text');
      if (textEl) textEl.textContent = text;
  }
  container.innerHTML = '';
  container.appendChild(clone);
}

function renderEmptyState(container, message = "No items found.", submessage = "", iconClass = "") {
  if (!container) return;
  const tpl = document.getElementById('global-empty-template');
  if (!tpl) return;
  const clone = tpl.content.cloneNode(true);
  
  if (message) {
      const msgEl = clone.querySelector('.empty-message');
      if (msgEl) msgEl.textContent = message;
  }
  if (submessage) {
      const subEl = clone.querySelector('.empty-submessage');
      if (subEl) subEl.textContent = submessage;
  }
  if (iconClass) {
      const iconEl = clone.querySelector('.dashboard-state-icon i');
      if (iconEl) {
          iconEl.className = iconClass;
      }
  }
  container.innerHTML = '';
  container.appendChild(clone);
}

function renderErrorState(container, message = "Failed to load data. Please try again.") {
  if (!container) return;
  const tpl = document.getElementById('global-error-template');
  if (!tpl) return;
  const clone = tpl.content.cloneNode(true);
  if (message) {
      const msgEl = clone.querySelector('.error-message');
      if (msgEl) msgEl.textContent = message;
  }
  container.innerHTML = '';
  container.appendChild(clone);
}

function renderTableSpinner(tbody, colspan, text) {
  if (!tbody) return;
  const tr = document.createElement('tr');
  const td = document.createElement('td');
  td.colSpan = colspan || 1;
  td.className = 'table-loading-cell';
  renderSpinner(td, text);
  tr.appendChild(td);
  tbody.innerHTML = '';
  tbody.appendChild(tr);
}

function renderTableErrorState(tbody, colspan, text) {
  if (!tbody) return;
  const tr = document.createElement('tr');
  const td = document.createElement('td');
  td.colSpan = colspan || 1;
  td.className = 'table-error-cell';
  renderErrorState(td, text);
  tr.appendChild(td);
  tbody.innerHTML = '';
  tbody.appendChild(tr);
}
