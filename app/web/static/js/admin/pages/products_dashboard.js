// items_dashboard.js
(function () {
    'use strict';
  
    function loadDashboard() {
      window.api.get('/admin/products/health_stats')
        .then(data => {
          const total = data.total_items || 0;
          
          // Render Product Type Distribution
          const distContainer = document.getElementById('stats-type-distribution');
          if (distContainer) {
              distContainer.innerHTML = data.product_type_distribution_html || '<div class="text-muted text-sm py-2">No type distribution data available.</div>';
          }
          
          // Render Top Engagement Items
          const engContainer = document.getElementById('stats-engagement-products');
          if (engContainer) {
              engContainer.innerHTML = data.top_engagement_items_html || '<div class="text-muted text-sm py-2 text-center">No engagement data available.</div>';
          }
        })
        .catch(err => {
          console.error('Failed to load dashboard stats', err);
        });
    }
  
    document.addEventListener('DOMContentLoaded', loadDashboard);
  })();
