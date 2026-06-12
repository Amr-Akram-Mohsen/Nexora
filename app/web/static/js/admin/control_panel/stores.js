// ==============================
// ADMIN — STORES CONTROL PANEL
// stores.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  let currentPage = 1;
  let totalPages = 1;
  let perPage = 20;
  let searchDebounce = null;

  function getFilters() {
    return {
      search: (document.getElementById('stores-search') || {}).value || '',
    };
  }

  // ── Fetch & render stores ──────────────
  function loadStores(page) {
    currentPage = page || 1;
    const filters = getFilters();
    const params = new URLSearchParams({
      page: currentPage,
      per_page: perPage,
      ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    });

    const tbody = document.getElementById('stores-table-body');
    tbody.innerHTML = getTableSpinnerHtml(8, "Loading stores list…", "loading-height-md");

    fetch(`/admin/providers/stores?${params}`)
      .then(r => { if (!r.ok) throw new Error('Network error'); return r.json(); })
      .then(data => renderStores(data))
      .catch((err) => {
        console.error(err);
        tbody.innerHTML = getTableErrorStateHtml(8, "Failed to load stores.");
      });
  }

  function renderStores(data) {
    const stores = data.stores || [];
    totalPages   = data.pages || 1;
    const total  = data.total || 0;
    const from   = ((currentPage - 1) * perPage) + 1;
    const to     = Math.min(currentPage * perPage, total);
    const tbody  = document.getElementById('stores-table-body');

    // Update summary & pagination info
    document.getElementById('stores-count').textContent = total.toLocaleString();
    document.getElementById('stores-pagination-info').textContent =
      `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} stores`;
    document.getElementById('stores-page-indicator').textContent =
      `Page ${currentPage} of ${totalPages}`;
    document.getElementById('stores-prev-btn').disabled = currentPage <= 1;
    document.getElementById('stores-next-btn').disabled = currentPage >= totalPages;

    if (!stores.length) {
      tbody.innerHTML = getTableEmptyStateHtml(8, "No stores found.", "Try adjusting your search term.", "loading-height-md");
      return;
    }

    tbody.innerHTML = '';
    stores.forEach(st => {
      const tr = document.createElement('tr');

      const latestTime = st.latest_activity ? formatDate(st.latest_activity, true) : '—';
      const statusBadge = st.is_active
        ? `<span class="status-badge active">Active</span>`
        : `<span class="status-badge inactive">Inactive</span>`;

      let latestProductHtml = '—';
      if (st.latest_product) {
        latestProductHtml = `
          <a href="/admin/items?search=${st.latest_product.id}" class="overview-top-link-title text-deco-none font-bold">
            ${escapeHtml(st.latest_product.name)}
          </a>
          <div class="user-cell-email">ID: #${st.latest_product.id}</div>
        `;
      }

      tr.innerHTML = `
        <td>
          <span class="user-cell-name">#${st.id}</span>
          <div class="mt-3">${statusBadge}</div>
        </td>
        <td>
          <span class="user-cell-name">${escapeHtml(st.name)}</span>
          <div class="user-cell-email"><a href="${st.website}" target="_blank" class="text-muted">${escapeHtml(st.website)}</a></div>
          <div class="user-cell-email">slug: <code>${escapeHtml(st.slug)}</code></div>
        </td>
        <td>
          <span class="status-badge purple">
            ${escapeHtml(st.affiliate_network || 'Direct')}
          </span>
        </td>
        <td>
          <strong class="inspect-brand-purple">${st.product_count.toLocaleString()}</strong>
        </td>
        <td>
          <span class="font-bold text-foreground">${st.currency || 'USD'} (${st.country || 'US'})</span>
        </td>
        <td>
          <span class="text-foreground">${latestTime}</span>
        </td>
        <td class="cell-wrap-ellipsis">
          ${latestProductHtml}
        </td>
        <td>
          <div class="user-actions-group">
            <a href="/admin/items?source=${st.slug}" class="user-action-btn user-action-inspect inspect-btn text-deco-none d-inline-block">
              👁️ View Products
            </a>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // ── Utilities ────────────────────────────
  // Exposes global escapeHtml and formatDate from core.js

  // ── Event Wiring ─────────────────────────
  function init() {
    loadStores(1);

    // Search debounce
    document.getElementById('stores-search').addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => loadStores(1), 400);
    });

    // Per-page
    document.getElementById('stores-per-page').addEventListener('change', e => {
      perPage = parseInt(e.target.value, 10);
      loadStores(1);
    });

    // Pagination
    document.getElementById('stores-prev-btn').addEventListener('click', () => {
      if (currentPage > 1) loadStores(currentPage - 1);
    });
    document.getElementById('stores-next-btn').addEventListener('click', () => {
      if (currentPage < totalPages) loadStores(currentPage + 1);
    });

    // Reset filters
    document.getElementById('clear-stores-filters-btn').addEventListener('click', () => {
      document.getElementById('stores-search').value = '';
      loadStores(1);
    });

    // Refresh button
    document.getElementById('refresh-stores-btn').addEventListener('click', () => loadStores(currentPage));
  }

  document.addEventListener('DOMContentLoaded', init);
})();
