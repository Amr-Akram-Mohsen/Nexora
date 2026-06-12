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
  let loadedItems = [];

  function getFilters() {
    return {
      search:    (document.getElementById('item-search') || {}).value || '',
      brand:     (document.getElementById('filter-item-brand') || {}).value || '',
      category:  (document.getElementById('filter-item-category') || {}).value || '',
      source:    (document.getElementById('filter-item-source') || {}).value || '',
      item_type: (document.getElementById('filter-item-type') || {}).value || '',
      sort_by:   (document.getElementById('item-sort-by') || {}).value || 'id',
      sort_dir:  (document.getElementById('item-sort-dir') || {}).value || 'desc',
    };
  }

  // ── Fetch meta for dropdowns ────────────
  function loadMeta() {
    return fetch('/admin/items/meta')
      .then(r => r.json())
      .then(data => {
        const brandSel = document.getElementById('filter-item-brand');
        const catSel   = document.getElementById('filter-item-category');
        const sourceSel = document.getElementById('filter-item-source');
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
        (data.sources || []).forEach(s => {
          const opt = document.createElement('option');
          opt.value = s.slug; opt.textContent = s.name;
          sourceSel.appendChild(opt);
        });
        (data.item_types || []).forEach(t => {
          const opt = document.createElement('option');
          opt.value = t; opt.textContent = t.charAt(0).toUpperCase() + t.slice(1);
          typeSel.appendChild(opt);
        });
      });
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
    tbody.innerHTML = getTableSpinnerHtml(9, "Loading…", "loading-height-md");

    fetch(`/admin/items/?${params}`)
      .then(r => { if (!r.ok) throw new Error('Network error'); return r.json(); })
      .then(data => renderItems(data))
      .catch(() => {
        tbody.innerHTML = getTableErrorStateHtml(9, "Failed to load products.");
      });
  }

  function renderItems(data) {
    const items   = data.items || [];
    loadedItems   = items;
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
      tbody.innerHTML = getTableEmptyStateHtml(9, "No products found.", "Try adjusting your filters.", "loading-height-md");
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
        <td>
          <span class="user-cell-name">${escapeHtml(item.source_name)}</span>
          <div class="user-cell-email">${escapeHtml(item.source_type)}</div>
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
            <button class="user-action-btn user-action-inspect inspect-btn"
              data-action="inspect-item"
              data-item-id="${item.id}"
              title="Inspect source variants and provider metadata">
              👁️ Inspect
            </button>
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
  // Exposes global escapeHtml and formatDate from core.js

  function applyUrlFilters() {
    if (typeof getUrlQueryParams !== "function") return;
    const params = getUrlQueryParams();
    
    const filterMap = {
      search: "item-search",
      brand: "filter-item-brand",
      category: "filter-item-category",
      source: "filter-item-source",
      item_type: "filter-item-type",
      sort_by: "item-sort-by",
      sort_dir: "item-sort-dir"
    };

    for (const [paramKey, elementId] of Object.entries(filterMap)) {
      if (params[paramKey] !== undefined) {
        const el = document.getElementById(elementId);
        if (el) {
          el.value = params[paramKey];
        }
      }
    }
  }

  // ── Event Wiring ─────────────────────────
  function init() {
    loadMeta()
      .then(() => {
        applyUrlFilters();
        loadItems(1);
      })
      .catch(() => {
        loadItems(1);
      });

    // Search debounce
    document.getElementById('item-search').addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => loadItems(1), 400);
    });

    // Filter selects
    ['filter-item-brand', 'filter-item-category', 'filter-item-source', 'filter-item-type',
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
      document.getElementById('filter-item-source').value = '';
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
      } else if (btn.dataset.action === 'inspect-item') {
        const itemId = parseInt(btn.dataset.itemId, 10);
        const item = loadedItems.find(i => i.id === itemId);
        if (item) {
          showInspectModal(itemId, item);
        }
      }
    });

    // Close inspect modal overlay
    const inspectCloseBtn = document.getElementById("inspect-item-close-btn");
    if (inspectCloseBtn) {
      inspectCloseBtn.addEventListener("click", () => {
        document.getElementById("inspect-item-modal").classList.remove("active");
      });
    }

    const inspectModalOverlay = document.getElementById("inspect-item-modal");
    if (inspectModalOverlay) {
      inspectModalOverlay.addEventListener("click", (e) => {
        if (e.target === inspectModalOverlay) {
          inspectModalOverlay.classList.remove("active");
        }
      });
    }
  }

  // ── Source/Provider Detail Inspection Modal ──────
  /**
   * Open the inspect modal, fetching full store-link details on demand
   * from /admin/items/<id>/detail (R-14 — store_links no longer embedded
   * in the listing response).
   */
  function showInspectModal(itemId, listItem) {
    const modal   = document.getElementById("inspect-item-modal");
    const body    = document.getElementById("inspect-item-body");
    const titleEl = document.getElementById("inspect-item-title");

    titleEl.textContent = `Inspect Product: ${listItem.name}`;
    body.innerHTML = getSpinnerHtml('Loading store links…');
    modal.classList.add("active");

    fetch(`/admin/items/${itemId}/detail`)
      .then(r => { if (!r.ok) throw new Error('Failed to load item detail'); return r.json(); })
      .then(detail => {
        body.innerHTML = buildInspectBodyHtml(detail);
      })
      .catch(() => {
        body.innerHTML = getErrorStateHtml('Could not load product details. Please try again.');
      });
  }

  function buildInspectBodyHtml(detail) {
    let linksHtml = "";
    const links = detail.store_links || [];

    if (links.length > 0) {
      links.forEach(lnk => {
        let metaRows = "";
        if (lnk.metadata && Object.keys(lnk.metadata).length > 0) {
          metaRows = `<div class="inspect-store-card-meta-box">`;
          for (const [k, v] of Object.entries(lnk.metadata)) {
            metaRows += `<div><strong>${k}:</strong> ${JSON.stringify(v)}</div>`;
          }
          metaRows += `</div>`;
        } else {
          metaRows = `<div class="inspect-store-card-meta-empty">No raw network tracking metadata.</div>`;
        }

        const priceVal = lnk.price != null ? `${Number(lnk.price).toFixed(2)} ${lnk.currency || ''}` : "—";
        const activeClass = lnk.is_active ? 'active' : 'inactive';

        linksHtml += `
          <div class="inspect-store-card">
            <div class="inspect-store-card-header">
              <div>
                <strong class="inspect-store-card-name">${escapeHtml(lnk.store_name)}</strong>
                <span class="status-badge inspect-store-card-badge-net">${escapeHtml(lnk.affiliate_network)}</span>
              </div>
              <div>
                <span class="status-badge ${lnk.availability === 'in_stock' ? 'active' : 'inactive'} badge-compact">
                  ${lnk.availability === 'in_stock' ? 'In Stock' : (lnk.availability || 'Out of Stock')}
                </span>
              </div>
            </div>
            <div class="inspect-store-card-grid">
              <div><strong>Program:</strong> ${escapeHtml(lnk.program_name)}</div>
              <div><strong>Price:</strong> ${priceVal}</div>
            </div>
            <div class="inspect-store-card-links">
              <div><strong>Original URL:</strong> <a href="${lnk.original_url}" target="_blank" class="inspect-link">${escapeHtml(lnk.original_url)} <i class="fas fa-external-link-alt"></i></a></div>
              <div><strong>Affiliate URL:</strong> <a href="${lnk.affiliate_url}" target="_blank" class="inspect-link text-brand-blue">${escapeHtml(lnk.affiliate_url)} <i class="fas fa-external-link-alt"></i></a></div>
            </div>
            <div class="mt-2">
              <span class="inspect-store-card-meta-label">Network Tracking Metadata:</span>
              ${metaRows}
            </div>
          </div>
        `;
      });
    } else {
      linksHtml = `<div class="text-center text-muted p-4">No store links or variant providers mapped for this product.</div>`;
    }

    return `
      <div class="inspect-details-group">
        <div>
          <strong class="inspect-details-title">Product Core Mappings</strong>
          <div class="inspect-details-row"><strong>ID:</strong> #${detail.id}</div>
          <div class="inspect-details-row"><strong>Type:</strong> <span class="status-badge inspect-badge-secondary">${escapeHtml(detail.item_type)}</span></div>
          <div class="inspect-details-row"><strong>Brand:</strong> ${escapeHtml(detail.brand)}</div>
          <div class="inspect-details-row"><strong>Category:</strong> ${escapeHtml(detail.category)}</div>
          <div class="inspect-details-row"><strong>System Source/Provider:</strong> <span class="inspect-brand-purple">${escapeHtml(detail.source_name)}</span> (slug: <code>${escapeHtml(detail.source_slug)}</code>)</div>
          <div class="inspect-details-row"><strong>Source Type:</strong> <code>${escapeHtml(detail.source_type)}</code></div>
        </div>
        <hr class="inspect-details-divider" />
        <div>
          <strong class="inspect-details-title">Ingested Stores &amp; Affiliate Links (${links.length})</strong>
          ${linksHtml}
        </div>
      </div>
    `;
  }

  document.addEventListener('DOMContentLoaded', init);
})();
