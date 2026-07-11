// ==============================
// ADMIN — PRODUCTS CONTROL PANEL
// products.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  window.itemsController = null;

  // ── Fetch Dashboard Stats ────────────────
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

  // ── Fetch meta for dropdowns ────────────
  function loadMeta() {
    return window.api.get('/admin/products/meta')
      .then(data => {
        const brandSel = document.getElementById('filter-product-brand');
        const catSel = document.getElementById('filter-product-category');
        const sourceSel = document.getElementById('filter-product-source');
        const typeSel = document.getElementById('filter-product-type');

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

  // ── Delete ───────────────────────────────
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
      brand: "filter-product-brand",
      category: "filter-product-category",
      source: "filter-product-source",
      product_type: "filter-product-type",
      has_images: "filter-product-has-images",
      has_brand: "filter-product-has-brand",
      availability: "filter-product-availability",
      sort_by: "product-sort-by",
      sort_dir: "product-sort-dir"
    });
  }


  // ── Event Wiring ─────────────────────────
  function init() {
    // Instantiate products controller
    window.itemsController = new AdminListController({
      domain: 'products',
      endpoint: '/admin/products/',
      rowsEndpoint: '/admin/products/rows',
      filterIds: [
        'filter-product-brand', 'filter-product-category', 'filter-product-source', 'filter-product-type',
        'filter-product-has-images', 'filter-product-has-brand', 'filter-product-availability',
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
