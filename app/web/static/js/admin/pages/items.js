// ==============================
// ADMIN — ITEMS CONTROL PANEL
// items.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  window.itemsController = null;

  // ── Fetch Dashboard Stats ────────────────
  function loadDashboardStats() {
    fetch('/admin/items/health_stats')
      .then(r => r.json())
      .then(data => {
        const total = data.total_items || 0;
        
        document.getElementById('stats-total-items').textContent = total.toLocaleString();
        
        const imgPct = total > 0 ? Math.round((data.items_with_images / total) * 100) : 0;
        document.getElementById('stats-image-coverage').textContent = imgPct + '%';
        document.getElementById('stats-meta-images').textContent = `${(total - data.items_with_images).toLocaleString()} missing`;
        
        const brandPct = total > 0 ? Math.round((data.branded_items / total) * 100) : 0;
        document.getElementById('stats-brand-coverage').textContent = brandPct + '%';
        document.getElementById('stats-meta-brands').textContent = `${(total - data.branded_items).toLocaleString()} unbranded`;
        
        const linkPct = total > 0 ? Math.round((data.items_with_links / total) * 100) : 0;
        document.getElementById('stats-link-coverage').textContent = linkPct + '%';
        document.getElementById('stats-meta-links').textContent = `${(total - data.items_with_links).toLocaleString()} missing links`;
        
        document.getElementById('stats-stale-syncs').textContent = (data.stale_sync_items || 0).toLocaleString();
        
        // Render Item Type Distribution
        const distContainer = document.getElementById('stats-type-distribution');
        if (data.item_type_distribution && data.item_type_distribution.length > 0) {
            distContainer.innerHTML = '';
            
            // Define colors for visual variety
            const colors = ['var(--brand-blue)', 'var(--brand-purple)', 'var(--brand-orange)', 'var(--brand-teal)', 'var(--brand-green)'];
            
            data.item_type_distribution.forEach((item, index) => {
                const pct = total > 0 ? ((item.count / total) * 100).toFixed(1) : 0;
                const color = colors[index % colors.length];
                const typeName = item.type.charAt(0).toUpperCase() + item.type.slice(1);
                
                const row = document.createElement('div');
                row.className = 'flex items-center w-full gap-3';
                row.innerHTML = `
                    <div class="overview-breakdown-icon" style="color: ${color};"><i class="fa-solid fa-cube"></i></div>
                    <div class="overview-breakdown-label truncate" title="${typeName}">${typeName}</div>
                    <div class="overview-breakdown-bar-track">
                        <div class="overview-breakdown-bar" style="width: ${pct}%; background-color: ${color};"></div>
                    </div>
                    <div class="overview-breakdown-val">${item.count.toLocaleString()}</div>
                    <div class="overview-breakdown-pct">${pct}%</div>
                `;
                
                // Make row clickable if it's a specific type
                if (item.type !== 'Uncategorized') {
                    row.style.cursor = 'pointer';
                    row.classList.add('dist-row-link');
                    row.addEventListener('click', () => {
                        const typeSelect = document.getElementById('filter-item-type');
                        if (typeSelect) {
                            typeSelect.value = item.type;
                            typeSelect.dispatchEvent(new Event('change'));
                        }
                    });
                }
                
                distContainer.appendChild(row);
            });
        } else {
            distContainer.innerHTML = '<div class="text-muted text-sm py-2">No type distribution data available.</div>';
        }
        
        // Render Top Engagement Items
        const engContainer = document.getElementById('stats-engagement-items');
        if (data.top_engagement_items && data.top_engagement_items.length > 0) {
            engContainer.innerHTML = '';
            
            data.top_engagement_items.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'overview-top-item flex items-center justify-between';
                li.innerHTML = `
                    <div class="overview-top-rank">#${index + 1}</div>
                    <div class="overview-top-name truncate px-2">
                        <a href="/admin/items?search=${item.id}" class="overview-top-link-title" title="${item.name}">${item.name}</a>
                    </div>
                    <div class="overview-top-value text-right" style="min-width: 60px;">
                        <div class="text-[var(--brand-green)] font-bold">${item.ctr}% CTR</div>
                        <div class="text-xs text-muted font-normal mt-1 flex gap-2 justify-end">
                            <span title="Save Rate"><i class="fa-solid fa-bookmark text-[var(--brand-orange)]"></i> ${item.save_rate}%</span>
                            <span title="Like Rate"><i class="fa-solid fa-heart text-[var(--brand-red)]"></i> ${item.like_rate}%</span>
                        </div>
                    </div>
                `;
                engContainer.appendChild(li);
            });
        } else {
            engContainer.innerHTML = '<li class="text-muted text-sm py-2 text-center">No engagement data available.</li>';
        }
      })
      .catch(err => {
        console.error('Failed to load dashboard stats', err);
      });
  }

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
              window.itemsController.load(window.itemsController.currentPage);
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
      has_images: "filter-item-has-images",
      has_brand: "filter-item-has-brand",
      availability: "filter-item-availability",
      sort_by: "item-sort-by",
      sort_dir: "item-sort-dir"
    });
  }


  // ── Event Wiring ─────────────────────────
  function init() {
    // Instantiate items controller
    window.itemsController = new AdminListController({
      domain: 'items',
      endpoint: '/admin/items/',
      rowsEndpoint: '/admin/items/rows',
      filterIds: [
        'filter-item-brand', 'filter-item-category', 'filter-item-source', 'filter-item-type',
        'filter-item-has-images', 'filter-item-has-brand', 'filter-item-availability',
        'item-sort-by', 'item-sort-dir'
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
    document.body.addEventListener('click', e => {
      const btn = e.target.closest("[data-action='delete-item']");
      if (!btn) return;
      const modal = document.getElementById("inspect-item-modal");
      deleteItem(parseInt(btn.dataset.id, 10), btn.dataset.name, btn, modal);
    });
  }





  document.addEventListener('DOMContentLoaded', init);
})();
