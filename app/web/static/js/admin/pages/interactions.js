// ==============================
// ADMIN — INTERACTIONS / MODERATION
// Refactored: HTML partial mode — no renderRow, no JS HTML building
// ==============================

(function () {
  'use strict';

  let commentsController;
  let reactionsController;
  let viewsController;
  let clicksController;
  let savesController;

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
      reactionsController.load(1);
    } else if (btn.dataset.tab === 'comments') {
      commentsController.load(1);
    } else if (btn.dataset.tab === 'views') {
      viewsController.load(1);
    } else if (btn.dataset.tab === 'clicks') {
      clicksController.load(1);
    } else if (btn.dataset.tab === 'saves') {
      savesController.load(1);
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
        container.innerHTML = '';
        container.className = 'dashboard-stats-grid';

        const template = document.getElementById('interactions-stat-card-template');
        const cards = [
          { icon: '💬', label: 'Comments', value: data.comments },
          { icon: '👍', label: 'Likes',    value: data.likes    },
          { icon: '👎', label: 'Dislikes', value: data.dislikes },
          { icon: '👁️', label: 'Views',   value: data.views    },
          { icon: '🔖', label: 'Saves',    value: data.saves    },
          { icon: '🛒', label: 'Clicks',   value: data.item_clicks },
        ];

        cards.forEach(c => {
          const clone = template.content.cloneNode(true);
          clone.querySelector('.dashboard-stat-icon').textContent  = c.icon;
          clone.querySelector('.dashboard-stat-value').textContent = (c.value || 0).toLocaleString();
          clone.querySelector('.dashboard-stat-label').textContent = c.label;
          container.appendChild(clone);
        });
      })
      .catch(() => {
        document.getElementById('interactions-stats-row').innerHTML =
          '<p class="hint grid-full-width">Could not load stats.</p>';
      });
  }

  function loadInteractionBreakdown() {
    if (typeof fetchAndInjectHtml === 'function') {
      fetchAndInjectHtml('/admin/dashboard/widget/interactions-breakdown', 'moderation-interactions-breakdown', 'Loading breakdown...');
    }
  }

  // ── Comment Moderation Actions ───────────
  function deleteComment(id, btn, modal) {
    showModal(
      'Delete Comment',
      'Are you sure you want to permanently delete this comment and all its replies?',
      () => {
        if (btn) btn.disabled = true;
        fetch(`/admin/interactions/comments/${id}`, { method: 'DELETE' })
          .then(r => r.json())
          .then(d => {
            if (d.success) {
              showToast('Comment deleted.', 'success');
              commentsController.load(commentsController.currentPage);
              loadStatsRow();
              if (modal) modal.classList.remove("active");
            } else {
              showToast(d.error || 'Delete failed.', 'error');
              if (btn) btn.disabled = false;
            }
          })
          .catch(() => { showToast('Delete failed.', 'error'); if (btn) btn.disabled = false; });
      }
    );
  }

  function flagComment(id, btn, modal) {
    if (btn) btn.disabled = true;
    fetch(`/admin/interactions/comments/${id}/flag`, { method: 'POST' })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          showToast('Comment flagged as spam.', 'success');
          commentsController.load(commentsController.currentPage);
          if (modal) modal.classList.remove("active");
        } else {
          showToast(d.error || 'Flag failed.', 'error');
          if (btn) btn.disabled = false;
        }
      })
      .catch(() => { showToast('Flag failed.', 'error'); if (btn) btn.disabled = false; });
  }

  // ── Inspect Modal (server-rendered body) ──────────────────────
  function openCommentInspect(commentId) {
    const modal   = document.getElementById("inspect-comment-modal");
    const body    = document.getElementById("inspect-comment-modal-body");
    const titleEl = document.getElementById("inspect-comment-modal-title");
    if (!modal || !body) return;

    body.innerHTML = '<div class="dashboard-loading"><div class="spinner"></div><p>Loading…</p></div>';
    titleEl.textContent = "Inspect Comment";
    modal.classList.add("active");

    fetch(`/admin/interactions/comments/${commentId}/inspect`)
      .then(r => r.text())
      .then(html => { body.innerHTML = html; })
      .catch(() => { body.innerHTML = "<p class='text-muted'>Could not load comment.</p>"; });
  }

  function applyInteractionsUrlFilters() {
    if (typeof applyUrlFilters !== "function") return;
    const params = getUrlQueryParams();
    const activeTab = params.tab || 'comments';

    if (params.search !== undefined) {
      let searchInputId = 'comment-search';
      if (activeTab === 'reactions') searchInputId = 'reactions-search';
      else if (activeTab === 'views') searchInputId = 'views-search';
      else if (activeTab === 'clicks') searchInputId = 'clicks-search';
      else if (activeTab === 'saves') searchInputId = 'saves-search';
      const searchEl = document.getElementById(searchInputId);
      if (searchEl) searchEl.value = params.search;
    }

    applyUrlFilters({
      sentiment: "filter-comment-sentiment",
      target_type: "filter-comment-target",
      reactions_type: "filter-reaction-type",
      reactions_user: "filter-reactions-user",
      views_start_date: "filter-views-start-date",
      views_end_date: "filter-views-end-date",
      clicks_destination: "filter-clicks-destination",
      saves_user: "filter-saves-user"
    });
  }

  // ── Init ─────────────────────────────────
  function init() {
    commentsController = new AdminListController({
      domain: 'comments',
      endpoint: '/admin/interactions/comments',
      rowsEndpoint: '/admin/interactions/comments/rows',   // ← HTML partial mode
      tbodyId: 'comments-table-body',
      searchId: 'comment-search',
      filterIds: ['filter-comment-sentiment', 'filter-comment-target'],
      perPageId: 'comments-per-page',
      prevBtnId: 'comments-prev-btn',
      nextBtnId: 'comments-next-btn',
      indicatorId: 'comments-page-indicator',
      infoId: 'comments-pagination-info',
      countId: 'comments-count',
      clearBtnId: 'clear-comment-filters-btn',
      defaultPerPage: 25,
      colspan: 6,
      autoInit: false
    });

    reactionsController = new AdminListController({
      domain: 'reactions',
      endpoint: '/admin/interactions/reactions',
      rowsEndpoint: '/admin/interactions/reactions/rows',  // ← HTML partial mode
      tbodyId: 'reactions-table-body',
      searchId: 'reactions-search',
      filterIds: ['filter-reaction-type', 'filter-reactions-user'],
      perPageId: 'reactions-per-page',
      prevBtnId: 'reactions-prev-btn',
      nextBtnId: 'reactions-next-btn',
      indicatorId: 'reactions-page-indicator',
      infoId: 'reactions-pagination-info',
      countId: 'reactions-count',
      clearBtnId: 'clear-reactions-filters-btn',
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });

    viewsController = new AdminListController({
      domain: 'views',
      endpoint: '/admin/interactions/views',
      rowsEndpoint: '/admin/interactions/views/rows',     // ← HTML partial mode
      tbodyId: 'views-table-body',
      searchId: 'views-search',
      filterIds: ['filter-views-start-date', 'filter-views-end-date'],
      perPageId: 'views-per-page',
      prevBtnId: 'views-prev-btn',
      nextBtnId: 'views-next-btn',
      indicatorId: 'views-page-indicator',
      infoId: 'views-pagination-info',
      countId: 'views-count',
      clearBtnId: 'clear-views-filters-btn',
      defaultPerPage: 25,
      colspan: 4,
      autoInit: false
    });

    clicksController = new AdminListController({
      domain: 'clicks',
      endpoint: '/admin/interactions/clicks',
      rowsEndpoint: '/admin/interactions/clicks/rows',    // ← HTML partial mode
      tbodyId: 'clicks-table-body',
      searchId: 'clicks-search',
      filterIds: ['filter-clicks-destination'],
      perPageId: 'clicks-per-page',
      prevBtnId: 'clicks-prev-btn',
      nextBtnId: 'clicks-next-btn',
      indicatorId: 'clicks-page-indicator',
      infoId: 'clicks-pagination-info',
      countId: 'clicks-count',
      clearBtnId: 'clear-clicks-filters-btn',
      defaultPerPage: 25,
      colspan: 4,
      autoInit: false
    });

    savesController = new AdminListController({
      domain: 'saves',
      endpoint: '/admin/interactions/saves',
      rowsEndpoint: '/admin/interactions/saves/rows',     // ← HTML partial mode
      tbodyId: 'saves-table-body',
      searchId: 'saves-search',
      filterIds: ['filter-saves-user'],
      perPageId: 'saves-per-page',
      prevBtnId: 'saves-prev-btn',
      nextBtnId: 'saves-next-btn',
      indicatorId: 'saves-page-indicator',
      infoId: 'saves-pagination-info',
      countId: 'saves-count',
      clearBtnId: 'clear-saves-filters-btn',
      defaultPerPage: 25,
      colspan: 4,
      autoInit: false
    });

    initTabs();
    loadStatsRow();
    loadInteractionBreakdown();
    applyInteractionsUrlFilters();

    commentsController.bindEvents();
    reactionsController.bindEvents();
    viewsController.bindEvents();
    clicksController.bindEvents();
    savesController.bindEvents();

    const params = typeof getUrlQueryParams === "function" ? getUrlQueryParams() : {};
    const activeTab = params.tab || 'comments';
    switchTab(activeTab);

    // Comments table: inspect click delegation
    document.getElementById('comments-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'inspect-comment') {
        openCommentInspect(parseInt(btn.dataset.id || btn.dataset.commentId, 10));
      }
    });

    // Comment inspect modal: action delegation (rendered by _inspect.html)
    const commentModal = document.getElementById("inspect-comment-modal");
    if (commentModal) {
      commentModal.addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const id = parseInt(btn.dataset.id, 10);
        if (btn.dataset.action === 'flag-comment') {
          flagComment(id, btn, commentModal);
        } else if (btn.classList.contains('inspect-delete-btn')) {
          deleteComment(id, btn, commentModal);
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
