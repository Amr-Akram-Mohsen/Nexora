// ==============================
// ADMIN — INTERACTIONS / MODERATION
// interactions.js
// ==============================

(function () {
  'use strict';

  let commentsController;
  let reactionsController;
  let viewsController;
  let clicksController;
  let savesController;

  let loadedComments = [];

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
          { icon: '💬', label: 'Comments',  value: data.comments },
          { icon: '👍', label: 'Likes',     value: data.likes },
          { icon: '👎', label: 'Dislikes',  value: data.dislikes },
          { icon: '👁️', label: 'Views',     value: data.views },
          { icon: '🔖', label: 'Saves',     value: data.saves },
          { icon: '🛒', label: 'Clicks',    value: data.item_clicks },
        ];

        cards.forEach(c => {
          const clone = template.content.cloneNode(true);
          clone.querySelector('.dashboard-stat-icon').textContent = c.icon;
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
    if (typeof renderInteractionBreakdown === 'function') {
      renderInteractionBreakdown('moderation-interactions-breakdown');
    }
  }

  // ── COMMENTS RENDER ──────────────────────
  function renderCommentRow(c) {
    const template = document.getElementById('comments-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    const previewEl = clone.querySelector('.comment-cell-preview');
    previewEl.textContent = c.preview;
    previewEl.title = c.content;

    const replyEl = clone.querySelector('.comment-cell-reply');
    if (!c.parent_id) {
      replyEl.remove();
    }

    clone.querySelector('.comment-cell-username').textContent = c.user_name;
    clone.querySelector('.comment-cell-userid').textContent = `#${c.user_id}`;
    clone.querySelector('.comment-cell-target').textContent = c.target_title;

    const targetTypeEl = clone.querySelector('.comment-cell-targettype');
    targetTypeEl.textContent = c.target_type;
    targetTypeEl.classList.add(c.target_type === 'content' ? 'badge-blue' : 'badge-purple');

    const sentimentEl = clone.querySelector('.comment-cell-sentiment');
    sentimentEl.textContent = c.sentiment;
    const sentimentClass = { positive: 'active', negative: 'inactive', neutral: 'user', spam: 'admin' };
    sentimentEl.classList.add(sentimentClass[c.sentiment] || 'user');

    clone.querySelector('.comment-cell-date').textContent = formatDate(c.created_at);

    // Buttons dataset
    const inspectBtn = clone.querySelector('.inspect-btn');
    inspectBtn.dataset.commentId = c.id;

    return tr;
  }

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

  function showInspectModal(comment) {
    const modal = document.getElementById("inspect-comment-modal");
    const body = document.getElementById("inspect-comment-modal-body");
    const titleEl = document.getElementById("inspect-comment-modal-title");

    titleEl.textContent = `Inspect Comment`;

    const template = document.getElementById("comment-inspect-template");
    const clone = template.content.cloneNode(true);

    clone.querySelector(".inspect-id").textContent = `#${comment.id}`;
    clone.querySelector(".inspect-username").textContent = comment.user_name || "—";
    clone.querySelector(".inspect-useremail").textContent = comment.user_email || "—";
    clone.querySelector(".inspect-userid").textContent = comment.user_id || "—";
    clone.querySelector(".inspect-target-title").textContent = comment.target_title || "—";

    const targetTypeBadge = clone.querySelector(".inspect-target-type");
    targetTypeBadge.textContent = comment.target_type;
    targetTypeBadge.className = `inspect-target-type status-badge ${comment.target_type === 'content' ? 'badge-blue' : 'badge-purple'}`;

    clone.querySelector(".inspect-date").textContent = formatDate(comment.created_at);

    const sentimentBadge = clone.querySelector(".inspect-sentiment");
    sentimentBadge.textContent = comment.sentiment;
    const sentimentClass = { positive: 'active', negative: 'inactive', neutral: 'user', spam: 'admin' };
    sentimentBadge.className = `inspect-sentiment status-badge ${sentimentClass[comment.sentiment] || 'user'}`;

    // Comment text
    clone.querySelector(".inspect-comment-body-text").textContent = comment.content;

    // Bind action buttons inside inspect modal
    const flagBtn = clone.querySelector(".inspect-flag-btn");
    if (flagBtn) {
      if (comment.sentiment === 'spam') {
        flagBtn.disabled = true;
        flagBtn.textContent = 'Already Flagged';
      } else {
        flagBtn.addEventListener("click", () => {
          flagComment(comment.id, flagBtn, modal);
        });
      }
    }

    const deleteBtn = clone.querySelector(".inspect-delete-btn");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", () => {
        deleteComment(comment.id, deleteBtn, modal);
      });
    }

    body.innerHTML = "";
    body.appendChild(clone);
    modal.classList.add("active");
  }

  // ── REACTIONS RENDER ─────────────────────
  function renderReactionRow(r) {
    const template = document.getElementById('reactions-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.reaction-cell-id').textContent = `#${r.id}`;
    clone.querySelector('.reaction-cell-target').textContent = r.target_title;
    
    const targetTypeEl = clone.querySelector('.reaction-cell-targettype');
    targetTypeEl.textContent = r.target_type;
    targetTypeEl.classList.add(r.target_type === 'content' ? 'badge-blue' : r.target_type === 'item' ? 'badge-purple' : 'badge-green');

    const typeEl = clone.querySelector('.reaction-cell-type');
    typeEl.textContent = r.type;
    typeEl.classList.add(r.type === 'like' ? 'active' : 'inactive');

    clone.querySelector('.reaction-cell-username').textContent = r.user_name;
    clone.querySelector('.reaction-cell-useremail').textContent = r.user_email ? `#${r.user_id} • ${r.user_email}` : `#${r.user_id}`;
    clone.querySelector('.reaction-cell-date').textContent = formatDate(r.created_at);

    return tr;
  }

  function renderViewRow(v) {
    const template = document.getElementById('views-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.views-cell-target').textContent = v.target_title;
    
    const typeEl = clone.querySelector('.views-cell-targettype');
    typeEl.textContent = v.target_type;
    typeEl.classList.add(v.target_type === 'content' ? 'badge-blue' : 'badge-purple');

    clone.querySelector('.views-cell-count').textContent = v.view_count.toLocaleString();
    clone.querySelector('.views-cell-date').textContent = formatDate(v.created_at);

    return tr;
  }

  // Clicks and Saves use manual compound queries, so we display their counts
  function renderClickRow(c) {
    const template = document.getElementById('clicks-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.clicks-cell-item').textContent = c.item_name;
    
    const destEl = clone.querySelector('.clicks-cell-destination');
    destEl.textContent = c.store_name;
    destEl.href = c.affiliate_url;

    clone.querySelector('.clicks-cell-count').textContent = c.click_count.toLocaleString();
    clone.querySelector('.clicks-cell-date').textContent = formatDate(c.created_at);

    return tr;
  }

  function renderSaveRow(s) {
    const template = document.getElementById('saves-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.saves-cell-target').textContent = s.target_title;
    
    const typeEl = clone.querySelector('.saves-cell-targettype');
    typeEl.textContent = s.target_type;
    typeEl.classList.add(s.target_type === 'content' ? 'badge-blue' : 'badge-purple');

    clone.querySelector('.saves-cell-username').textContent = s.user_name;
    clone.querySelector('.saves-cell-useremail').textContent = s.user_email ? `#${s.user_id} • ${s.user_email}` : `#${s.user_id}`;
    clone.querySelector('.saves-cell-date').textContent = formatDate(s.created_at);

    return tr;
  }

  function applyUrlFilters() {
    if (typeof getUrlQueryParams !== "function") return;
    const params = getUrlQueryParams();
    
    const activeTab = params.tab || 'comments';
    
    const filterMap = {
      sentiment: "filter-comment-sentiment",
      target_type: "filter-comment-target",
      reactions_type: "filter-reaction-type",
      reactions_user: "filter-reactions-user",
      views_start_date: "filter-views-start-date",
      views_end_date: "filter-views-end-date",
      clicks_destination: "filter-clicks-destination",
      saves_user: "filter-saves-user"
    };

    // Map generic 'search' query param to active tab search input
    if (params.search !== undefined) {
      let searchInputId = 'comment-search';
      if (activeTab === 'reactions') searchInputId = 'reactions-search';
      else if (activeTab === 'views') searchInputId = 'views-search';
      else if (activeTab === 'clicks') searchInputId = 'clicks-search';
      else if (activeTab === 'saves') searchInputId = 'saves-search';
      
      const searchEl = document.getElementById(searchInputId);
      if (searchEl) {
        searchEl.value = params.search;
      }
    }

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
    commentsController = new AdminListController({
      domain: 'comments',
      endpoint: '/admin/interactions/comments',
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
      rowTemplateId: 'comments-row-template',
      defaultPerPage: 25,
      colspan: 6,
      itemsKey: 'items',
      renderRow: renderCommentRow,
      onLoaded: (data) => {
        loadedComments = data.items || [];
      },
      autoInit: false
    });

    reactionsController = new AdminListController({
      domain: 'reactions',
      endpoint: '/admin/interactions/reactions',
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
      rowTemplateId: 'reactions-row-template',
      defaultPerPage: 25,
      colspan: 5,
      itemsKey: 'items',
      renderRow: renderReactionRow,
      autoInit: false
    });

    viewsController = new AdminListController({
      domain: 'views',
      endpoint: '/admin/interactions/views',
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
      rowTemplateId: 'views-row-template',
      defaultPerPage: 25,
      colspan: 4,
      itemsKey: 'items',
      renderRow: renderViewRow,
      autoInit: false
    });

    clicksController = new AdminListController({
      domain: 'clicks',
      endpoint: '/admin/interactions/clicks',
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
      rowTemplateId: 'clicks-row-template',
      defaultPerPage: 25,
      colspan: 4,
      itemsKey: 'items',
      renderRow: renderClickRow,
      autoInit: false
    });

    savesController = new AdminListController({
      domain: 'saves',
      endpoint: '/admin/interactions/saves',
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
      rowTemplateId: 'saves-row-template',
      defaultPerPage: 25,
      colspan: 4,
      itemsKey: 'items',
      renderRow: renderSaveRow,
      autoInit: false
    });

    initTabs();
    loadStatsRow();
    applyUrlFilters();

    // Bind events for all controllers
    commentsController.bindEvents();
    reactionsController.bindEvents();
    viewsController.bindEvents();
    clicksController.bindEvents();
    savesController.bindEvents();

    const params = typeof getUrlQueryParams === "function" ? getUrlQueryParams() : {};
    const activeTab = params.tab || 'comments';
    switchTab(activeTab);

    // Comments table click delegation
    document.getElementById('comments-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'inspect-comment') {
        const commentId = parseInt(btn.dataset.commentId, 10);
        const comment = loadedComments.find(c => c.id === commentId);
        if (comment) {
          showInspectModal(comment);
        }
      }
    });

    // Close inspect comment modal overlay
    const inspectCloseBtn = document.getElementById("inspect-comment-close-btn");
    if (inspectCloseBtn) {
      inspectCloseBtn.addEventListener("click", () => {
        document.getElementById("inspect-comment-modal").classList.remove("active");
      });
    }

    const inspectModalOverlay = document.getElementById("inspect-comment-modal");
    if (inspectModalOverlay) {
      inspectModalOverlay.addEventListener("click", (e) => {
        if (e.target === inspectModalOverlay) {
          inspectModalOverlay.classList.remove("active");
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
