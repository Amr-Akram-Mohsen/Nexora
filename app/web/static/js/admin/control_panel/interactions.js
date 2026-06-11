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
  function initTabs() {
    document.getElementById('interactions-tabs').addEventListener('click', e => {
      const btn = e.target.closest('.admin-tab-btn');
      if (!btn) return;

      document.querySelectorAll('#interactions-tabs .admin-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.admin-tab-panel').forEach(p => p.classList.add('is-hidden'));

      btn.classList.add('active');
      const panelId = `tab-panel-${btn.dataset.tab}`;
      document.getElementById(panelId).classList.remove('is-hidden');

      if (btn.dataset.tab === 'reactions' && reactionsPage === 1) {
        loadInteractionBreakdown();
        loadReactions(1);
      }
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
          '<p class="hint" style="grid-column:1/-1;padding:1rem;">Could not load stats.</p>';
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
    tbody.innerHTML = `<tr><td colspan="7" class="table-loading-cell">
      <div class="dashboard-loading loading-height-md"><div class="spinner"></div><p>Loading…</p></div>
    </td></tr>`;

    fetch(`/admin/interactions/comments?${params}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => renderComments(data))
      .catch(() => {
        tbody.innerHTML = `<tr><td colspan="7" class="table-loading-cell">
          <div class="dashboard-error"><span style="font-size:2rem">⚠️</span><p>Failed to load comments.</p></div>
        </td></tr>`;
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
      tbody.innerHTML = `<tr><td colspan="7" class="table-loading-cell">
        <div class="dashboard-empty">
          <span style="font-size:2.5rem;margin-bottom:1rem">📭</span>
          <p>No comments found. Try adjusting filters.</p>
        </div>
      </td></tr>`;
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
              style="font-size:0.75rem;"
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
    tbody.innerHTML = `<tr><td colspan="6" class="table-loading-cell">
      <div class="dashboard-loading loading-height-md"><div class="spinner"></div><p>Loading…</p></div>
    </td></tr>`;

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
          tbody.innerHTML = `<tr><td colspan="6" class="table-loading-cell">
            <div class="dashboard-empty"><span style="font-size:2.5rem;margin-bottom:1rem">📭</span><p>No reactions found.</p></div>
          </td></tr>`;
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
        tbody.innerHTML = `<tr><td colspan="6" class="table-loading-cell">
          <div class="dashboard-error"><span style="font-size:2rem">⚠️</span><p>Failed to load reactions.</p></div>
        </td></tr>`;
      });
  }

  // ── Utilities ────────────────────────────
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '—';
    return div.innerHTML;
  }

  function formatDate(str) {
    if (!str) return '—';
    try { return new Date(str).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); }
    catch { return str; }
  }

  // ── Init ─────────────────────────────────
  function init() {
    initTabs();
    loadStatsRow();
    loadComments(1);

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
