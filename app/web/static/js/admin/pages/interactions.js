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
  window.sharesController = null;

  // ── Tab switching ───────────────────────
  function initTabs() {
    initAdminTabs('interactions-tabs', tabName => {
      if (tabName === 'reactions') window.reactionsController.load(1);
      else if (tabName === 'comments') window.commentsController.load(1);
      else if (tabName === 'views') window.viewsController.load(1);
      else if (tabName === 'clicks') window.clicksController.load(1);
      else if (tabName === 'saves') window.savesController.load(1);
      else if (tabName === 'shares') window.sharesController.load(1);
    });
  }

  // ── Stats Row ───────────────────────────
  function loadStatsRow() {
    return window.api.get('/admin/interactions/stats')
      .then(data => {
        const container = document.getElementById('interactions-stats-row');
        if (!container) return;
        container.replaceChildren();
        container.className = 'dashboard-stats-grid';

        const template = document.getElementById('interactions-stat-card-template');
        if (!template) return;
        
        const cards = [
          { key: 'comments', icon: '💬', label: 'Comments', value: data.comments },
          { key: 'likes', icon: '👍', label: 'Likes',    value: data.likes    },
          { key: 'dislikes', icon: '👎', label: 'Dislikes', value: data.dislikes },
          { key: 'views', icon: '👁️', label: 'Views',   value: data.views    },
          { key: 'saves', icon: '🔖', label: 'Saves',    value: data.saves    },
          { key: 'shares', icon: '📤', label: 'Shares',   value: data.shares   },
          { key: 'item_clicks', icon: '🛒', label: 'Clicks',   value: data.item_clicks },
        ];

        cards.forEach(c => {
          const clone = template.content.cloneNode(true);
          const cardEl = clone.querySelector('.dashboard-stat-card');
          if (cardEl) cardEl.dataset.statKey = c.key;
          clone.querySelector('.dashboard-stat-icon').textContent  = c.icon;
          clone.querySelector('.dashboard-stat-value').textContent = (c.value || 0).toLocaleString();
          clone.querySelector('.dashboard-stat-label').textContent = c.label;
          container.appendChild(clone);
        });
      })
      .catch(() => {
        const container = document.getElementById('interactions-stats-row');
        if (container) {
          container.replaceChildren();
          const p = document.createElement('p');
          p.className = 'hint grid-full-width';
          p.textContent = 'Could not load stats.';
          container.appendChild(p);
        }
      });
  }

  function loadInteractionBreakdown() {
    if (typeof fetchAndInjectHtml === 'function') {
      fetchAndInjectHtml('/admin/dashboard/widget/interactions-breakdown', 'moderation-interactions-breakdown', 'Loading breakdown...');
    }
  }

  // ── Analytics Overview ──────────────────
  let engagementChart, sentimentChart, countryChart, reactionChart, heatmapChart;

  function loadAnalyticsOverview() {
    window.api.get('/admin/interactions/analytics')
      .then(data => {
        renderTopSaves(data.top_saves_html);
        const ctrBadge = document.getElementById('recs-ctr-badge');
        if(ctrBadge) {
            ctrBadge.replaceChildren();
            const b = document.createElement('b');
            b.textContent = `${data.recs_kpi.ctr}%`;
            ctrBadge.appendChild(document.createTextNode('Recommendations CTR: '));
            ctrBadge.appendChild(b);
        }
        
        updateStatsDeltas(data.deltas);
        
        const modPanel = document.getElementById('moderation-stats-panel');
        if (modPanel) {
            modPanel.style.display = '';
            document.getElementById('mod-daily-new').textContent = data.moderation_workload.daily_new;
            document.getElementById('mod-daily-flagged').textContent = data.moderation_workload.daily_flagged;
            document.getElementById('mod-pending-triage').textContent = data.moderation_workload.pending_triage;
        }

        drawSentimentChart(data.sentiment_dist);
        drawReactionChart(data.reaction_targets);
      })
      .catch(err => console.error("Failed to load analytics", err));
  }

  function updateStatsDeltas(deltas) {
    const cards = document.querySelectorAll('.dashboard-stat-card');
    cards.forEach(card => {
      const key = card.dataset.statKey;
      if (!key || key === 'likes' || key === 'dislikes') return; // no delta for these specifically
      
      let lookupKey = key;
      if (key === 'item_clicks') lookupKey = 'clicks';
      
      const d = deltas[lookupKey];
      if (d) {
        const span = document.createElement('span');
        span.className = 'text-xs ml-2 font-medium';
        if (d.delta > 0) {
          span.classList.add('text-green');
          span.textContent = `↑ ${d.delta}%`;
        } else if (d.delta < 0) {
          span.classList.add('text-red');
          span.textContent = `↓ ${Math.abs(d.delta)}%`;
        } else {
          span.classList.add('text-muted');
          span.textContent = `— 0%`;
        }
        span.title = 'vs previous 7 days';
        const valEl = card.querySelector('.dashboard-stat-value');
        if (valEl && !valEl.nextElementSibling) valEl.after(span);
      }
    });
  }

  function renderTopSaves(html) {
    const container = document.getElementById('top-saves-container');
    if (!container) return;
    container.innerHTML = html;
  }



  function drawSentimentChart(sentimentDist) {
    const labels = Object.keys(sentimentDist);
    const data = Object.values(sentimentDist);
    const colors = labels.map(l => l === 'positive' ? '#4CAF50' : l === 'negative' ? '#F44336' : l === 'spam' ? '#FF9800' : '#9E9E9E');

    window.nexoraCharts.render('sentimentSpamChart', 'doughnut', 
      { labels, datasets: [{ data, backgroundColor: colors }] },
      { plugins: { legend: { position: 'right' }, title: { display: true, text: 'Comment Sentiment', color: '#ccc' } } }
    );
  }



  function drawReactionChart(reactionTargets) {
    const labels = Object.keys(reactionTargets);
    const data = Object.values(reactionTargets);

    window.nexoraCharts.render('reactionTargetChart', 'pie', 
      { labels, datasets: [{ data, backgroundColor: ['#00BCD4', '#E91E63', '#FFC107'] }] },
      { plugins: { legend: { position: 'right' }, title: { display: true, text: 'Reactions by Target Type', color: '#ccc' } } }
    );
  }



  // ── Comment Moderation Actions ───────────
  function deleteComment(id, btn, modal) {
    showModal(
      'Delete Comment',
      'Are you sure you want to permanently delete this comment and all its replies?',
      () => {
        if (btn) btn.disabled = true;
        window.api.delete(`/admin/interactions/comments/${id}`)
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
          .catch(() => { if (btn) btn.disabled = false; });
      }
    );
  }

  function flagComment(id, btn, modal) {
    if (btn) btn.disabled = true;
    window.api.post(`/admin/interactions/comments/${id}/flag`)
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
      .catch(() => { if (btn) btn.disabled = false; });
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
      comments_start_date: "filter-comments-start-date",
      comments_end_date: "filter-comments-end-date",
      reactions_type: "filter-reaction-type",
      reactions_user: "filter-reactions-user",
      views_start_date: "filter-views-start-date",
      views_end_date: "filter-views-end-date",
      clicks_destination: "filter-clicks-destination",
      saves_user: "filter-saves-user",
      shares_user: "filter-shares-user"
    });
  }

  // ── Init ─────────────────────────────────
  function init() {
    window.commentsController = new AdminListController({
      domain: 'comments',
      endpoint: '/admin/interactions/comments',
      rowsEndpoint: '/admin/interactions/comments/rows',
      filterIds: ['filter-comment-sentiment', 'filter-comment-target', 'filter-comments-start-date', 'filter-comments-end-date'],
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

    window.sharesController = new AdminListController({
      domain: 'shares',
      endpoint: '/admin/interactions/shares',
      rowsEndpoint: '/admin/interactions/shares/rows',
      filterIds: ['filter-shares-user'],
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });

    initTabs();
    loadStatsRow().then(loadAnalyticsOverview);
    loadInteractionBreakdown();
    applyInteractionsUrlFilters();

    window.commentsController.bindEvents();
    window.reactionsController.bindEvents();
    window.viewsController.bindEvents();
    window.clicksController.bindEvents();
    window.savesController.bindEvents();
    window.sharesController.bindEvents();

    const params = typeof getUrlQueryParams === "function" ? getUrlQueryParams() : {};
    const activeTab = params.tab || 'comments';
    const tabBtn = document.querySelector(`#interactions-tabs .admin-tab-btn[data-tab="${activeTab}"]`);
    if (tabBtn) {
      if (tabBtn.classList.contains("active")) {
        // Tab is already active visually, just load the data
        if (activeTab === 'reactions') window.reactionsController.load(1);
        else if (activeTab === 'comments') window.commentsController.load(1);
        else if (activeTab === 'views') window.viewsController.load(1);
        else if (activeTab === 'clicks') window.clicksController.load(1);
        else if (activeTab === 'saves') window.savesController.load(1);
        else if (activeTab === 'shares') window.sharesController.load(1);
      } else {
        // Tab is not active, simulate click to switch visuals and trigger load
        tabBtn.click();
      }
    }
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
