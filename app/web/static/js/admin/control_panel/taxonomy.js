// ==============================
// ADMIN — TAXONOMY MANAGEMENT
// taxonomy.js
// ==============================

(function () {
  'use strict';

  const TABS = ['categories', 'brands', 'topics', 'sections'];
  const loadedTabs = new Set();
  let searchDebounce = null;

  // ── Slug helper (mirrors Python's generate_slug) ─────────────
  function slugify(str) {
    return (str || '')
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_-]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  // Exposes global escapeHtml from core.js

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
      if (!loadedTabs.has(tab)) { loadTab(tab); }
    });
  }

  function loadTab(tab) {
    loadedTabs.add(tab);
    switch (tab) {
      case 'categories': return loadCategories();
      case 'brands':     return loadBrands();
      case 'topics':     return loadTopics();
      case 'sections':   return loadSections();
    }
  }

  // ── Generic Fetch ─────────────────────────────────────────────
  function fetchList(endpoint, onSuccess, onError) {
    return fetch(endpoint)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(onSuccess)
      .catch(onError || (() => {}));
  }

  // ────────────────────────────────────────────
  // CATEGORIES
  // ────────────────────────────────────────────
  function loadCategories(search) {
    const url = search ? `/admin/taxonomy/categories?search=${encodeURIComponent(search)}` : '/admin/taxonomy/categories';
    const tbody = document.getElementById('categories-table-body');
    tbody.innerHTML = getTableSpinnerHtml(6, "Loading…", "loading-height-sm");

    fetchList(url, data => renderCategories(data), () => {
      tbody.innerHTML = getTableErrorStateHtml(6, "Failed to load categories.");
    });
  }

  function renderCategories(items) {
    const tbody = document.getElementById('categories-table-body');
    if (!items.length) {
      tbody.innerHTML = getTableEmptyStateHtml(6, "No categories yet.", "", "loading-height-sm");
      return;
    }
    tbody.innerHTML = '';
    items.forEach(cat => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="user-cell-name">#${cat.id}</span></td>
        <td><span class="user-cell-name">${escapeHtml(cat.name)}</span></td>
        <td><code class="admin-slug-code">${escapeHtml(cat.slug)}</code></td>
        <td>
          <label class="admin-toggle" title="Toggle active">
            <input type="checkbox" class="admin-toggle-input"
              data-action="toggle-category"
              data-id="${cat.id}"
              ${cat.is_active ? 'checked' : ''} />
            <span class="status-badge ${cat.is_active ? 'active' : 'inactive'}">
              ${cat.is_active ? 'Active' : 'Inactive'}
            </span>
          </label>
        </td>
        <td>
          <span class="status-badge ${cat.is_leaf ? 'user' : 'admin'}">
            ${cat.is_leaf ? 'Leaf' : 'Parent'}
          </span>
        </td>
        <td>
          <button class="user-action-btn user-action-delete"
            data-action="delete-category"
            data-id="${cat.id}"
            data-name="${escapeHtml(cat.name)}">🗑</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
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
        loadCategories();
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteCategory(id, name, btn) {
    showModal('Delete Category', `Delete "${name}"? This may affect contents and products assigned to it.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/categories/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); loadCategories(); }
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
        loadCategories();
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ────────────────────────────────────────────
  // BRANDS
  // ────────────────────────────────────────────
  function loadBrands(search) {
    const url = search ? `/admin/taxonomy/brands?search=${encodeURIComponent(search)}` : '/admin/taxonomy/brands';
    const tbody = document.getElementById('brands-table-body');
    tbody.innerHTML = getTableSpinnerHtml(7, "Loading…", "loading-height-sm");

    fetchList(url, data => renderBrands(data), () => {
      tbody.innerHTML = getTableErrorStateHtml(7, "Failed to load brands.");
    });
  }

  function renderBrands(items) {
    const tbody = document.getElementById('brands-table-body');
    if (!items.length) {
      tbody.innerHTML = getTableEmptyStateHtml(7, "No brands yet.", "", "loading-height-sm");
      return;
    }
    tbody.innerHTML = '';
    items.forEach(b => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="user-cell-name">#${b.id}</span></td>
        <td><span class="user-cell-name">${escapeHtml(b.name)}</span></td>
        <td><code class="admin-slug-code">${escapeHtml(b.slug)}</code></td>
        <td>${escapeHtml(b.industry) || '—'}</td>
        <td>
          <label class="admin-toggle">
            <input type="checkbox" class="admin-toggle-input"
              data-action="toggle-brand"
              data-id="${b.id}"
              ${b.is_active ? 'checked' : ''} />
            <span class="status-badge ${b.is_active ? 'active' : 'inactive'}">
              ${b.is_active ? 'Active' : 'Inactive'}
            </span>
          </label>
        </td>
        <td>
          <span class="status-badge ${b.is_featured ? 'admin' : 'user'}">
            ${b.is_featured ? 'Featured' : '—'}
          </span>
        </td>
        <td>
          <button class="user-action-btn user-action-delete"
            data-action="delete-brand"
            data-id="${b.id}"
            data-name="${escapeHtml(b.name)}">🗑</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
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
        loadBrands();
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteBrand(id, name, btn) {
    showModal('Delete Brand', `Delete "${name}"? Items and content tagged with this brand will lose the association.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/brands/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); loadBrands(); }
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
        loadBrands();
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ────────────────────────────────────────────
  // TOPICS
  // ────────────────────────────────────────────
  function loadTopics(search) {
    const url = search ? `/admin/taxonomy/topics?search=${encodeURIComponent(search)}` : '/admin/taxonomy/topics';
    const tbody = document.getElementById('topics-table-body');
    tbody.innerHTML = getTableSpinnerHtml(6, "Loading…", "loading-height-sm");

    fetchList(url, data => renderTopics(data), () => {
      tbody.innerHTML = getTableErrorStateHtml(6, "Failed to load topics.");
    });
  }

  function renderTopics(items) {
    const tbody = document.getElementById('topics-table-body');
    if (!items.length) {
      tbody.innerHTML = getTableEmptyStateHtml(6, "No topics yet.", "", "loading-height-sm");
      return;
    }
    tbody.innerHTML = '';
    items.forEach(t => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="user-cell-name">#${t.id}</span></td>
        <td><span class="user-cell-name">${escapeHtml(t.name)}</span></td>
        <td><code class="admin-slug-code">${escapeHtml(t.slug)}</code></td>
        <td>
          <label class="admin-toggle">
            <input type="checkbox" class="admin-toggle-input"
              data-action="toggle-topic"
              data-id="${t.id}"
              ${t.is_active ? 'checked' : ''} />
            <span class="status-badge ${t.is_active ? 'active' : 'inactive'}">
              ${t.is_active ? 'Active' : 'Inactive'}
            </span>
          </label>
        </td>
        <td>
          <span class="status-badge ${t.is_featured ? 'admin' : 'user'}">
            ${t.is_featured ? 'Featured' : '—'}
          </span>
        </td>
        <td>
          <button class="user-action-btn user-action-delete"
            data-action="delete-topic"
            data-id="${t.id}"
            data-name="${escapeHtml(t.name)}">🗑</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
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
        loadTopics();
      })
      .catch(() => showToast('Create failed.', 'error'));
  }

  function deleteTopic(id, name, btn) {
    showModal('Delete Topic', `Delete "${name}"? Content tagged with this topic will lose the association.`, () => {
      if (btn) btn.disabled = true;
      fetch(`/admin/taxonomy/topics/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(d => {
          if (d.success) { showToast(d.message, 'success'); loadTopics(); }
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
        loadTopics();
      })
      .catch(() => { showToast('Update failed.', 'error'); el.checked = !isActive; });
  }

  // ────────────────────────────────────────────
  // SECTIONS
  // ────────────────────────────────────────────
  function loadSections() {
    const tbody = document.getElementById('sections-table-body');
    tbody.innerHTML = getTableSpinnerHtml(6, "Loading…", "loading-height-sm");

    fetchList('/admin/taxonomy/sections', data => renderSections(data), () => {
      tbody.innerHTML = getTableErrorStateHtml(6, "Failed to load sections.");
    });
  }

  function renderSections(items) {
    const tbody = document.getElementById('sections-table-body');
    if (!items.length) {
      tbody.innerHTML = getTableEmptyStateHtml(6, "No sections found.", "", "loading-height-sm");
      return;
    }
    tbody.innerHTML = '';
    items.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="user-cell-name">#${s.id}</span></td>
        <td><span class="user-cell-name">${escapeHtml(s.name)}</span></td>
        <td><code class="admin-slug-code">${escapeHtml(s.slug)}</code></td>
        <td class="text-muted" style="max-width:260px;white-space:normal;">${escapeHtml(s.description)}</td>
        <td>
          <label class="admin-toggle">
            <input type="checkbox" class="admin-toggle-input"
              data-action="toggle-section"
              data-id="${s.id}"
              ${s.is_active ? 'checked' : ''} />
            <span class="status-badge ${s.is_active ? 'active' : 'inactive'}">
              ${s.is_active ? 'Active' : 'Inactive'}
            </span>
          </label>
        </td>
        <td></td>
      `;
      tbody.appendChild(tr);
    });
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
        loadSections();
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

  // ── Search Wiring ────────────────────────
  function initSearch() {
    const searchMap = {
      'category-search': s => loadCategories(s),
      'brand-search':    s => loadBrands(s),
      'topic-search':    s => loadTopics(s),
    };
    Object.entries(searchMap).forEach(([inputId, fn]) => {
      const el = document.getElementById(inputId);
      if (!el) return;
      el.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => fn(el.value.trim()), 400);
      });
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
    initTabs();
    initTableDelegation();
    initSlugPreviews();
    initSearch();
    initCreateButtons();

    // Load first tab (categories)
    loadCategories();
    loadedTabs.add('categories');
  }

  document.addEventListener('DOMContentLoaded', init);
})();
