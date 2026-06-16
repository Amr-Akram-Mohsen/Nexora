// ==============================
// ADMIN — ITEMS CONTROL PANEL
// items.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  let itemsController;

  // ── Fetch meta for dropdowns ────────────
  function loadMeta() {
    return fetch('/admin/items/meta')
      .then(r => r.json())
      .then(data => {
        const brandSel = document.getElementById('filter-item-brand');
        const catSel = document.getElementById('filter-item-category');
        const sourceSel = document.getElementById('filter-item-source');
        const typeSel = document.getElementById('filter-item-type');

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

  // ── Delete ───────────────────────────────
  function deleteItem(id, name, btn, modal) {
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
              itemsController.load(itemsController.currentPage);
              if (modal) { modal.classList.remove("active"); }
            } else {
              showToast(d.error || 'Delete failed.', 'error');
              if (btn) { btn.disabled = false; btn.textContent = '🗑 Delete Product'; }
            }
          })
          .catch(() => {
            showToast('Delete failed. Please try again.', 'error');
            if (btn) { btn.disabled = false; btn.textContent = '🗑 Delete Product'; }
          });
      }
    );
  }

  function applyItemUrlFilters() {
    if (typeof applyUrlFilters !== "function") return;
    applyUrlFilters({
      search: "item-search",
      brand: "filter-item-brand",
      category: "filter-item-category",
      source: "filter-item-source",
      item_type: "filter-item-type",
      sort_by: "item-sort-by",
      sort_dir: "item-sort-dir"
    });
  }


  // ── Event Wiring ─────────────────────────
  function init() {
    // Instantiate items controller
    itemsController = new AdminListController({
      domain: 'items',
      endpoint: '/admin/items/',
      rowsEndpoint: '/admin/items/rows',  // ← HTML partial mode
      tbodyId: 'items-table-body',
      searchId: 'item-search',
      filterIds: [
        'filter-item-brand', 'filter-item-category', 'filter-item-source', 'filter-item-type',
        'item-sort-by', 'item-sort-dir'
      ],
      perPageId: 'items-per-page',
      prevBtnId: 'items-prev-btn',
      nextBtnId: 'items-next-btn',
      indicatorId: 'items-page-indicator',
      infoId: 'items-pagination-info',
      countId: 'items-count',
      clearBtnId: 'clear-item-filters-btn',
      refreshBtnId: 'refresh-items-btn',
      defaultPerPage: 20,
      colspan: 8,
      autoInit: false
    });

    loadMeta()
      .then(() => {
        applyItemUrlFilters();
        itemsController.init();
      })
      .catch(() => {
        itemsController.init();
      });

    // Parent tbody click event delegation
    document.getElementById('items-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'inspect-item') {
        const itemId = parseInt(btn.dataset.id || btn.dataset.itemId, 10);
        showInspectModal(itemId);
      }
    });

    // Inspect modal: delete action delegation
    const inspectModal = document.getElementById("inspect-item-modal");
    if (inspectModal) {
      inspectModal.addEventListener('click', e => {
        const btn = e.target.closest("[data-action='delete-item']");
        if (!btn) return;
        deleteItem(parseInt(btn.dataset.id, 10), btn.dataset.name, btn, inspectModal);
      });
    }
  }

  // ── Inspect Modal (server-rendered) ──────────────────
  function showInspectModal(itemId) {
    const modal   = document.getElementById("inspect-item-modal");
    const body    = document.getElementById("inspect-item-modal-body");
    const titleEl = document.getElementById("inspect-item-modal-title");
    if (!modal || !body) return;

    body.innerHTML = getSpinnerHtml('Loading store links…');
    titleEl.textContent = 'Product Details';
    modal.classList.add("active");

    fetch(`/admin/items/${itemId}/inspect`)
      .then(r => r.text())
      .then(html => {
        body.innerHTML = html;
      })
      .catch(() => {
        body.innerHTML = getErrorStateHtml('Could not load product details. Please try again.');
      });
  }



  document.addEventListener('DOMContentLoaded', init);
})();
