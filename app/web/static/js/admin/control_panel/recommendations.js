// ==============================
// ADMIN — RECOMMENDATIONS
// recommendations.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  let currentPage = 1;
  let totalPages  = 1;
  let perPage     = 25;
  let searchDebounce = null;

  // ── Stats Row ───────────────────────────
  function loadStats() {
    fetch('/admin/recommendations/stats')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('rec-stats-row');
        container.className = 'dashboard-stats-grid';
        container.innerHTML = [
          { icon: '🔗', label: 'Total Matches',     value: data.total_matches   },
          { icon: '📰', label: 'Linked Contents',   value: data.linked_contents },
          { icon: '🛍️', label: 'Linked Products',  value: data.linked_items    },
        ].map(c => `
          <div class="dashboard-stat-card">
            <div class="dashboard-stat-icon">${c.icon}</div>
            <h3 class="dashboard-stat-value">${(c.value || 0).toLocaleString()}</h3>
            <p class="dashboard-stat-label">${c.label}</p>
          </div>
        `).join('');
      })
      .catch(() => {
        document.getElementById('rec-stats-row').innerHTML =
          '<p class="hint" style="grid-column:1/-1;padding:1rem;">Could not load stats.</p>';
      });
  }

  // ── Load Matches ────────────────────────
  function loadMatches(page) {
    currentPage = page || 1;
    const search = (document.getElementById('rec-search') || {}).value || '';
    const params = new URLSearchParams({ page: currentPage, per_page: perPage });
    if (search) params.set('search', search);

    const tbody = document.getElementById('recs-table-body');
    tbody.innerHTML = `<tr><td colspan="7" class="table-loading-cell">
      <div class="dashboard-loading loading-height-lg"><div class="spinner"></div><p>Loading matches…</p></div>
    </td></tr>`;

    fetch(`/admin/recommendations/matches?${params}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => renderMatches(data))
      .catch(() => {
        tbody.innerHTML = `<tr><td colspan="7" class="table-loading-cell">
          <div class="dashboard-error"><span style="font-size:2rem">⚠️</span><p>Failed to load matches.</p></div>
        </td></tr>`;
      });
  }

  function renderMatches(data) {
    const items = data.items || [];
    totalPages = data.pages || 1;
    const total = data.total || 0;
    const from  = ((currentPage - 1) * perPage) + 1;
    const to    = Math.min(currentPage * perPage, total);
    const tbody = document.getElementById('recs-table-body');

    document.getElementById('rec-count').textContent = total.toLocaleString();
    document.getElementById('rec-pagination-info').textContent =
      `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} matches`;
    document.getElementById('rec-page-indicator').textContent =
      `Page ${currentPage} of ${totalPages}`;
    document.getElementById('rec-prev-btn').disabled = currentPage <= 1;
    document.getElementById('rec-next-btn').disabled = currentPage >= totalPages;

    if (!items.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="table-loading-cell">
        <div class="dashboard-empty">
          <span style="font-size:2.5rem;margin-bottom:1rem">🔗</span>
          <p>No content-product matches found.</p>
          <p style="font-size:0.8rem;opacity:0.7;">Run the article-item matcher to generate associations.</p>
        </div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = '';
    items.forEach(m => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <span class="user-cell-name">${escapeHtml(m.content_title)}</span>
          <div class="user-cell-email">#${m.content_id}</div>
        </td>
        <td>
          <span class="status-badge user" style="text-transform:capitalize;">${m.content_type || '—'}</span>
        </td>
        <td>${(m.content_views || 0).toLocaleString()}</td>
        <td>
          <span class="user-cell-name">${escapeHtml(m.item_name)}</span>
          <div class="user-cell-email">#${m.item_id}</div>
        </td>
        <td>
          <span class="status-badge user" style="text-transform:capitalize;">${m.item_type || '—'}</span>
        </td>
        <td>${(m.item_clicks || 0).toLocaleString()}</td>
        <td>
          <button class="user-action-btn user-action-delete"
            data-action="unlink-match"
            data-content-id="${m.content_id}"
            data-item-id="${m.item_id}"
            title="Remove this association">
            🔓 Unlink
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // ── Unlink ──────────────────────────────
  function unlinkMatch(contentId, itemId, btn) {
    showModal(
      'Remove Association',
      `Remove the link between this content and product? The association can be re-created by running the matcher.`,
      () => {
        if (btn) btn.disabled = true;
        fetch(`/admin/recommendations/matches/${contentId}/${itemId}`, { method: 'DELETE' })
          .then(r => r.json())
          .then(d => {
            if (d.success) {
              showToast('Association removed.', 'success');
              loadMatches(currentPage);
              loadStats();
            } else {
              showToast(d.error || 'Unlink failed.', 'error');
              if (btn) btn.disabled = false;
            }
          })
          .catch(() => { showToast('Unlink failed.', 'error'); if (btn) btn.disabled = false; });
      }
    );
  }

  // ── Utilities ────────────────────────────
  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str || '—';
    return d.innerHTML;
  }

  // ── Init ─────────────────────────────────
  function init() {
    loadStats();
    loadMatches(1);

    // Search
    document.getElementById('rec-search').addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => loadMatches(1), 400);
    });

    // Filters clear
    document.getElementById('clear-rec-filters-btn').addEventListener('click', () => {
      document.getElementById('rec-search').value = '';
      loadMatches(1);
    });

    // Per-page
    document.getElementById('rec-per-page').addEventListener('change', e => {
      perPage = parseInt(e.target.value, 10);
      loadMatches(1);
    });

    // Pagination
    document.getElementById('rec-prev-btn').addEventListener('click', () => {
      if (currentPage > 1) loadMatches(currentPage - 1);
    });
    document.getElementById('rec-next-btn').addEventListener('click', () => {
      if (currentPage < totalPages) loadMatches(currentPage + 1);
    });

    // Refresh
    document.getElementById('refresh-recs-btn').addEventListener('click', () => {
      loadStats();
      loadMatches(currentPage);
    });

    // Table delegation
    document.getElementById('recs-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'unlink-match') {
        unlinkMatch(btn.dataset.contentId, btn.dataset.itemId, btn);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
