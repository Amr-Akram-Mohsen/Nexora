// ==============================
// ADMIN — TAXONOMY MANAGEMENT
// taxonomy.js
// ==============================

(function () {
  'use strict';

  const loadedTabs = new Set();
  let categoriesController;
  let brandsController;
  let topicsController;
  let sectionsController;

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
    if (!loadedTabs.has(tab)) {
      loadedTabs.add(tab);
      if (tab === 'categories') categoriesController.init();
      if (tab === 'brands')     brandsController.init();
      if (tab === 'topics')     topicsController.init();
      if (tab === 'sections')   sectionsController.init();
    } else {
      if (tab === 'categories') categoriesController.load(1);
      if (tab === 'brands')     brandsController.load(1);
      if (tab === 'topics')     topicsController.load(1);
      if (tab === 'sections')   sectionsController.load(1);
    }
  }

  // ── CATEGORIES RENDER ──────────────────────
  function renderCategoryRow(cat) {
    const template = document.getElementById('categories-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.cat-cell-name').textContent = cat.name;

    const cb = clone.querySelector('.cat-cell-checkbox');
    cb.dataset.id = cat.id;
    cb.checked = cat.is_active;

    const badge = clone.querySelector('.cat-cell-badge');
    badge.className = `status-badge ${cat.is_active ? 'active' : 'inactive'}`;
    badge.textContent = cat.is_active ? 'Active' : 'Inactive';

    const leaf = clone.querySelector('.cat-cell-leaf');
    leaf.className = `status-badge ${cat.is_leaf ? 'user' : 'admin'}`;
    leaf.textContent = cat.is_leaf ? 'Leaf' : 'Parent';

    const delBtn = clone.querySelector('.cat-cell-delete');
    delBtn.dataset.id = cat.id;
    delBtn.dataset.name = cat.name;

    return tr;
  }

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
        categoriesController.load(1);
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteCategory(id, name, btn) {
    showModal('Delete Category', `Delete "${name}"? This may affect contents and products assigned to it.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/categories/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); categoriesController.load(1); }
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
        categoriesController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── BRANDS RENDER ─────────────────────────
  function renderBrandRow(b) {
    const template = document.getElementById('brands-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.brand-cell-name').textContent = b.name;
    clone.querySelector('.brand-cell-industry').textContent = b.industry || '—';

    const cb = clone.querySelector('.brand-cell-checkbox');
    cb.dataset.id = b.id;
    cb.checked = b.is_active;

    const badge = clone.querySelector('.brand-cell-badge');
    badge.className = `status-badge ${b.is_active ? 'active' : 'inactive'}`;
    badge.textContent = b.is_active ? 'Active' : 'Inactive';

    const feat = clone.querySelector('.brand-cell-featured');
    feat.className = `status-badge ${b.is_featured ? 'admin' : 'user'}`;
    feat.textContent = b.is_featured ? 'Featured' : '—';

    const delBtn = clone.querySelector('.brand-cell-delete');
    delBtn.dataset.id = b.id;
    delBtn.dataset.name = b.name;

    return tr;
  }

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
        brandsController.load(1);
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  // Delete brand
  function deleteBrand(id, name, btn) {
    showModal('Delete Brand', `Delete "${name}"? Items and content tagged with this brand will lose the association.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/brands/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); brandsController.load(1); }
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
        brandsController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── TOPICS RENDER ─────────────────────────
  function renderTopicRow(t) {
    const template = document.getElementById('topics-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.topic-cell-name').textContent = t.name;

    const cb = clone.querySelector('.topic-cell-checkbox');
    cb.dataset.id = t.id;
    cb.checked = t.is_active;

    const badge = clone.querySelector('.topic-cell-badge');
    badge.className = `status-badge ${t.is_active ? 'active' : 'inactive'}`;
    badge.textContent = t.is_active ? 'Active' : 'Inactive';

    const feat = clone.querySelector('.topic-cell-featured');
    feat.className = `status-badge ${t.is_featured ? 'admin' : 'user'}`;
    feat.textContent = t.is_featured ? 'Featured' : '—';

    const delBtn = clone.querySelector('.topic-cell-delete');
    delBtn.dataset.id = t.id;
    delBtn.dataset.name = t.name;

    return tr;
  }

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
        topicsController.load(1);
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteTopic(id, name, btn) {
    showModal('Delete Topic', `Delete "${name}"? Content tagged with this topic will lose the association.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/topics/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); topicsController.load(1); }
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
        topicsController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── SECTIONS RENDER ───────────────────────
  function renderSectionRow(s) {
    const template = document.getElementById('sections-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.section-cell-name').textContent = s.name;
    clone.querySelector('.section-cell-desc').textContent = s.description;

    const cb = clone.querySelector('.section-cell-checkbox');
    cb.dataset.id = s.id;
    cb.checked = s.is_active;

    const badge = clone.querySelector('.section-cell-badge');
    badge.className = `status-badge ${s.is_active ? 'active' : 'inactive'}`;
    badge.textContent = s.is_active ? 'Active' : 'Inactive';

    return tr;
  }

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
        sectionsController.load(1);
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ── Global table event delegation ────────
  function initTableDelegation() {
    document.addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;

      const { action, id, name } = btn.dataset;

      // Delete actions
      if (action === 'delete-category') deleteCategory(id, name, btn);
      if (action === 'delete-brand')    deleteBrand(id, name, btn);
      if (action === 'delete-topic')    deleteTopic(id, name, btn);
    });

    // Toggle checkboxes (use change event)
    document.addEventListener('change', e => {
      const el = e.target;
      if (!el.matches('[data-action]')) return;
      const { action, id } = el.dataset;
      const isActive = el.checked;
      if (action === 'toggle-category') toggleCategoryActive(id, isActive, el);
      if (action === 'toggle-brand')    toggleBrandActive(id, isActive, el);
      if (action === 'toggle-topic')    toggleTopicActive(id, isActive, el);
      if (action === 'toggle-section')  toggleSectionActive(id, isActive, el);
    });
  }

  // ── Slug Preview Wiring ──────────────────
  function initSlugPreviews() {
    const pairs = [
      ['new-category-name', 'new-category-slug-preview'],
      ['new-brand-name',    'new-brand-slug-preview'],
      ['new-topic-name',    'new-topic-slug-preview'],
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

    // Allow Enter key in name inputs to submit
    ['new-category-name', 'new-brand-name', 'new-topic-name'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          if (id.includes('category')) createCategory();
          if (id.includes('brand'))    createBrand();
          if (id.includes('topic'))    createTopic();
        }
      });
    });
  }

  // ── Init ─────────────────────────────────
  function init() {
    categoriesController = new AdminListController({
      domain: 'categories',
      endpoint: '/admin/taxonomy/categories',
      tbodyId: 'categories-table-body',
      searchId: 'category-search',
      filterIds: [],
      colspan: 4,
      rowTemplateId: 'categories-row-template',
      renderRow: renderCategoryRow,
      autoInit: false
    });

    brandsController = new AdminListController({
      domain: 'brands',
      endpoint: '/admin/taxonomy/brands',
      tbodyId: 'brands-table-body',
      searchId: 'brand-search',
      filterIds: [],
      colspan: 5,
      rowTemplateId: 'brands-row-template',
      renderRow: renderBrandRow,
      autoInit: false
    });

    topicsController = new AdminListController({
      domain: 'topics',
      endpoint: '/admin/taxonomy/topics',
      tbodyId: 'topics-table-body',
      searchId: 'topic-search',
      filterIds: [],
      colspan: 4,
      rowTemplateId: 'topics-row-template',
      renderRow: renderTopicRow,
      autoInit: false
    });

    sectionsController = new AdminListController({
      domain: 'sections',
      endpoint: '/admin/taxonomy/sections',
      tbodyId: 'sections-table-body',
      searchId: '',
      filterIds: [],
      colspan: 4,
      rowTemplateId: 'sections-row-template',
      renderRow: renderSectionRow,
      autoInit: false
    });

    initTabs();
    initTableDelegation();
    initSlugPreviews();
    initCreateButtons();

    // Load first tab (categories)
    categoriesController.init();
    loadedTabs.add('categories');
  }

  document.addEventListener('DOMContentLoaded', init);
})();
