// ==============================
// ADMIN — RECOMMENDATIONS
// Refactored: HTML partial mode — no renderRow, no JS HTML building
// ==============================

(function () {
  'use strict';

  window.recController = null;

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
              window.recController.load(window.recController.currentPage);
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
    fetch('/admin/recommendations/context-performance')
      .then(r => r.json())
      .then(d => {
        const tbody = document.getElementById('context-performance-tbody');
        if (!d.data || d.data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No data available.</td></tr>';
          return;
        }
        tbody.innerHTML = d.data.map(r => `
          <tr>
            <td><span class="badge badge-secondary">${r.context_id}</span></td>
            <td><span class="status-badge badge-type-compact">${r.entity_type}</span></td>
            <td>${r.impressions}</td>
            <td>${r.clicks}</td>
            <td class="col-metric font-bold">${r.ctr}</td>
          </tr>
        `).join('');
      })
      .catch(() => {
        document.getElementById('context-performance-tbody').innerHTML = '<tr><td colspan="5" class="text-center text-muted">Failed to load data.</td></tr>';
      });
  }

  function loadEntityPerformance() {
    fetch('/admin/recommendations/entity-performance')
      .then(r => r.json())
      .then(d => {
        const tbody = document.getElementById('entity-performance-tbody');
        if (!d.data || d.data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No data available.</td></tr>';
          return;
        }
        tbody.innerHTML = d.data.map(r => `
          <tr>
            <td class="font-bold">${r.entity_name}</td>
            <td><span class="status-badge badge-type-compact">${r.entity_type}</span></td>
            <td class="col-metric">${r.clicks}</td>
          </tr>
        `).join('');
      })
      .catch(() => {
        document.getElementById('entity-performance-tbody').innerHTML = '<tr><td colspan="3" class="text-center text-muted">Failed to load data.</td></tr>';
      });
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

        list.innerHTML = d.signals.map(s => {
          let icon = 'ℹ️';
          let cls = 'text-muted';
          if (s.level === 'critical') { icon = '🚨'; cls = 'text-danger font-bold'; }
          else if (s.level === 'warning') { icon = '⚠️'; cls = 'text-warning font-bold'; }
          else if (s.level === 'success') { icon = '✅'; cls = 'text-success'; }
          return `<div class="${cls}"><span class="mr-1">${icon}</span> ${s.message}</div>`;
        }).join('');

        if (d.status === 'critical') {
          banner.classList.add('alert-danger');
          iconContainer.innerHTML = '<span>🚨</span>';
        } else if (d.status === 'warning') {
          banner.classList.add('alert-warning');
          iconContainer.innerHTML = '<span>⚠️</span>';
        } else {
          banner.classList.add('alert-success');
          iconContainer.innerHTML = '<span>✅</span>';
        }
      })
      .catch(() => {
        const list = document.getElementById('health-signals-list');
        if (list) list.innerHTML = '<div class="text-muted">Failed to load health status.</div>';
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
        ctx.parentElement.innerHTML = '<div class="text-center text-muted">Failed to load chart data.</div>';
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
        ctx.parentElement.innerHTML = '<div class="text-center text-muted">Failed to load slot data.</div>';
      });
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadContextPerformance();
    loadEntityPerformance();
    loadSystemHealth();
    loadTrendChart();
    loadSlotChart();

    window.recController = new AdminListController({
      domain: 'rec',
      endpoint: '/admin/recommendations/matches',
      rowsEndpoint: '/admin/recommendations/matches/rows',
      defaultPerPage: 25,
      colspan: 7,
      autoInit: false
    });
    window.recController.init();


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
