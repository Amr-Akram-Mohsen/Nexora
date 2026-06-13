// ==============================
// ADMIN — ITEMS CONTROL PANEL
// items.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  let itemsController;
  let loadedItems = [];

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

  function renderItemRow(item) {
    const template = document.getElementById('item-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.item-cell-name').textContent = item.name;
    clone.querySelector('.item-cell-brand').textContent = item.brand;
    clone.querySelector('.item-cell-category').textContent = item.category;
    clone.querySelector('.item-cell-price').textContent = item.min_price != null
      ? `${Number(item.min_price).toFixed(2)} ${item.currency || ''}`
      : '—';
    clone.querySelector('.item-cell-storecount').textContent = item.store_count;
    clone.querySelector('.item-cell-clicks').textContent = (item.click_count || 0).toLocaleString();
    clone.querySelector('.item-cell-date').textContent = formatDate(item.created_at);

    // Buttons dataset
    const inspectBtn = clone.querySelector('.inspect-btn');
    inspectBtn.dataset.itemId = item.id;

    return tr;
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
    // Instantiate items controller
    itemsController = new AdminListController({
      domain: 'items',
      endpoint: '/admin/items/',
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
      rowTemplateId: 'item-row-template',
      defaultPerPage: 20,
      colspan: 8,
      itemsKey: 'items',
      renderRow: renderItemRow,
      onLoaded: (data) => {
        loadedItems = data.items || [];
      },
      autoInit: false
    });

    loadMeta()
      .then(() => {
        applyUrlFilters();
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
  function showInspectModal(itemId, listItem) {
    const modal = document.getElementById("inspect-item-modal");
    const body = document.getElementById("inspect-item-modal-body");
    const titleEl = document.getElementById("inspect-item-modal-title");

    titleEl.textContent = `Inspect Product: ${listItem.name}`;
    body.innerHTML = getSpinnerHtml('Loading store links…');
    modal.classList.add("active");

    fetch(`/admin/items/${itemId}/detail`)
      .then(r => { if (!r.ok) throw new Error('Failed to load item detail'); return r.json(); })
      .then(detail => {
        body.innerHTML = "";
        body.appendChild(buildInspectBody(detail, modal));
      })
      .catch(() => {
        body.innerHTML = getErrorStateHtml('Could not load product details. Please try again.');
      });
  }

  function buildInspectBody(detail, modal) {
    const template = document.getElementById('item-inspect-template');
    const clone = template.content.cloneNode(true);
    const container = clone.querySelector('.inspect-details-group');

    clone.querySelector('.inspect-id').textContent = `#${detail.id}`;
    clone.querySelector('.inspect-type').textContent = detail.item_type;
    clone.querySelector('.inspect-brand').textContent = detail.brand;
    clone.querySelector('.inspect-category').textContent = detail.category;
    clone.querySelector('.inspect-source').textContent = detail.source_name;
    clone.querySelector('.inspect-source-slug').textContent = detail.source_slug;
    clone.querySelector('.inspect-source-type').textContent = detail.source_type;

    const links = detail.store_links || [];
    clone.querySelector('.inspect-links-count').textContent = links.length;

    const linksContainer = clone.querySelector('.inspect-links-container');
    const cardTemplate = document.getElementById('item-store-link-template');

    if (links.length > 0) {
      links.forEach(lnk => {
        const cardClone = cardTemplate.content.cloneNode(true);
        const card = cardClone.querySelector('.inspect-store-card');

        cardClone.querySelector('.inspect-store-card-name').textContent = lnk.store_name;

        const netBadge = cardClone.querySelector('.inspect-store-card-badge-net');
        netBadge.textContent = lnk.affiliate_network;

        const availBadge = cardClone.querySelector('.inspect-store-availability');
        availBadge.textContent = lnk.availability === 'in_stock' ? 'In Stock' : (lnk.availability || 'Out of Stock');
        availBadge.classList.add(lnk.availability === 'in_stock' ? 'active' : 'inactive');

        cardClone.querySelector('.inspect-store-program').textContent = lnk.program_name;
        cardClone.querySelector('.inspect-store-price').textContent = lnk.price != null
          ? `${Number(lnk.price).toFixed(2)} ${lnk.currency || ''}`
          : "—";

        const origLink = cardClone.querySelector('.inspect-store-orig-link');
        origLink.href = lnk.original_url;
        origLink.textContent = lnk.original_url;

        const affLink = cardClone.querySelector('.inspect-store-aff-link');
        affLink.href = lnk.affiliate_url;
        affLink.textContent = lnk.affiliate_url;

        const metaBox = cardClone.querySelector('.inspect-store-metadata-box');
        if (lnk.metadata && Object.keys(lnk.metadata).length > 0) {
          metaBox.className = "inspect-store-card-meta-box";
          let metaHtml = "";
          for (const [k, v] of Object.entries(lnk.metadata)) {
            metaHtml += `<div><strong>${k}:</strong> ${JSON.stringify(v)}</div>`;
          }
          metaBox.innerHTML = metaHtml;
        } else {
          metaBox.className = "inspect-store-card-meta-empty";
          metaBox.textContent = "No raw network tracking metadata.";
        }

        linksContainer.appendChild(card);
      });
    } else {
      linksContainer.innerHTML = `<div class="text-center text-muted p-4">No store links or variant providers mapped for this product.</div>`;
    }

    const deleteBtn = clone.querySelector('.inspect-delete-btn');
    if (deleteBtn) {
      deleteBtn.dataset.id = detail.id;
      deleteBtn.dataset.name = detail.name;
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteItem(detail.id, detail.name, deleteBtn, modal);
      });
    }

    return container;
  }

  document.addEventListener('DOMContentLoaded', init);
})();
