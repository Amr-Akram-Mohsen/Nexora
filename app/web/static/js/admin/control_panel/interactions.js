// ==============================
// ADMIN — INTERACTIONS / MODERATION
// interactions.js
// ==============================

(function () {
  'use strict';

  // ── State ──────────────────────────────
  let commentsPage = 1, commentsTotalPages = 1, commentsPerPage = 25;
  let reactionsPage = 1, reactionsTotalPages = 1;
  let commentDebounce = null;

  // ── Tab switching ───────────────────────
  function switchTab(tabName) {
    const btn = document.querySelector(`#interactions-tabs .admin-tab-btn[data-tab="${tabName}"]`);
    if (!btn) return;

    document.querySelectorAll('#interactions-tabs .admin-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.admin-tab-panel').forEach(p => p.classList.add('is-hidden'));

    btn.classList.add('active');
    const panelId = `tab-panel-${btn.dataset.tab}`;
    const panel = document.getElementById(panelId);
    if (panel) panel.classList.remove('is-hidden');

    if (btn.dataset.tab === 'reactions') {
      loadInteractionBreakdown();
      loadReactions(1);
    }
  }

  function initTabs() {
    document.getElementById('interactions-tabs').addEventListener('click', e => {
      const btn = e.target.closest('.admin-tab-btn');
      if (!btn) return;
      switchTab(btn.dataset.tab);
    });
  }

  // ── Stats Row ───────────────────────────
  function loadStatsRow() {
    fetch('/admin/interactions/stats')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('interactions-stats-row');
        const cards = [
          { icon: '💬', label: 'Comments',  value: data.comments },
          { icon: '👍', label: 'Likes',     value: data.likes },
          { icon: '👎', label: 'Dislikes',  value: data.dislikes },
          { icon: '👁️', label: 'Views',     value: data.views },
          { icon: '🔖', label: 'Saves',     value: data.saves },
          { icon: '🛒', label: 'Clicks',    value: data.item_clicks },
        ];
        container.className = 'dashboard-stats-grid';
        container.innerHTML = cards.map(c => `
          <div class="dashboard-stat-card">
            <div class="dashboard-stat-icon">${c.icon}</div>
            <h3 class="dashboard-stat-value">${(c.value || 0).toLocaleString()}</h3>
            <p class="dashboard-stat-label">${c.label}</p>
          </div>
        `).join('');
      })
      .catch(() => {
        document.getElementById('interactions-stats-row').innerHTML =
          '<p class="hint grid-full-width">Could not load stats.</p>';
      });
  }

  // ── Interaction Breakdown (reactions tab) ─
  function loadInteractionBreakdown() {
    renderInteractionBreakdown('moderation-interactions-breakdown');
  }

  // ── COMMENTS ────────────────────────────
  function getCommentFilters() {
    return {
      sentiment:   document.getElementById('filter-comment-sentiment').value,
      target_type: document.getElementById('filter-comment-target').value,
      search:      document.getElementById('comment-search').value,
    };
  }

  function loadComments(page) {
    commentsPage = page || 1;
    const filters = getCommentFilters();
    const params = new URLSearchParams({ page: commentsPage, per_page: commentsPerPage });
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });

    const tbody = document.getElementById('comments-table-body');
    tbody.innerHTML = getTableSpinnerHtml(7, "Loading…", "loading-height-md");

    fetch(`/admin/interactions/comments?${params}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => renderComments(data))
      .catch(() => {
        tbody.innerHTML = getTableErrorStateHtml(7, "Failed to load comments.");
      });
  }

  function renderComments(data) {
    const items = data.items || [];
    commentsTotalPages = data.pages || 1;
    const total = data.total || 0;
    const from  = ((commentsPage - 1) * commentsPerPage) + 1;
    const to    = Math.min(commentsPage * commentsPerPage, total);
    const tbody = document.getElementById('comments-table-body');

    document.getElementById('comments-count').textContent = total.toLocaleString();
    document.getElementById('comments-pagination-info').textContent =
      `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} comments`;
    document.getElementById('comments-page-indicator').textContent =
      `Page ${commentsPage} of ${commentsTotalPages}`;
    document.getElementById('comments-prev-btn').disabled = commentsPage <= 1;
    document.getElementById('comments-next-btn').disabled = commentsPage >= commentsTotalPages;

    if (!items.length) {
      tbody.innerHTML = getTableEmptyStateHtml(7, "No comments found.", "Try adjusting filters.", "loading-height-md");
      return;
    }

    const sentimentClass = { positive: 'active', negative: 'inactive', neutral: 'user', spam: 'admin' };

    tbody.innerHTML = '';
    items.forEach(c => {
      const tr = document.createElement('tr');
      const sentClass = sentimentClass[c.sentiment] || 'user';
      tr.innerHTML = `
        <td><span class="user-cell-name">#${c.id}</span></td>
        <td>
          <span class="user-cell-name" title="${escapeHtml(c.content)}">${escapeHtml(c.preview)}</span>
          ${c.parent_id ? '<div class="user-cell-email">↩ Reply</div>' : ''}
        </td>
        <td>
          <span class="user-cell-name">${escapeHtml(c.user_name)}</span>
          <div class="user-cell-email">#${c.user_id}</div>
        </td>
        <td>
          <span class="user-cell-name">${escapeHtml(c.target_title)}</span>
          <div class="user-cell-email">${c.target_type}</div>
        </td>
        <td>
          <span class="status-badge ${sentClass}">${c.sentiment}</span>
        </td>
        <td><span class="user-cell-email">${formatDate(c.created_at)}</span></td>
        <td>
          <div class="user-actions-group">
            <button class="user-action-btn user-action-delete"
              data-action="delete-comment"
              data-comment-id="${c.id}">🗑</button>
            <button class="user-action-btn"
              data-action="flag-comment"
              data-comment-id="${c.id}">🚩 Flag</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function deleteComment(id, btn) {
    showModal(
      'Delete Comment',
      'Are you sure you want to permanently delete this comment and all its replies?',
      () => {
        if (btn) { btn.disabled = true; }
        fetch(`/admin/interactions/comments/${id}`, { method: 'DELETE' })
          .then(r => r.json())
          .then(d => {
            if (d.success) { showToast('Comment deleted.', 'success'); loadComments(commentsPage); }
            else { showToast(d.error || 'Delete failed.', 'error'); if (btn) btn.disabled = false; }
          })
          .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
      }
    );
  }

  function flagComment(id, btn) {
    if (btn) btn.disabled = true;
    fetch(`/admin/interactions/comments/${id}/flag`, { method: 'POST' })
      .then(r => r.json())
      .then(d => {
        if (d.success) { showToast('Comment flagged as spam.', 'success'); loadComments(commentsPage); }
        else { showToast(d.error || 'Flag failed.', 'error'); if (btn) btn.disabled = false; }
      })
      .catch(() => { showToast('Flag failed.', 'error'); if (btn) btn.disabled = false; });
  }

  // ── REACTIONS ────────────────────────────
  function loadReactions(page) {
    reactionsPage = page || 1;
    const type = document.getElementById('filter-reaction-type').value;
    const params = new URLSearchParams({ page: reactionsPage, per_page: 25 });
    if (type) params.set('type', type);

    const tbody = document.getElementById('reactions-table-body');
    tbody.innerHTML = getTableSpinnerHtml(6, "Loading…", "loading-height-md");

    fetch(`/admin/interactions/reactions?${params}`)
      .then(r => r.json())
      .then(data => {
        const items = data.items || [];
        reactionsTotalPages = data.pages || 1;
        const total = data.total || 0;
        const from  = ((reactionsPage - 1) * 25) + 1;
        const to    = Math.min(reactionsPage * 25, total);

        document.getElementById('reactions-pagination-info').textContent =
          `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} reactions`;
        document.getElementById('reactions-page-indicator').textContent =
          `Page ${reactionsPage} of ${reactionsTotalPages}`;
        document.getElementById('reactions-prev-btn').disabled = reactionsPage <= 1;
        document.getElementById('reactions-next-btn').disabled = reactionsPage >= reactionsTotalPages;

        if (!items.length) {
          tbody.innerHTML = getTableEmptyStateHtml(6, "No reactions found.", "", "loading-height-md");
          return;
        }

        tbody.innerHTML = '';
        items.forEach(r => {
          const tr = document.createElement('tr');
          const typeClass = r.type === 'like' ? 'active' : 'inactive';
          tr.innerHTML = `
            <td><span class="user-cell-name">#${r.id}</span></td>
            <td>
              <span class="user-cell-name">${escapeHtml(r.user_name)}</span>
              <div class="user-cell-email">#${r.user_id}</div>
            </td>
            <td><span class="status-badge ${typeClass}">${r.type}</span></td>
            <td>${r.target_type}</td>
            <td>#${r.target_id}</td>
            <td><span class="user-cell-email">${formatDate(r.created_at)}</span></td>
          `;
          tbody.appendChild(tr);
        });
      })
      .catch(() => {
        tbody.innerHTML = getTableErrorStateHtml(6, "Failed to load reactions.");
      });
  }

  // ── Utilities ────────────────────────────
  // Exposes global escapeHtml and formatDate from core.js

  function applyUrlFilters() {
    if (typeof getUrlQueryParams !== "function") return;
    const params = getUrlQueryParams();
    
    // Switch to active tab if specified
    if (params.tab) {
      switchTab(params.tab);
    }
    
    const filterMap = {
      search: "comment-search",
      sentiment: "filter-comment-sentiment",
      target_type: "filter-comment-target"
    };

    for (const [paramKey, elementId] of Object.entries(filterMap)) {
      if (params[paramKey] !== undefined) {
        const el = document.getElementById(elementId);
        if (el) {
          el.value = params[paramKey];
        }
      }
    }
  }

  // ── Init ─────────────────────────────────
  function init() {
    initTabs();
    loadStatsRow();
    applyUrlFilters();

    const params = typeof getUrlQueryParams === "function" ? getUrlQueryParams() : {};
    if (params.tab !== 'reactions') {
      loadComments(1);
    }

    // Comment filters
    document.getElementById('comment-search').addEventListener('input', () => {
      clearTimeout(commentDebounce);
      commentDebounce = setTimeout(() => loadComments(1), 400);
    });
    ['filter-comment-sentiment', 'filter-comment-target'].forEach(id => {
      document.getElementById(id).addEventListener('change', () => loadComments(1));
    });
    document.getElementById('clear-comment-filters-btn').addEventListener('click', () => {
      document.getElementById('comment-search').value = '';
      document.getElementById('filter-comment-sentiment').value = '';
      document.getElementById('filter-comment-target').value = '';
      loadComments(1);
    });

    // Comment pagination
    document.getElementById('comments-per-page').addEventListener('change', e => {
      commentsPerPage = parseInt(e.target.value, 10);
      loadComments(1);
    });
    document.getElementById('comments-prev-btn').addEventListener('click', () => {
      if (commentsPage > 1) loadComments(commentsPage - 1);
    });
    document.getElementById('comments-next-btn').addEventListener('click', () => {
      if (commentsPage < commentsTotalPages) loadComments(commentsPage + 1);
    });

    // Comments table delegation
    document.getElementById('comments-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'delete-comment') deleteComment(btn.dataset.commentId, btn);
      if (btn.dataset.action === 'flag-comment') flagComment(btn.dataset.commentId, btn);
    });

    // Reactions filter
    document.getElementById('filter-reaction-type').addEventListener('change', () => loadReactions(1));
    document.getElementById('reactions-prev-btn').addEventListener('click', () => {
      if (reactionsPage > 1) loadReactions(reactionsPage - 1);
    });
    document.getElementById('reactions-next-btn').addEventListener('click', () => {
      if (reactionsPage < reactionsTotalPages) loadReactions(reactionsPage + 1);
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
