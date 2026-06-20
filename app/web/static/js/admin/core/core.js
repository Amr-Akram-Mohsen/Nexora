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
    if (domain === "source" || domain === "store") {
      url = `/admin/providers/${domain}s/${id}/inspect`;
    } else if (domain === "rec") {
      const parts = id.split('-');
      url = `/admin/recommendations/matches/${parts[0]}/${parts[1]}/inspect`;
    } else if (["category", "brand", "topic", "section"].includes(domain)) {
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
