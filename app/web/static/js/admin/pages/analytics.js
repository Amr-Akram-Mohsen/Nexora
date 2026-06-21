(function () {
  'use strict';

  document.addEventListener("DOMContentLoaded", () => {
    fetch('/admin/audience-analytics/stats')
      .then(res => res.json())
      .then(data => {
        // 1. Text Metrics
        document.getElementById('receptivity-ctr').textContent = data.receptivity_ctr + '%';
        document.getElementById('receptivity-clicks').textContent = parseInt(data.recommendation_clicks).toLocaleString();
        document.getElementById('receptivity-impressions').textContent = parseInt(data.recommendation_impressions).toLocaleString();
        document.getElementById('churn-risk-count').textContent = parseInt(data.churn_risk_count).toLocaleString();

        if (typeof Chart === 'undefined') return;

        // 2. Power User Segmentation Chart
        new Chart(document.getElementById('powerUserChart'), {
          type: 'doughnut',
          data: {
            labels: Object.keys(data.power_user_segmentation),
            datasets: [{
              data: Object.values(data.power_user_segmentation),
              backgroundColor: ['#27AE60', '#EB5757']
            }]
          },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
        });

        // 3. Retention Chart
        new Chart(document.getElementById('retentionChart'), {
          type: 'line',
          data: {
            labels: Object.keys(data.retention_curve),
            datasets: [{
              label: '% Retained',
              data: Object.values(data.retention_curve),
              borderColor: '#9B51E0',
              backgroundColor: 'rgba(155, 81, 224, 0.1)',
              tension: 0.3,
              fill: true
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { min: 0, max: 100 } }
          }
        });
      });
  });
})();
