// ==============================
// ADMIN — ITEMS CONTROL PANEL
// items.js
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
      search:    (document.getElementById('item-search') || {}).value || '',
      brand:     (document.getElementById('filter-item-brand') || {}).value || '',
      category:  (document.getElementById('filter-item-category') || {}).value || '',
      item_type: (document.getElementById('filter-item-type') || {}).value || '',
      sort_by:   (document.getElementById('item-sort-by') || {}).value || 'id',
      sort_dir:  (document.getElementById('item-sort-dir') || {}).value || 'desc',
    };
  }

  // ── Fetch meta for dropdowns ────────────
  function loadMeta() {
    fetch('/admin/items/meta')
      .then(r => r.json())
      .then(data => {
        const brandSel = document.getElementById('filter-item-brand');
        const catSel   = document.getElementById('filter-item-category');
        const typeSel  = document.getElementById('filter-item-type');

        (data.brands || []).forEach(b => {
          const opt = document.createElement('option');
          opt.value = b.slug; opt.textContent = b.name;
          brandSel.appendChild(opt);
        });
        (data.categories || []).forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.slug; opt.textContent = c.name;
          catSel.appendChild(opt);
        });
        (data.item_types || []).forEach(t => {
          const opt = document.createElement('option');
          opt.value = t; opt.textContent = t.charAt(0).toUpperCase() + t.slice(1);
          typeSel.appendChild(opt);
        });
      })
      .catch(() => {});
  }

  // ── Fetch & render items ────────────────
  function loadItems(page) {
    currentPage = page || 1;
    const filters = getFilters();
    const params = new URLSearchParams({
      page: currentPage,
      per_page: perPage,
      ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    });

    const tbody = document.getElementById('items-table-body');
    tbody.innerHTML = `<tr><td colspan="8" class="table-loading-cell">
      <div class="dashboard-loading loading-height-md"><div class="spinner"></div><p>Loading…</p></div>
    </td></tr>`;

    fetch(`/admin/items/?${params}`)
      .then(r => { if (!r.ok) throw new Error('Network error'); return r.json(); })
      .then(data => renderItems(data))
      .catch(() => {
        tbody.innerHTML = `<tr><td colspan="8" class="table-loading-cell">
          <div class="dashboard-error"><span style="font-size:2rem">⚠️</span><p>Failed to load products.</p></div>
        </td></tr>`;
      });
  }

  function renderItems(data) {
    const items   = data.items || [];
    totalPages    = data.pages || 1;
    const total   = data.total || 0;
    const from    = ((currentPage - 1) * perPage) + 1;
    const to      = Math.min(currentPage * perPage, total);
    const tbody   = document.getElementById('items-table-body');

    // Update summary & pagination info
    document.getElementById('items-count').textContent = total.toLocaleString();
    document.getElementById('items-pagination-info').textContent =
      `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} products`;
    document.getElementById('items-page-indicator').textContent =
      `Page ${currentPage} of ${totalPages}`;
    document.getElementById('items-prev-btn').disabled = currentPage <= 1;
    document.getElementById('items-next-btn').disabled = currentPage >= totalPages;

    if (!items.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="table-loading-cell">
        <div class="dashboard-empty">
          <span style="font-size:2.5rem;margin-bottom:1rem">📭</span>
          <p>No products found. Try adjusting your filters.</p>
        </div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = '';
    items.forEach(item => {
      const tr = document.createElement('tr');
      const priceStr = item.min_price != null
        ? `${Number(item.min_price).toFixed(2)} ${item.currency || ''}`
        : '—';
      const ratingStr = item.rating != null ? `⭐ ${Number(item.rating).toFixed(1)}` : '—';

      tr.innerHTML = `
        <td>
          <span class="user-cell-name">#${item.id}</span>
          <div class="user-cell-email">${item.item_type}</div>
        </td>
        <td>
          <span class="user-cell-name">${escapeHtml(item.name)}</span>
          <div class="user-cell-email">${escapeHtml(item.brand)} · ${escapeHtml(item.category)}</div>
        </td>
        <td>${priceStr}</td>
        <td>${ratingStr}</td>
        <td>${item.store_count}</td>
        <td>${(item.click_count || 0).toLocaleString()}</td>
        <td>
          <span class="user-cell-email">${formatDate(item.created_at)}</span>
        </td>
        <td>
          <div class="user-actions-group">
            <button class="user-action-btn user-action-delete"
              data-action="delete-item"
              data-item-id="${item.id}"
              data-item-name="${escapeHtml(item.name)}">
              🗑 Delete
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // ── Delete ───────────────────────────────
  function deleteItem(id, name, btn) {
    showModal(
      'Delete Product',
      `Are you sure you want to permanently delete "${name}"? This will remove all variants and store links.`,
      () => {
        if (btn) { btn.disabled = true; btn.textContent = 'Deleting…'; }
        fetch(`/admin/items/${id}`, { method: 'DELETE' })
          .then(r => r.json())
          .then(d => {
            if (d.success) {
              showToast(d.message || 'Product deleted.', 'success');
              loadItems(currentPage);
            } else {
              showToast(d.error || 'Delete failed.', 'error');
              if (btn) { btn.disabled = false; btn.textContent = '🗑 Delete'; }
            }
          })
          .catch(() => {
            showToast('Delete failed. Please try again.', 'error');
            if (btn) { btn.disabled = false; btn.textContent = '🗑 Delete'; }
          });
      }
    );
  }

  // ── Utilities ────────────────────────────
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '—';
    return div.innerHTML;
  }

  function formatDate(str) {
    if (!str) return '—';
    try { return new Date(str).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); }
    catch { return str; }
  }

  // ── Event Wiring ─────────────────────────
  function init() {
    loadMeta();
    loadItems(1);

    // Search debounce
    document.getElementById('item-search').addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => loadItems(1), 400);
    });

    // Filter selects
    ['filter-item-brand', 'filter-item-category', 'filter-item-type',
     'item-sort-by', 'item-sort-dir'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', () => loadItems(1));
    });

    // Per-page
    document.getElementById('items-per-page').addEventListener('change', e => {
      perPage = parseInt(e.target.value, 10);
      loadItems(1);
    });

    // Pagination
    document.getElementById('items-prev-btn').addEventListener('click', () => {
      if (currentPage > 1) loadItems(currentPage - 1);
    });
    document.getElementById('items-next-btn').addEventListener('click', () => {
      if (currentPage < totalPages) loadItems(currentPage + 1);
    });

    // Reset filters
    document.getElementById('clear-item-filters-btn').addEventListener('click', () => {
      document.getElementById('item-search').value = '';
      document.getElementById('filter-item-brand').value = '';
      document.getElementById('filter-item-category').value = '';
      document.getElementById('filter-item-type').value = '';
      document.getElementById('item-sort-by').value = 'id';
      document.getElementById('item-sort-dir').value = 'desc';
      loadItems(1);
    });

    // Refresh button
    document.getElementById('refresh-items-btn').addEventListener('click', () => loadItems(currentPage));

    // Table event delegation
    document.getElementById('items-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'delete-item') {
        deleteItem(btn.dataset.itemId, btn.dataset.itemName, btn);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
