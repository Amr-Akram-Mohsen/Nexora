// ==============================
// ADMIN — INTERACTIONS / MODERATION
// Refactored: HTML partial mode — no renderRow, no JS HTML building
// ==============================

(function () {
  'use strict';

  window.commentsController = null;
  window.reactionsController = null;
  window.viewsController = null;
  window.clicksController = null;
  window.savesController = null;

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
      window.reactionsController.load(1);
    } else if (btn.dataset.tab === 'comments') {
      window.commentsController.load(1);
    } else if (btn.dataset.tab === 'views') {
      window.viewsController.load(1);
    } else if (btn.dataset.tab === 'clicks') {
      window.clicksController.load(1);
    } else if (btn.dataset.tab === 'saves') {
      window.savesController.load(1);
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
              window.commentsController.load(window.commentsController.currentPage);
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
          window.commentsController.load(window.commentsController.currentPage);
          if (modal) modal.classList.remove("active");
        } else {
          showToast(d.error || 'Flag failed.', 'error');
          if (btn) btn.disabled = false;
        }
      })
      .catch(() => { showToast('Flag failed.', 'error'); if (btn) btn.disabled = false; });
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
    window.commentsController = new AdminListController({
      domain: 'comments',
      endpoint: '/admin/interactions/comments',
      rowsEndpoint: '/admin/interactions/comments/rows',
      filterIds: ['filter-comment-sentiment', 'filter-comment-target'],
      defaultPerPage: 25,
      colspan: 6,
      autoInit: false
    });

    window.reactionsController = new AdminListController({
      domain: 'reactions',
      endpoint: '/admin/interactions/reactions',
      rowsEndpoint: '/admin/interactions/reactions/rows',
      filterIds: ['filter-reaction-type', 'filter-reactions-user'],
      defaultPerPage: 25,
      colspan: 6,
      autoInit: false
    });

    window.viewsController = new AdminListController({
      domain: 'views',
      endpoint: '/admin/interactions/views',
      rowsEndpoint: '/admin/interactions/views/rows',
      filterIds: ['filter-views-start-date', 'filter-views-end-date'],
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });

    window.clicksController = new AdminListController({
      domain: 'clicks',
      endpoint: '/admin/interactions/clicks',
      rowsEndpoint: '/admin/interactions/clicks/rows',
      filterIds: ['filter-clicks-destination'],
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });

    window.savesController = new AdminListController({
      domain: 'saves',
      endpoint: '/admin/interactions/saves',
      rowsEndpoint: '/admin/interactions/saves/rows',
      filterIds: ['filter-saves-user'],
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });

    initTabs();
    loadStatsRow();
    loadInteractionBreakdown();
    applyInteractionsUrlFilters();

    window.commentsController.bindEvents();
    window.reactionsController.bindEvents();
    window.viewsController.bindEvents();
    window.clicksController.bindEvents();
    window.savesController.bindEvents();

    const params = typeof getUrlQueryParams === "function" ? getUrlQueryParams() : {};
    const activeTab = params.tab || 'comments';
    switchTab(activeTab);


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
