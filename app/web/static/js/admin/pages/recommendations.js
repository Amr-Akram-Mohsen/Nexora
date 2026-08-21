// ADMIN — RECOMMENDATIONS
// Refactored: HTML partial mode — no renderRow, no JS HTML building

(function () {
  'use strict';

  let recController = null;

  function loadStats() {
    fetch('/admin/recommendations/stats')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('rec-stats-row');
        container.className = 'dashboard-stats-grid';
        container.innerHTML = '';

        const template = document.getElementById('rec-stat-card-template');
        const stats = [
          { icon: '🔗', label: 'Total Matches', value: data.total_matches },
          { icon: '📰', label: 'Linked Contents', value: data.linked_contents },
          { icon: '🛍️', label: 'Linked Products', value: data.linked_items },
          { icon: '👁️', label: 'Total Impressions', value: data.total_impressions },
          { icon: '🖱️', label: 'Total Clicks', value: data.total_clicks },
          { icon: '📈', label: 'Overall CTR', value: data.overall_ctr + '%' },
        ];

        stats.forEach(c => {
          const clone = template.content.cloneNode(true);
          clone.querySelector('.dashboard-stat-icon').textContent = c.icon;
          clone.querySelector('.dashboard-stat-value').textContent = (c.value || 0).toLocaleString();
          clone.querySelector('.dashboard-stat-label').textContent = c.label;
          container.appendChild(clone);
        });
      })
      .catch(() => {
        document.getElementById('rec-stats-row').innerHTML =
          '<p class="hint grid-full-width">Could not load stats.</p>';
      });
  }

  function unlinkMatch(contentId, itemId, btn, modal) {
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
              if (recController) {
                recController.load(recController.currentPage);
              }
              loadStats();
              if (modal) modal.classList.remove("active");
            } else {
              showToast(d.error || 'Unlink failed.', 'error');
              if (btn) btn.disabled = false;
            }
          })
          .catch(() => { showToast('Unlink failed.', 'error'); if (btn) btn.disabled = false; });
      }
    );
  }

  function loadContextPerformance() {
    if (typeof fetchAndInjectHtml === 'function') {
      fetchAndInjectHtml('/admin/recommendations/context-performance?format=html', 'context-performance-tbody', 'Loading data...', 5);
    }
  }

  function loadEntityPerformance() {
    if (typeof fetchAndInjectHtml === 'function') {
      fetchAndInjectHtml('/admin/recommendations/entity-performance?format=html', 'entity-performance-tbody', 'Loading data...', 3);
    }
  }

  function loadSystemHealth() {
    fetch('/admin/recommendations/health')
      .then(r => r.json())
      .then(d => {
        const container = document.getElementById('recommendation-health-container');
        const list = document.getElementById('health-signals-list');
        const iconContainer = document.querySelector('.alert-icon');
        const banner = document.querySelector('.alert-banner');

        if (!container || !list) return;

        list.replaceChildren();
        d.signals.forEach(s => {
          let iconStr = 'ℹ️';
          let cls = 'text-muted';
          if (s.level === 'critical') { iconStr = '🚨'; cls = 'text-danger font-bold'; }
          else if (s.level === 'warning') { iconStr = '⚠️'; cls = 'text-warning font-bold'; }
          else if (s.level === 'success') { iconStr = '✅'; cls = 'text-success'; }

          const div = document.createElement('div');
          div.className = cls;

          const iconSpan = document.createElement('span');
          iconSpan.className = 'mr-1';
          iconSpan.textContent = iconStr;

          div.appendChild(iconSpan);
          div.appendChild(document.createTextNode(` ${s.message}`));

          list.appendChild(div);
        });

        iconContainer.replaceChildren();
        const mainIconSpan = document.createElement('span');

        banner.classList.remove('alert-danger', 'alert-warning', 'alert-success');
        if (d.status === 'critical') {
          banner.classList.add('alert-danger');
          mainIconSpan.textContent = '🚨';
        } else if (d.status === 'warning') {
          banner.classList.add('alert-warning');
          mainIconSpan.textContent = '⚠️';
        } else {
          banner.classList.add('alert-success');
          mainIconSpan.textContent = '✅';
        }
        iconContainer.appendChild(mainIconSpan);
      })
      .catch(() => {
        const list = document.getElementById('health-signals-list');
        if (list) {
          list.replaceChildren();
          const errDiv = document.createElement('div');
          errDiv.className = 'text-muted';
          errDiv.textContent = 'Failed to load health status.';
          list.appendChild(errDiv);
        }
      });
  }

  function loadTrendChart() {
    const ctx = document.getElementById('recTrendChart');
    if (!ctx) return;

    fetch('/admin/recommendations/trend')
      .then(r => r.json())
      .then(data => {
        new Chart(ctx, {
          type: 'line',
          data: {
            labels: data.labels,
            datasets: [
              {
                label: 'Impressions',
                data: data.impressions,
                borderColor: 'var(--primary-color)',
                backgroundColor: 'rgba(var(--primary-color-rgb), 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
              },
              {
                label: 'Clicks',
                data: data.clicks,
                borderColor: 'var(--success-color)',
                backgroundColor: 'rgba(var(--success-color-rgb), 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
              mode: 'index',
              intersect: false,
            },
            plugins: {
              legend: { position: 'top' }
            },
            scales: {
              y: { beginAtZero: true }
            }
          }
        });
      })
      .catch(() => {
        renderErrorState(ctx.parentElement, "Failed to load chart data.");
      });
  }

  function loadSlotChart() {
    const ctx = document.getElementById('recSlotChart');
    if (!ctx) return;

    fetch('/admin/recommendations/slot-analysis')
      .then(r => r.json())
      .then(data => {
        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: data.labels,
            datasets: [
              {
                label: 'Clicks per Slot',
                data: data.data,
                backgroundColor: 'rgba(var(--primary-color-rgb), 0.7)',
                borderColor: 'var(--primary-color)',
                borderWidth: 1,
                borderRadius: 4
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false }
            },
            scales: {
              y: { beginAtZero: true, title: { display: true, text: 'Clicks' } },
              x: { title: { display: true, text: 'Position in Widget' } }
            }
          }
        });
      })
      .catch(() => {
        renderErrorState(ctx.parentElement, "Failed to load slot data.");
      });
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadContextPerformance();
    loadEntityPerformance();
    loadSystemHealth();
    loadTrendChart();
    loadSlotChart();

    recController = new AdminListController({
      domain: 'rec',
      endpoint: '/admin/recommendations/matches',
      rowsEndpoint: '/admin/recommendations/matches/rows',
      defaultPerPage: 25,
      colspan: 7,
      autoInit: false
    });
    recController.init();

    // Inspect modal: unlink action delegation (rendered by _inspect.html)
    const modal = document.getElementById("inspect-rec-modal");
    if (modal) {
      modal.addEventListener('click', e => {
        const btn = e.target.closest("[data-action='unlink-match']");
        if (!btn) return;
        const cid = parseInt(btn.dataset.contentId, 10);
        const iid = parseInt(btn.dataset.itemId, 10);
        unlinkMatch(cid, iid, btn, modal);
      });
    }
  });
})();
