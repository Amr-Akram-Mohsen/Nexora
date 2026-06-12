// ==============================
// ADMIN — SOURCES CONTROL PANEL
// sources.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  let currentPage = 1;
  let totalPages = 1;
  let perPage = 20;
  let searchDebounce = null;

  function getFilters() {
    return {
      search: (document.getElementById('sources-search') || {}).value || '',
    };
  }

  // ── Fetch & render sources ──────────────
  function loadSources(page) {
    currentPage = page || 1;
    const filters = getFilters();
    const params = new URLSearchParams({
      page: currentPage,
      per_page: perPage,
      ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    });

    const tbody = document.getElementById('sources-table-body');
    tbody.innerHTML = getTableSpinnerHtml(7, "Loading content sources…", "loading-height-md");

    fetch(`/admin/providers/sources?${params}`)
      .then(r => { if (!r.ok) throw new Error('Network error'); return r.json(); })
      .then(data => renderSources(data))
      .catch((err) => {
        console.error(err);
        tbody.innerHTML = getTableErrorStateHtml(7, "Failed to load sources.");
      });
  }

  function renderSources(data) {
    const sources = data.sources || [];
    totalPages    = data.pages || 1;
    const total   = data.total || 0;
    const from    = ((currentPage - 1) * perPage) + 1;
    const to      = Math.min(currentPage * perPage, total);
    const tbody   = document.getElementById('sources-table-body');

    // Update summary & pagination info
    document.getElementById('sources-count').textContent = total.toLocaleString();
    document.getElementById('sources-pagination-info').textContent =
      `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} sources`;
    document.getElementById('sources-page-indicator').textContent =
      `Page ${currentPage} of ${totalPages}`;
    document.getElementById('sources-prev-btn').disabled = currentPage <= 1;
    document.getElementById('sources-next-btn').disabled = currentPage >= totalPages;

    if (!sources.length) {
      tbody.innerHTML = getTableEmptyStateHtml(7, "No content sources found.", "Try adjusting your search term.", "loading-height-md");
      return;
    }

    tbody.innerHTML = '';
    sources.forEach(src => {
      const tr = document.createElement('tr');

      const latestTime = src.latest_activity ? formatDate(src.latest_activity, true) : '—';
      const statusBadge = src.is_active
        ? `<span class="status-badge active">Active</span>`
        : `<span class="status-badge inactive">Inactive</span>`;

      let latestArticleHtml = '—';
      if (src.latest_content) {
        latestArticleHtml = `
          <a href="/admin/contents?search=${src.latest_content.id}" class="overview-top-link-title text-deco-none font-bold">
            ${escapeHtml(src.latest_content.title)}
          </a>
          <div class="user-cell-email">ID: #${src.latest_content.id}</div>
        `;
      }

      tr.innerHTML = `
        <td>
          <span class="user-cell-name">#${src.id}</span>
          <div class="mt-1">${statusBadge}</div>
        </td>
        <td>
          <span class="user-cell-name">${escapeHtml(src.name)}</span>
          <div class="user-cell-email"><a href="https://${src.domain}" target="_blank" class="text-muted">${escapeHtml(src.domain)}</a></div>
          <div class="user-cell-email">slug: <code>${escapeHtml(src.slug)}</code></div>
        </td>
        <td>
          <span class="status-badge admin">
            ${src.authority_score} / 100
          </span>
        </td>
        <td>
          <strong class="inspect-brand-purple">${src.content_count.toLocaleString()}</strong>
        </td>
        <td>
          <span class="text-foreground">${latestTime}</span>
        </td>
        <td class="cell-wrap-ellipsis">
          ${latestArticleHtml}
        </td>
        <td>
          <div class="user-actions-group">
            <a href="/admin/contents?source=${src.slug}" class="user-action-btn user-action-inspect inspect-btn text-deco-none d-inline-block">
              👁️ View Content
            </a>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // ── Utilities ────────────────────────────
  // Exposes global escapeHtml and formatDate from core.js

  // ── Event Wiring ─────────────────────────
  function init() {
    loadSources(1);

    // Search debounce
    document.getElementById('sources-search').addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => loadSources(1), 400);
    });

    // Per-page
    document.getElementById('sources-per-page').addEventListener('change', e => {
      perPage = parseInt(e.target.value, 10);
      loadSources(1);
    });

    // Pagination
    document.getElementById('sources-prev-btn').addEventListener('click', () => {
      if (currentPage > 1) loadSources(currentPage - 1);
    });
    document.getElementById('sources-next-btn').addEventListener('click', () => {
      if (currentPage < totalPages) loadSources(currentPage + 1);
    });

    // Reset filters
    document.getElementById('clear-sources-filters-btn').addEventListener('click', () => {
      document.getElementById('sources-search').value = '';
      loadSources(1);
    });

    // Refresh button
    document.getElementById('refresh-sources-btn').addEventListener('click', () => loadSources(currentPage));
  }

  document.addEventListener('DOMContentLoaded', init);
})();
