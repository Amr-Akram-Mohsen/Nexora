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
    window.api.get('/admin/items/health_stats')
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
            
            const colors = ['var(--brand-blue)', 'var(--brand-purple)', 'var(--brand-orange)', 'var(--brand-teal)', 'var(--brand-green)'];
            
            data.item_type_distribution.forEach((item, index) => {
                const pct = total > 0 ? ((item.count / total) * 100).toFixed(1) : 0;
                const color = colors[index % colors.length];
                const typeName = item.type.charAt(0).toUpperCase() + item.type.slice(1);
                
                const row = document.createElement('div');
                row.className = 'flex items-center w-full gap-3';
                
                const iconDiv = document.createElement('div');
                iconDiv.className = 'overview-breakdown-icon';
                iconDiv.style.color = color;
                const iconI = document.createElement('i');
                iconI.className = 'fa-solid fa-cube';
                iconDiv.appendChild(iconI);
                
                const labelDiv = document.createElement('div');
                labelDiv.className = 'overview-breakdown-label truncate';
                labelDiv.title = typeName;
                labelDiv.textContent = typeName;
                
                const trackDiv = document.createElement('div');
                trackDiv.className = 'overview-breakdown-bar-track';
                const barDiv = document.createElement('div');
                barDiv.className = 'overview-breakdown-bar';
                barDiv.style.width = pct + '%';
                barDiv.style.backgroundColor = color;
                trackDiv.appendChild(barDiv);
                
                const valDiv = document.createElement('div');
                valDiv.className = 'overview-breakdown-val';
                valDiv.textContent = item.count.toLocaleString();
                
                const pctDiv = document.createElement('div');
                pctDiv.className = 'overview-breakdown-pct';
                pctDiv.textContent = pct + '%';
                
                row.appendChild(iconDiv);
                row.appendChild(labelDiv);
                row.appendChild(trackDiv);
                row.appendChild(valDiv);
                row.appendChild(pctDiv);
                
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
            distContainer.textContent = 'No type distribution data available.';
            distContainer.className = 'text-muted text-sm py-2';
        }
        
        // Render Top Engagement Items
        const engContainer = document.getElementById('stats-engagement-items');
        if (data.top_engagement_items && data.top_engagement_items.length > 0) {
            engContainer.innerHTML = '';
            
            data.top_engagement_items.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'overview-top-item flex items-center justify-between';
                
                const rankDiv = document.createElement('div');
                rankDiv.className = 'overview-top-rank';
                rankDiv.textContent = `#${index + 1}`;
                
                const nameDiv = document.createElement('div');
                nameDiv.className = 'overview-top-name truncate px-2';
                const link = document.createElement('a');
                link.href = `/admin/items?search=${item.id}`;
                link.className = 'overview-top-link-title';
                link.title = item.name;
                link.textContent = item.name;
                nameDiv.appendChild(link);
                
                const valDiv = document.createElement('div');
                valDiv.className = 'overview-top-value text-right';
                valDiv.style.minWidth = '60px';
                
                const ctrDiv = document.createElement('div');
                ctrDiv.className = 'text-[var(--brand-green)] font-bold';
                ctrDiv.textContent = `${item.ctr}% CTR`;
                
                const ratesDiv = document.createElement('div');
                ratesDiv.className = 'text-xs text-muted font-normal mt-1 flex gap-2 justify-end';
                
                const saveSpan = document.createElement('span');
                saveSpan.title = 'Save Rate';
                saveSpan.innerHTML = `<i class="fa-solid fa-bookmark text-[var(--brand-orange)]"></i> ${item.save_rate}%`;
                
                const likeSpan = document.createElement('span');
                likeSpan.title = 'Like Rate';
                likeSpan.innerHTML = `<i class="fa-solid fa-heart text-[var(--brand-red)]"></i> ${item.like_rate}%`;
                
                ratesDiv.appendChild(saveSpan);
                ratesDiv.appendChild(likeSpan);
                valDiv.appendChild(ctrDiv);
                valDiv.appendChild(ratesDiv);
                
                li.appendChild(rankDiv);
                li.appendChild(nameDiv);
                li.appendChild(valDiv);
                engContainer.appendChild(li);
            });
        } else {
            engContainer.textContent = 'No engagement data available.';
            engContainer.className = 'text-muted text-sm py-2 text-center';
        }
      })
      .catch(err => {
        console.error('Failed to load dashboard stats', err);
      });
  }

  // ── Fetch meta for dropdowns ────────────
  function loadMeta() {
    return window.api.get('/admin/items/meta')
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
          (data.item_types || []).forEach(t => {
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
        window.api.delete(`/admin/items/${id}`)
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
    function itemActionHandler(e) {
      const btn = e.target.closest("[data-action='delete-item']");
      if (!btn) return;
      const modal = document.getElementById("inspect-item-modal");
      deleteItem(parseInt(btn.dataset.id, 10), btn.dataset.name, btn, modal);
    }
    
    const tableContainer = document.getElementById("items-table");
    if (tableContainer) tableContainer.addEventListener("click", itemActionHandler);

    const inspectModal = document.getElementById("inspect-item-modal");
    if (inspectModal) inspectModal.addEventListener("click", itemActionHandler);
  }





  document.addEventListener('DOMContentLoaded', init);
})();
