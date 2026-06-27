// ==============================
// ADMIN — TAXONOMY MANAGEMENT
// taxonomy.js
// ==============================

(function () {
  'use strict';

  const loadedTabs = new Set();

  function loadTaxonomyAnalytics() {
    if (typeof fetchAndInjectHtml === 'function') {
      fetchAndInjectHtml('/admin/taxonomy/analytics', 'taxonomy-analytics-dashboard', 'Loading analytics...');
    }
  }

  function loadInsights() {
    if (typeof fetchAndInjectHtml === 'function') {
      fetchAndInjectHtml('/admin/taxonomy/insights/suggestions', 'insights-suggestions-container', 'Loading suggestions...');
      fetchAndInjectHtml('/admin/taxonomy/insights/coherence', 'insights-coherence-container', 'Loading coherence analysis...');
    }
  }

  function applyInsightSuggestion(contentId, type, suggestedId) {
    if (!confirm(`Apply ${type} suggestion?`)) return;
    window.api.post('/admin/taxonomy/insights/apply', { content_id: contentId, type: type, suggested_id: suggestedId })
      .then(d => {
        if (d.success) {
          alert("Applied successfully!");
          loadInsights(); // reload tables
        } else {
          alert("Error applying suggestion: " + d.error);
        }
      })
      .catch(err => {
        alert("Error applying suggestion");
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
    initAdminTabs('taxonomy-tabs', loadTab);
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

    window.api.post('/admin/taxonomy/categories', { name })
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
      window.api.delete(`/admin/taxonomy/categories/${id}`)
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); window.categoriesController.load(1); }
          else { showToast(d.error, 'error'); if (btn) btn.disabled = false; }
        })
        .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
    });
  }

  function toggleCategoryActive(id, isActive, el) {
    window.api.put(`/admin/taxonomy/categories/${id}`, { is_active: isActive })
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

    window.api.post('/admin/taxonomy/brands', { name, industry: industry || null })
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
      window.api.delete(`/admin/taxonomy/brands/${id}`)
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); window.brandsController.load(1); }
          else { showToast(d.error, 'error'); if (btn) btn.disabled = false; }
        })
        .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
    });
  }

  function toggleBrandActive(id, isActive, el) {
    window.api.put(`/admin/taxonomy/brands/${id}`, { is_active: isActive })
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

    window.api.post('/admin/taxonomy/topics', { name })
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
      window.api.delete(`/admin/taxonomy/topics/${id}`)
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); window.topicsController.load(1); }
          else { showToast(d.error, 'error'); if (btn) btn.disabled = false; }
        })
        .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
    });
  }

  function toggleTopicActive(id, isActive, el) {
    window.api.put(`/admin/taxonomy/topics/${id}`, { is_active: isActive })
      .then(d => {
        if (d.error) { showToast(d.error, 'error'); el.checked = !isActive; return; }
        showToast(`Topic ${isActive ? 'activated' : 'deactivated'}.`, 'success');
        window.topicsController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── SECTIONS ─────────────────────────────
  function toggleSectionActive(id, isActive, el) {
    window.api.put(`/admin/taxonomy/sections/${id}`, { is_active: isActive })
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

    window.api.post('/admin/taxonomy/attributes', { name })
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
      window.api.delete(`/admin/taxonomy/attributes/${id}`)
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

      const { action, id, name, domain, sourceId, targetId } = btn.dataset;

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

      // Duplicate detection actions
      if (action === 'find-duplicates') openDuplicatesModal(domain);
      if (action === 'merge-duplicate') mergeDuplicate(domain, sourceId, targetId, btn);
      
      // Insight suggestions
      if (action === 'apply-insight') {
          applyInsightSuggestion(id, btn.dataset.insightType, btn.dataset.suggestedId);
      }
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
  }

  // ── DUPLICATES LOGIC ───────────────────────
  function openDuplicatesModal(domain) {
    const modal = document.getElementById('admin-duplicates-modal');
    if (modal) modal.classList.add('active');
    
    if (typeof fetchAndInjectHtml === 'function') {
      fetchAndInjectHtml(`/admin/taxonomy/duplicates?type=${domain}`, 'admin-duplicates-body', 'Scanning for duplicates...');
    }
  }

  function mergeDuplicate(domain, sourceId, targetId, btn) {
    if (!confirm(`Are you sure you want to merge ID ${sourceId} into ID ${targetId}? The source entity will be deleted and its contents will be moved to the target.`)) return;

    if (btn) btn.disabled = true;
    window.api.post('/admin/taxonomy/merge', { domain, source_id: sourceId, target_id: targetId })
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
