// ADMIN — PRODUCTS CONTROL PANEL
// products.js

(function () {
  'use strict';

  window.itemsController = null;

  function loadDashboardStats() {
    window.api.get('/admin/products/health_stats')
      .then(data => {
        const total = data.total_items || 0;

        if (window.itemsController) {
          window.itemsController.updateStatsUI(data, {
            total_items: 'stats-total-products',
            stale_sync_items: 'stats-stale-syncs'
          });
        }

        const imgPct = total > 0 ? Math.round((data.items_with_images / total) * 100) : 0;
        document.getElementById('stats-image-coverage').textContent = imgPct + '%';
        document.getElementById('stats-meta-images').textContent = `${(total - data.items_with_images).toLocaleString()} missing`;

        const brandPct = total > 0 ? Math.round((data.branded_items / total) * 100) : 0;
        document.getElementById('stats-brand-coverage').textContent = brandPct + '%';
        document.getElementById('stats-meta-brands').textContent = `${(total - data.branded_items).toLocaleString()} unbranded`;

        const linkPct = total > 0 ? Math.round((data.items_with_links / total) * 100) : 0;
        document.getElementById('stats-link-coverage').textContent = linkPct + '%';
        document.getElementById('stats-meta-links').textContent = `${(total - data.items_with_links).toLocaleString()} missing links`;

      })
      .catch(err => {
        console.error('Failed to load dashboard stats', err);
      });
  }

  function loadMeta() {
    return window.api.get('/admin/products/meta')
      .then(data => {
        const brandSel = document.getElementById('filter-item-brand');
        const catSel = document.getElementById('filter-item-category');
        const sourceSel = document.getElementById('filter-item-source');
        const typeSel = document.getElementById('filter-item-type');

        if(brandSel) {
          (data.brands || []).forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.slug; opt.textContent = b.name;
            brandSel.appendChild(opt);
          });
        }
        if(catSel) {
          (data.categories || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.slug; opt.textContent = c.name;
            catSel.appendChild(opt);
          });
        }
        if(sourceSel) {
          (data.sources || []).forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.slug; opt.textContent = s.name;
            sourceSel.appendChild(opt);
          });
        }
        if(typeSel) {
          (data.product_types || []).forEach(t => {
            const opt = document.createElement('option');
            opt.value = t; opt.textContent = t.charAt(0).toUpperCase() + t.slice(1);
            typeSel.appendChild(opt);
          });
        }
      });
  }

  function deleteItem(id, name, btn, modal) {
    showModal(
      'Delete Product',
      `Are you sure you want to permanently delete "${name}"? This will remove all variants and store links.`,
      () => {
        if (btn) { btn.disabled = true; btn.textContent = 'Deleting…'; }
        window.api.delete(`/admin/products/${id}`)
          .then(d => {
            if (d.success) {
              showToast(d.message || 'Product deleted.', 'success');
              window.itemsController.load(window.itemsController.currentPage);
              if (modal) { modal.classList.remove("active"); }
            } else {
              showToast(d.error || 'Delete failed.', 'error');
              if (btn) { btn.disabled = false; btn.textContent = '🗑 Delete Product'; }
            }
          })
          .catch(() => {
            if (btn) { btn.disabled = false; btn.textContent = '🗑 Delete Product'; }
          });
      }
    );
  }

  function applyItemUrlFilters() {
    if (typeof applyUrlFilters !== "function") return;
    applyUrlFilters({
      search: "product-search",
      brand: "filter-item-brand",
      category: "filter-item-category",
      source: "filter-item-source",
      product_type: "filter-item-type",
      has_images: "filter-item-has-images",
      has_brand: "filter-item-has-brand",
      availability: "filter-item-availability",
      sort_by: "product-sort-by",
      sort_dir: "product-sort-dir"
    });
  }

  function init() {
    // Instantiate products controller
    window.itemsController = new AdminListController({
      domain: 'products',
      endpoint: '/admin/products/',
      rowsEndpoint: '/admin/products/rows',
      filterIds: [
        'filter-item-brand', 'filter-item-category', 'filter-item-source', 'filter-item-type',
        'filter-item-has-images', 'filter-item-has-brand', 'filter-item-availability',
        'product-sort-by', 'product-sort-dir'
      ],
      colspan: 10,
      autoInit: false
    });

    loadMeta()
      .then(() => {
        applyItemUrlFilters();
        window.itemsController.init();
      })
      .catch(() => {
        window.itemsController.init();
      });

    loadDashboardStats();

    // Bind dashboard cards to filters
    document.querySelectorAll('.filter-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const filterId = link.getAttribute('data-filter');
        const filterVal = link.getAttribute('data-val');

        if (filterId) {
            const select = document.getElementById(filterId);
            if (select) {
                select.value = filterVal;
                // Trigger change event to fire AdminListController refresh
                select.dispatchEvent(new Event('change'));
            }
        }
      });
    });

    // Inspect modal or detail page: delete action delegation
    function itemActionHandler(e) {
      const btn = e.target.closest("[data-action='delete-product']");
      if (!btn) return;
      const modal = document.getElementById("inspect-product-modal");
      deleteItem(parseInt(btn.dataset.id, 10), btn.dataset.name, btn, modal);
    }

    const tableContainer = document.getElementById("products-table");
    if (tableContainer) tableContainer.addEventListener("click", itemActionHandler);

    const inspectModal = document.getElementById("inspect-product-modal");
    if (inspectModal) inspectModal.addEventListener("click", itemActionHandler);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
