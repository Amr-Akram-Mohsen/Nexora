// ==============================
// ADMIN — STORES CONTROL PANEL
// stores.js
// ==============================

(function () {
  'use strict';

  // ── Fetch Dashboard Stats ────────────────
  function loadDashboardStats() {
    fetch('/admin/providers/stores/health_stats')
      .then(r => r.json())
      .then(data => {
        document.getElementById('stats-active-links').textContent = (data.active_links || 0).toLocaleString();
        document.getElementById('stats-total-links').textContent = `${(data.total_links || 0).toLocaleString()} total recorded links`;
        
        document.getElementById('stats-synced-today').textContent = (data.synced_today || 0).toLocaleString();
        document.getElementById('stats-synced-week').textContent = (data.synced_this_week || 0).toLocaleString();
        
        document.getElementById('stats-out-of-stock').textContent = (data.out_of_stock || 0).toLocaleString();
        document.getElementById('stats-never-synced').textContent = (data.never_synced || 0).toLocaleString();
        
        // Render Out of Stock Distribution
        const distContainer = document.getElementById('stats-oos-distribution');
        if (data.oos_by_store && data.oos_by_store.length > 0) {
            distContainer.innerHTML = '';
            
            // Define colors for visual variety
            const colors = ['var(--brand-red)', 'var(--brand-orange)', 'var(--brand-orange)', 'var(--brand-orange)', 'var(--brand-orange)'];
            
            // Find max for percentage calculation
            const maxCount = Math.max(...data.oos_by_store.map(s => s.count));
            
            data.oos_by_store.forEach((item, index) => {
                const pct = maxCount > 0 ? ((item.count / maxCount) * 100).toFixed(1) : 0;
                const color = colors[index % colors.length];
                
                const row = document.createElement('div');
                row.className = 'flex items-center w-full gap-3';
                row.innerHTML = `
                    <div class="overview-breakdown-icon" style="color: ${color};"><i class="fa-solid fa-store"></i></div>
                    <div class="overview-breakdown-label truncate" title="${item.name}">${item.name}</div>
                    <div class="overview-breakdown-bar-track">
                        <div class="overview-breakdown-bar" style="width: ${pct}%; background-color: ${color};"></div>
                    </div>
                    <div class="overview-breakdown-val">${item.count.toLocaleString()}</div>
                `;
                
                distContainer.appendChild(row);
            });
        } else {
            distContainer.innerHTML = '<div class="text-muted text-sm py-2">No out-of-stock issues detected.</div>';
        }
      })
      .catch(err => {
        console.error('Failed to load stores dashboard stats', err);
      });
  }

  function loadCoverageStats() {
    fetch('/admin/providers/stores/coverage_stats')
      .then(r => r.json())
      .then(data => {
        // Render Category Coverage
        const catContainer = document.getElementById('stats-category-coverage');
        if (data.category_coverage && data.category_coverage.length > 0) {
            catContainer.innerHTML = '';
            const maxCat = Math.max(...data.category_coverage.map(s => s.count));
            
            data.category_coverage.slice(0, 10).forEach((item, index) => {
                const pct = maxCat > 0 ? ((item.count / maxCat) * 100).toFixed(1) : 0;
                
                const row = document.createElement('div');
                row.className = 'flex items-center w-full gap-3';
                row.innerHTML = `
                    <div class="overview-breakdown-label truncate" title="${item.name}">${item.name}</div>
                    <div class="overview-breakdown-bar-track">
                        <div class="overview-breakdown-bar" style="width: ${pct}%; background-color: var(--brand-purple);"></div>
                    </div>
                    <div class="overview-breakdown-val">${item.count.toLocaleString()}</div>
                `;
                catContainer.appendChild(row);
            });
        } else {
            catContainer.innerHTML = '<div class="text-muted text-sm py-2">No category coverage data available.</div>';
        }
        
        // Render Commission Rates
        const commContainer = document.getElementById('stats-commission-rates');
        if (data.commission_rates && data.commission_rates.length > 0) {
            commContainer.innerHTML = '';
            const maxComm = Math.max(...data.commission_rates.map(s => s.avg_rate));
            
            data.commission_rates.slice(0, 10).forEach((item, index) => {
                const pct = maxComm > 0 ? ((item.avg_rate / maxComm) * 100).toFixed(1) : 0;
                
                const row = document.createElement('div');
                row.className = 'flex items-center w-full gap-3';
                row.innerHTML = `
                    <div class="overview-breakdown-label truncate" title="${item.name}">${item.name}</div>
                    <div class="overview-breakdown-bar-track">
                        <div class="overview-breakdown-bar" style="width: ${pct}%; background-color: var(--brand-teal);"></div>
                    </div>
                    <div class="overview-breakdown-val">${item.avg_rate.toFixed(1)}%</div>
                `;
                commContainer.appendChild(row);
            });
        } else {
            commContainer.innerHTML = '<div class="text-muted text-sm py-2">No commission rate data available.</div>';
        }
      })
      .catch(err => {
        console.error('Failed to load stores coverage stats', err);
      });
  }

  function init() {
    loadDashboardStats();
    loadCoverageStats();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
