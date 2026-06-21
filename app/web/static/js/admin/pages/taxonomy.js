// ==============================
// ADMIN — TAXONOMY MANAGEMENT
// taxonomy.js
// ==============================

(function () {
  'use strict';

  const loadedTabs = new Set();

  function loadTaxonomyAnalytics() {
    fetch('/admin/taxonomy/analytics')
      .then(r => r.json())
      .then(d => {
        const container = document.getElementById('taxonomy-analytics-dashboard');
        if (!container) return;

        let missingBrandPct = d.total_content ? Math.round((d.missing_brand / d.total_content) * 100) : 0;
        let missingCategoryPct = d.total_content ? Math.round((d.missing_category / d.total_content) * 100) : 0;

        container.style.display = 'grid';
        container.innerHTML = `
          <div class="dashboard-widget-card" style="padding:1.5rem; background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px;">
            <div style="font-size:0.875rem; color:var(--text-muted); margin-bottom:0.5rem;">Total Entities</div>
            <div style="font-size:1.75rem; font-weight:bold;">${d.total_entities.toLocaleString()}</div>
          </div>
          <div class="dashboard-widget-card" style="padding:1.5rem; background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px;">
            <div style="font-size:0.875rem; color:var(--text-muted); margin-bottom:0.5rem;">Orphaned Entities</div>
            <div style="font-size:1.75rem; font-weight:bold; color:var(--error);">${d.orphans.toLocaleString()}</div>
          </div>
          <div class="dashboard-widget-card" style="padding:1.5rem; background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px;">
            <div style="font-size:0.875rem; color:var(--text-muted); margin-bottom:0.5rem;">Content w/o Brand</div>
            <div style="font-size:1.75rem; font-weight:bold; color:${missingBrandPct > 10 ? 'var(--warning)' : 'inherit'};">${missingBrandPct}%</div>
          </div>
          <div class="dashboard-widget-card" style="padding:1.5rem; background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px;">
            <div style="font-size:0.875rem; color:var(--text-muted); margin-bottom:0.5rem;">Content w/o Category</div>
            <div style="font-size:1.75rem; font-weight:bold; color:${missingCategoryPct > 10 ? 'var(--warning)' : 'inherit'};">${missingCategoryPct}%</div>
          </div>
        `;
      })
      .catch(e => console.error("Failed to load taxonomy analytics:", e));
  }

  function loadInsights() {
    // Load Suggestions
    fetch('/admin/taxonomy/insights/suggestions')
      .then(r => r.json())
      .then(data => {
        const c = document.getElementById('insights-suggestions-container');
        if (!c) return;
        if (!data || data.length === 0) {
          c.innerHTML = `<div style="text-align:center; padding: 2rem; color: var(--text-muted);">No suggestions found. You're fully tagged!</div>`;
          return;
        }
        let html = `<table class="admin-table"><thead><tr><th>Content</th><th>Suggested Tag</th><th>Action</th></tr></thead><tbody>`;
        data.forEach(item => {
          html += `<tr>
            <td>${item.content_title}</td>
            <td><span class="badge badge-info">${item.type}: ${item.suggested_name}</span></td>
            <td><button class="btn btn-sm btn-primary" onclick="applyInsightSuggestion(${item.content_id}, '${item.type}', ${item.suggested_id})">Apply</button></td>
          </tr>`;
        });
        html += `</tbody></table>`;
        c.innerHTML = html;
      });

    // Load Coherence
    fetch('/admin/taxonomy/insights/coherence')
      .then(r => r.json())
      .then(data => {
        const c = document.getElementById('insights-coherence-container');
        if (!c) return;
        if (!data || data.length === 0) {
          c.innerHTML = `<div style="text-align:center; padding: 2rem; color: var(--text-muted);">No cross-domain conflicts detected!</div>`;
          return;
        }
        let html = `<table class="admin-table"><thead><tr><th>Content</th><th>Content Brands</th><th>Item</th><th>Item Brand</th><th>Action</th></tr></thead><tbody>`;
        data.forEach(item => {
          html += `<tr>
            <td>${item.content_title}</td>
            <td><span class="badge badge-warning">${item.content_brands.join(', ') || 'None'}</span></td>
            <td>${item.item_name}</td>
            <td><span class="badge badge-error">${item.item_brand}</span></td>
            <td><button class="btn btn-sm btn-outline-primary" onclick="applyInsightSuggestion(${item.content_id}, 'Brand', ${item.suggested_brand_id})">Fix Content Brand</button></td>
          </tr>`;
        });
        html += `</tbody></table>`;
        c.innerHTML = html;
      });
  }

  window.applyInsightSuggestion = function (contentId, type, suggestedId) {
    if (!confirm(`Apply ${type} suggestion?`)) return;
    fetch('/admin/taxonomy/insights/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: contentId, type: type, suggested_id: suggestedId })
    })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          alert("Applied successfully!");
          loadInsights(); // reload tables
        } else {
          alert("Error applying suggestion: " + d.error);
        }
      });
  };

  window.categoriesController = null;
  window.brandsController = null;
  window.topicsController = null;
  window.sectionsController = null;

  // ── Slug helper (mirrors Python's generate_slug) ─────────────
  function slugify(str) {
    return (str || '')
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_-]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  // ── Tab Switching ─────────────────────────────────────────────
  function initTabs() {
    document.getElementById('taxonomy-tabs').addEventListener('click', e => {
      const btn = e.target.closest('.admin-tab-btn');
      if (!btn) return;
      const tab = btn.dataset.tab;
      document.querySelectorAll('#taxonomy-tabs .admin-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.admin-tab-panel').forEach(p => p.classList.add('is-hidden'));
      btn.classList.add('active');
      document.getElementById(`tab-panel-${tab}`).classList.remove('is-hidden');
      loadTab(tab);
    });
  }

  function loadTab(tab) {
    const targetId = tab;
    if (!loadedTabs.has(targetId)) {
      if (targetId === 'categories') window.categoriesController.init();
      if (targetId === 'brands') window.brandsController.init();
      if (targetId === 'topics') window.topicsController.init();
      if (targetId === 'sections') window.sectionsController.init();
      if (targetId === 'attributes') window.attributesController.init();
      if (targetId === 'gender_facets') window.genderFacetsController.init();
      if (targetId === 'intent_facets') window.intentFacetsController.init();
      if (targetId === 'price_tier_facets') window.priceTierFacetsController.init();
      loadedTabs.add(targetId);
    } else {
      if (tab === 'categories') window.categoriesController.load(1);
      if (tab === 'brands') window.brandsController.load(1);
      if (tab === 'topics') window.topicsController.load(1);
      if (tab === 'sections') window.sectionsController.load(1);
      if (tab === 'attributes') window.attributesController.load(1);
      if (tab === 'gender_facets') window.genderFacetsController.load(1);
      if (tab === 'intent_facets') window.intentFacetsController.load(1);
      if (tab === 'price_tier_facets') window.priceTierFacetsController.load(1);
    }
  }

  // ── CATEGORIES ─────────────────────────────
  function createCategory() {
    const nameInput = document.getElementById('new-category-name');
    const name = nameInput.value.trim();
    if (!name) { showToast('Category name is required.', 'error'); return; }

    fetch('/admin/taxonomy/categories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); return; }
        showToast(`Category "${name}" created.`, 'success');
        nameInput.value = '';
        document.getElementById('new-category-slug-preview').textContent = '—';
        window.categoriesController.load(1);
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteCategory(id, name, btn) {
    showModal('Delete Category', `Delete "${name}"? This may affect contents and products assigned to it.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/categories/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); window.categoriesController.load(1); }
          else { showToast(d.error, 'error'); if (btn) btn.disabled = false; }
        })
        .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
    });
  }

  function toggleCategoryActive(id, isActive, el) {
    fetch(`/admin/taxonomy/categories/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); el.checked = !isActive; return; }
        showToast(`Category ${isActive ? 'activated' : 'deactivated'}.`, 'success');
        window.categoriesController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── BRANDS ───────────────────────────────
  function createBrand() {
    const name = document.getElementById('new-brand-name').value.trim();
    const industry = document.getElementById('new-brand-industry').value.trim();
    if (!name) { showToast('Brand name is required.', 'error'); return; }

    fetch('/admin/taxonomy/brands', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, industry: industry || null }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); return; }
        showToast(`Brand "${name}" created.`, 'success');
        document.getElementById('new-brand-name').value = '';
        document.getElementById('new-brand-industry').value = '';
        document.getElementById('new-brand-slug-preview').textContent = '—';
        window.brandsController.load(1);
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteBrand(id, name, btn) {
    showModal('Delete Brand', `Delete "${name}"? Items and content tagged with this brand will lose the association.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/brands/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); window.brandsController.load(1); }
          else { showToast(d.error, 'error'); if (btn) btn.disabled = false; }
        })
        .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
    });
  }

  function toggleBrandActive(id, isActive, el) {
    fetch(`/admin/taxonomy/brands/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); el.checked = !isActive; return; }
        showToast(`Brand ${isActive ? 'activated' : 'deactivated'}.`, 'success');
        window.brandsController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── TOPICS ───────────────────────────────
  function createTopic() {
    const name = document.getElementById('new-topic-name').value.trim();
    if (!name) { showToast('Topic name is required.', 'error'); return; }

    fetch('/admin/taxonomy/topics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); return; }
        showToast(`Topic "${name}" created.`, 'success');
        document.getElementById('new-topic-name').value = '';
        document.getElementById('new-topic-slug-preview').textContent = '—';
        window.topicsController.load(1);
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteTopic(id, name, btn) {
    showModal('Delete Topic', `Delete "${name}"? Content tagged with this topic will lose the association.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/topics/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); window.topicsController.load(1); }
          else { showToast(d.error, 'error'); if (btn) btn.disabled = false; }
        })
        .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
    });
  }

  function toggleTopicActive(id, isActive, el) {
    fetch(`/admin/taxonomy/topics/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); el.checked = !isActive; return; }
        showToast(`Topic ${isActive ? 'activated' : 'deactivated'}.`, 'success');
        window.topicsController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── SECTIONS ─────────────────────────────
  function toggleSectionActive(id, isActive, el) {
    fetch(`/admin/taxonomy/sections/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); el.checked = !isActive; return; }
        showToast(`Section ${isActive ? 'activated' : 'deactivated'}.`, 'success');
        window.sectionsController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── ATTRIBUTES ───────────────────────────
  function createAttribute() {
    const name = document.getElementById('new-attribute-name').value.trim();
    if (!name) { showToast('Attribute name is required.', 'error'); return; }

    fetch('/admin/taxonomy/attributes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); return; }
        showToast(`Attribute "${name}" created.`, 'success');
        document.getElementById('new-attribute-name').value = '';
        document.getElementById('new-attribute-slug-preview').textContent = '—';
        window.attributesController.load(1);
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteAttribute(id, name, btn) {
    showModal('Delete Attribute', `Delete "${name}"? Content tagged with this attribute will lose the association.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/attributes/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); window.attributesController.load(1); }
          else { showToast(d.error, 'error'); if (btn) btn.disabled = false; }
        })
        .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
    });
  }

  // ── Global table event delegation ────────
  function initTableDelegation() {
    document.addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;

      const { action, id, name } = btn.dataset;

      // Delete actions
      if (action === 'delete-category') deleteCategory(id, name, btn);
      if (action === 'delete-brand') deleteBrand(id, name, btn);
      if (action === 'delete-topic') deleteTopic(id, name, btn);
      if (action === 'delete-attribute') deleteAttribute(id, name, btn);

      // Inspect actions
      if (action === 'inspect-category') inspectTaxonomy('categories', 'category', id);
      if (action === 'inspect-brand') inspectTaxonomy('brands', 'brand', id);
      if (action === 'inspect-topic') inspectTaxonomy('topics', 'topic', id);
      if (action === 'inspect-section') inspectTaxonomy('sections', 'section', id);
      if (action === 'inspect-attribute') inspectTaxonomy('attributes', 'attribute', id);
      if (action === 'inspect-gender_facet') inspectTaxonomy('gender_facets', 'gender_facet', id);
      if (action === 'inspect-intent_facet') inspectTaxonomy('intent_facets', 'intent_facet', id);
      if (action === 'inspect-price_tier_facet') inspectTaxonomy('price_tier_facets', 'price_tier_facet', id);
    });

    // Toggle checkboxes (use change event)
    document.addEventListener('change', e => {
      const el = e.target;
      if (!el.matches('[data-action]')) return;
      const { action, id } = el.dataset;
      const isActive = el.checked;
      if (action === 'toggle-category') toggleCategoryActive(id, isActive, el);
      if (action === 'toggle-brand') toggleBrandActive(id, isActive, el);
      if (action === 'toggle-topic') toggleTopicActive(id, isActive, el);
      if (action === 'toggle-section') toggleSectionActive(id, isActive, el);
    });

    // Find Duplicates
    document.addEventListener('click', e => {
      const btn = e.target.closest('[data-action="find-duplicates"]');
      if (!btn) return;
      const domain = btn.dataset.domain;
      openDuplicatesModal(domain);
    });

    document.addEventListener('click', e => {
      const btn = e.target.closest('[data-action="merge-duplicate"]');
      if (!btn) return;
      const { domain, sourceId, targetId } = btn.dataset;
      mergeDuplicate(domain, sourceId, targetId, btn);
    });
  }

  // ── DUPLICATES LOGIC ───────────────────────
  function openDuplicatesModal(domain) {
    const modal = document.getElementById('admin-duplicates-modal');
    const body = document.getElementById('admin-duplicates-body');
    if (modal) modal.classList.add('active');
    if (body) body.innerHTML = '<div style="padding: 2rem; text-align: center;">Scanning for duplicates...</div>';

    fetch(`/admin/taxonomy/duplicates?type=${domain}`)
      .then(r => r.json())
      .then(d => {
        if (d.error) {
          if (body) body.innerHTML = `<div style="padding: 2rem; color: var(--error);">${d.error}</div>`;
          return;
        }
        if (!d.length) {
          if (body) body.innerHTML = `<div style="padding: 2rem; text-align: center;">No duplicates found!</div>`;
          return;
        }
        let html = `<table class="admin-table"><thead><tr><th>Source (Will be merged & deleted)</th><th>Target (Will be kept)</th><th>Similarity</th><th>Actions</th></tr></thead><tbody>`;
        d.forEach(pair => {
          html += `<tr>
            <td><strong>${pair.source.name}</strong> (ID: ${pair.source.id})</td>
            <td><strong>${pair.target.name}</strong> (ID: ${pair.target.id})</td>
            <td>${pair.similarity}%</td>
            <td>
              <div class="flex gap-2">
                <button class="admin-btn-secondary admin-btn-sm" data-action="merge-duplicate" data-domain="${domain}" data-source-id="${pair.source.id}" data-target-id="${pair.target.id}">Merge S &rarr; T</button>
                <button class="admin-btn-secondary admin-btn-sm" data-action="merge-duplicate" data-domain="${domain}" data-source-id="${pair.target.id}" data-target-id="${pair.source.id}">Merge T &rarr; S</button>
              </div>
            </td>
          </tr>`;
        });
        html += `</tbody></table>`;
        if (body) body.innerHTML = html;
      })
      .catch(() => {
        if (body) body.innerHTML = `<div style="padding: 2rem; color: var(--error);">Failed to load duplicates.</div>`;
      });
  }

  function mergeDuplicate(domain, sourceId, targetId, btn) {
    if (!confirm(`Are you sure you want to merge ID ${sourceId} into ID ${targetId}? The source entity will be deleted and its contents will be moved to the target.`)) return;

    if (btn) btn.disabled = true;
    fetch('/admin/taxonomy/merge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domain, source_id: sourceId, target_id: targetId }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) {
          showToast(d.error, 'error');
          if (btn) btn.disabled = false;
        } else {
          showToast(`Successfully merged!`, 'success');
          openDuplicatesModal(domain); // reload duplicates
          // Reload the relevant table
          if (window[`${domain}Controller`]) {
            window[`${domain}Controller`].load(window[`${domain}Controller`].currentPage);
          }
        }
      })
      .catch(() => {
        showToast('Merge failed.', 'error');
        if (btn) btn.disabled = false;
      });
  }

  function inspectTaxonomy(domainPlural, domainSingular, id) {
    if (typeof window.openInspectModal === "function") {
      const title = domainSingular.charAt(0).toUpperCase() + domainSingular.slice(1);
      window.openInspectModal(`/admin/taxonomy/${domainPlural}/${id}/inspect`, `inspect-${domainSingular}-modal`, `Inspect ${title}`);
    }
  }

  // ── Slug Preview Wiring ──────────────────
  function initSlugPreviews() {
    const pairs = [
      ['new-category-name', 'new-category-slug-preview'],
      ['new-brand-name', 'new-brand-slug-preview'],
      ['new-topic-name', 'new-topic-slug-preview'],
      ['new-attribute-name', 'new-attribute-slug-preview']
    ];
    pairs.forEach(([inputId, previewId]) => {
      const input = document.getElementById(inputId);
      const preview = document.getElementById(previewId);
      if (input && preview) {
        input.addEventListener('input', () => {
          preview.textContent = slugify(input.value) || '—';
        });
      }
    });
  }

  // ── Create Buttons ───────────────────────
  function initCreateButtons() {
    document.getElementById('create-category-btn').addEventListener('click', createCategory);
    document.getElementById('create-brand-btn').addEventListener('click', createBrand);
    document.getElementById('create-topic-btn').addEventListener('click', createTopic);
    document.getElementById('create-attribute-btn').addEventListener('click', createAttribute);

    // Allow Enter key in name inputs to submit
    ['new-category-name', 'new-brand-name', 'new-topic-name', 'new-attribute-name'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          if (id.includes('category')) createCategory();
          if (id.includes('brand')) createBrand();
          if (id.includes('topic')) createTopic();
        }
      });
    });
  }

  // ── Init ─────────────────────────────────
  function init() {
    window.categoriesController = new AdminListController({
      domain: 'categories',
      endpoint: '/admin/taxonomy/categories',
      rowsEndpoint: '/admin/taxonomy/categories/rows',
      filterIds: ['category-filter-status', 'category-filter-health'],
      colspan: 8,
      autoInit: false
    });

    window.brandsController = new AdminListController({
      domain: 'brands',
      endpoint: '/admin/taxonomy/brands',
      rowsEndpoint: '/admin/taxonomy/brands/rows',
      filterIds: ['brand-filter-status', 'brand-filter-health'],
      colspan: 8,
      autoInit: false
    });

    window.topicsController = new AdminListController({
      domain: 'topics',
      endpoint: '/admin/taxonomy/topics',
      rowsEndpoint: '/admin/taxonomy/topics/rows',
      filterIds: ['topic-filter-status', 'topic-filter-health'],
      colspan: 7,
      autoInit: false
    });

    window.sectionsController = new AdminListController({
      domain: 'sections',
      endpoint: '/admin/taxonomy/sections',
      rowsEndpoint: '/admin/taxonomy/sections/rows',
      filterIds: ['section-filter-status', 'section-filter-health'],
      colspan: 8,
      autoInit: false
    });

    window.attributesController = new AdminListController({
      domain: 'attributes',
      endpoint: '/admin/taxonomy/attributes',
      rowsEndpoint: '/admin/taxonomy/attributes/rows',
      filterIds: ['attribute-filter-health'],
      colspan: 5,
      autoInit: false
    });

    window.genderFacetsController = new AdminListController({
      domain: 'gender_facets',
      endpoint: '/admin/taxonomy/gender_facets',
      rowsEndpoint: '/admin/taxonomy/gender_facets/rows',
      filterIds: ['gender_facet-filter-health'],
      colspan: 4,
      autoInit: false
    });

    window.intentFacetsController = new AdminListController({
      domain: 'intent_facets',
      endpoint: '/admin/taxonomy/intent_facets',
      rowsEndpoint: '/admin/taxonomy/intent_facets/rows',
      filterIds: ['intent_facet-filter-health'],
      colspan: 4,
      autoInit: false
    });

    window.priceTierFacetsController = new AdminListController({
      domain: 'price_tier_facets',
      endpoint: '/admin/taxonomy/price_tier_facets',
      rowsEndpoint: '/admin/taxonomy/price_tier_facets/rows',
      filterIds: ['price_tier_facet-filter-health'],
      colspan: 4,
      autoInit: false
    });

    initTabs();
    initTableDelegation();
    initSlugPreviews();
    initCreateButtons();

    // Load analytics on init
    loadTaxonomyAnalytics();

    // Load insights if we default to insights tab
    loadInsights();

    // Load categories tab if needed
    window.categoriesController.init();
    loadedTabs.add('categories');
  }

  document.addEventListener('DOMContentLoaded', init);
})();
