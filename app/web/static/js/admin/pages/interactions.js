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
    } else if (btn.dataset.tab === 'shares') {
      window.sharesController.load(1);
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
          { icon: '📤', label: 'Shares',   value: data.shares   },
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

  // ── Analytics Overview ──────────────────
  let engagementChart, sentimentChart, countryChart, reactionChart, heatmapChart;

  function loadAnalyticsOverview() {
    fetch('/admin/interactions/analytics')
      .then(r => r.json())
      .then(data => {
        renderTopSaves(data.top_saves);
        const ctrBadge = document.getElementById('recs-ctr-badge');
        if(ctrBadge) ctrBadge.innerHTML = `Recommendations CTR: <b>${data.recs_kpi.ctr}%</b>`;
        
        updateStatsDeltas(data.deltas);
        
        const modPanel = document.getElementById('moderation-stats-panel');
        if (modPanel) {
            modPanel.style.display = '';
            document.getElementById('mod-daily-new').textContent = data.moderation_workload.daily_new;
            document.getElementById('mod-daily-flagged').textContent = data.moderation_workload.daily_flagged;
            document.getElementById('mod-pending-triage').textContent = data.moderation_workload.pending_triage;
        }

        drawEngagementChart(data.trends, data.spam_trend);
        drawSentimentChart(data.sentiment_dist);
        drawCountryChart(data.country_dist);
        drawReactionChart(data.reaction_targets);
        drawHeatmapChart(data.heatmap);
      })
      .catch(err => console.error("Failed to load analytics", err));
  }

  function updateStatsDeltas(deltas) {
    const cards = document.querySelectorAll('.dashboard-stat-card');
    cards.forEach(card => {
      const label = card.querySelector('.dashboard-stat-label').textContent.toLowerCase();
      let key = label;
      if (label === 'likes' || label === 'dislikes') return; // no delta for these specifically
      if (label === 'item clicks') key = 'clicks';
      
      const d = deltas[key];
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

  function renderTopSaves(saves) {
    const container = document.getElementById('top-saves-container');
    if (!container) return;
    if (!saves || !saves.length) {
      container.innerHTML = '<p class="text-muted">No saves recorded.</p>';
      return;
    }
    let html = '<ul class="divide-y divide-[var(--border-color)]">';
    saves.forEach(s => {
      const icon = s.target_type === 'content' ? '📄' : '📦';
      html += `<li class="py-2 flex justify-between">
        <span class="truncate pr-4">${icon} ${s.name}</span>
        <span class="font-semibold text-[var(--accent-color)]">${s.count}</span>
      </li>`;
    });
    html += '</ul>';
    container.innerHTML = html;
  }

  const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#888' } } },
    scales: {
      x: { ticks: { color: '#888' }, grid: { color: 'rgba(128,128,128,0.1)' } },
      y: { ticks: { color: '#888' }, grid: { color: 'rgba(128,128,128,0.1)' }, beginAtZero: true }
    }
  };

  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'right', labels: { color: '#888' } } }
  };

  function getSortedDates(trendsObj) {
    const allDates = new Set();
    Object.values(trendsObj).forEach(typeData => Object.keys(typeData).forEach(d => allDates.add(d)));
    return Array.from(allDates).sort();
  }

  function drawEngagementChart(trends, spamTrend) {
    const ctx = document.getElementById('engagementTrendChart');
    if (!ctx) return;
    if (engagementChart) engagementChart.destroy();
    
    const dates = getSortedDates(trends);
    const datasets = [
      { label: 'Comments', data: dates.map(d => trends.comments[d] || 0), borderColor: '#4CAF50', tension: 0.4 },
      { label: 'Reactions', data: dates.map(d => trends.reactions[d] || 0), borderColor: '#2196F3', tension: 0.4 },
      { label: 'Views', data: dates.map(d => trends.views[d] || 0), borderColor: '#9C27B0', tension: 0.4 },
      { label: 'Spam', data: dates.map(d => spamTrend[d] || 0), borderColor: '#F44336', borderDash: [5, 5], tension: 0.4 },
    ];
    
    engagementChart = new Chart(ctx, {
      type: 'line',
      data: { labels: dates, datasets },
      options: { ...defaultChartOptions, plugins: { title: { display: true, text: '30-Day Engagement & Spam', color: '#ccc' } } }
    });
  }

  function drawSentimentChart(sentimentDist) {
    const ctx = document.getElementById('sentimentSpamChart');
    if (!ctx) return;
    if (sentimentChart) sentimentChart.destroy();
    
    const labels = Object.keys(sentimentDist);
    const data = Object.values(sentimentDist);
    const colors = labels.map(l => l === 'positive' ? '#4CAF50' : l === 'negative' ? '#F44336' : l === 'spam' ? '#FF9800' : '#9E9E9E');

    sentimentChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{ data, backgroundColor: colors }]
      },
      options: { ...pieChartOptions, plugins: { ...pieChartOptions.plugins, title: { display: true, text: 'Comment Sentiment', color: '#ccc' } } }
    });
  }

  function drawCountryChart(countryDist) {
    const ctx = document.getElementById('countryDistChart');
    if (!ctx) return;
    if (countryChart) countryChart.destroy();

    const labels = Object.keys(countryDist);
    const data = Object.values(countryDist);

    countryChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: 'Clicks', data, backgroundColor: '#3F51B5' }]
      },
      options: { ...defaultChartOptions, plugins: { ...defaultChartOptions.plugins, title: { display: true, text: 'Top Click Countries', color: '#ccc' } } }
    });
  }

  function drawReactionChart(reactionTargets) {
    const ctx = document.getElementById('reactionTargetChart');
    if (!ctx) return;
    if (reactionChart) reactionChart.destroy();

    const labels = Object.keys(reactionTargets);
    const data = Object.values(reactionTargets);

    reactionChart = new Chart(ctx, {
      type: 'pie',
      data: {
        labels,
        datasets: [{ data, backgroundColor: ['#00BCD4', '#E91E63', '#FFC107'] }]
      },
      options: { ...pieChartOptions, plugins: { ...pieChartOptions.plugins, title: { display: true, text: 'Reactions by Target Type', color: '#ccc' } } }
    });
  }

  function drawHeatmapChart(heatmapData) {
    const ctx = document.getElementById('hourlyHeatmapChart');
    if (!ctx) return;
    if (heatmapChart) heatmapChart.destroy();

    const labels = Array.from({length: 24}, (_, i) => `${i}:00`);

    heatmapChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
            label: 'Total Engagement',
            data: heatmapData,
            backgroundColor: 'rgba(255, 152, 0, 0.6)',
            borderColor: '#FF9800',
            borderWidth: 1
        }]
      },
      options: { 
          ...defaultChartOptions, 
          plugins: { ...defaultChartOptions.plugins, title: { display: true, text: 'Most Engaged Hour of Day (Last 30 Days)', color: '#ccc' } } 
      }
    });
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
    loadStatsRow();
    loadInteractionBreakdown();
    setTimeout(loadAnalyticsOverview, 500); // load after stats
    applyInteractionsUrlFilters();

    window.commentsController.bindEvents();
    window.reactionsController.bindEvents();
    window.viewsController.bindEvents();
    window.clicksController.bindEvents();
    window.savesController.bindEvents();
    window.sharesController.bindEvents();

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
