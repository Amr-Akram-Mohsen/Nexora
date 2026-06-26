(function () {
  'use strict';

  document.addEventListener("DOMContentLoaded", () => {
    window.api.get('/admin/audience-analytics/stats')
      .then(data => {
        // 1. Text Metrics
        const receptivityCtr = document.getElementById('receptivity-ctr');
        if (receptivityCtr) receptivityCtr.textContent = data.receptivity_ctr + '%';
        
        const receptivityClicks = document.getElementById('receptivity-clicks');
        if (receptivityClicks) receptivityClicks.textContent = parseInt(data.recommendation_clicks).toLocaleString();
        
        const receptivityImpressions = document.getElementById('receptivity-impressions');
        if (receptivityImpressions) receptivityImpressions.textContent = parseInt(data.recommendation_impressions).toLocaleString();
        
        const churnRiskCount = document.getElementById('churn-risk-count');
        if (churnRiskCount) churnRiskCount.textContent = parseInt(data.churn_risk_count).toLocaleString();

        // 2. Power User Segmentation Chart
        if (document.getElementById('powerUserChart')) {
            window.nexoraCharts.render('powerUserChart', 'doughnut', {
              labels: Object.keys(data.power_user_segmentation),
              datasets: [{
                data: Object.values(data.power_user_segmentation),
                backgroundColor: ['#27AE60', '#EB5757']
              }]
            }, { plugins: { legend: { position: 'bottom' } } });
        }

        // 3. Retention Chart
        if (document.getElementById('retentionChart')) {
            window.nexoraCharts.render('retentionChart', 'line', {
              labels: Object.keys(data.retention_curve),
              datasets: [{
                label: '% Retained',
                data: Object.values(data.retention_curve),
                borderColor: '#9B51E0',
                backgroundColor: 'rgba(155, 81, 224, 0.1)',
                tension: 0.3,
                fill: true
              }]
            }, { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } });
        }
      });
  });
})();
