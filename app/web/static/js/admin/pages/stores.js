// ==============================
// ADMIN — STORES CONTROL PANEL
// stores.js
// ==============================

(function () {
  'use strict';

  let availabilityChart = null;
  let syncCadenceChart = null;
  let syncAgeChart = null;

  // ── Fetch Dashboard Stats ────────────────
  function loadDashboardStats() {
    fetch('/admin/providers/stores/health_stats')
      .then(r => r.json())
      .then(data => {
        document.getElementById('stats-active-links').textContent = (data.active_links || 0).toLocaleString();
        document.getElementById('stats-total-links').textContent = `${(data.total_links || 0).toLocaleString()} total recorded links`;
        
        document.getElementById('stats-synced-today').textContent = (data.synced_today || 0).toLocaleString();
        
        const statsChecked = document.getElementById('stats-checked-today');
        if (statsChecked) statsChecked.textContent = (data.checked_in_24h || 0).toLocaleString();
        
        const statsDeeplinks = document.getElementById('stats-deeplinks-fresh');
        if (statsDeeplinks) statsDeeplinks.textContent = (data.deeplink_refreshed_30d || 0).toLocaleString();
        
        const statsOos = document.getElementById('stats-out-of-stock');
        if (statsOos) statsOos.textContent = (data.out_of_stock || 0).toLocaleString();
        
        // Render Out of Stock Distribution
        const distContainer = document.getElementById('stats-oos-distribution');
        if (data.oos_by_store && data.oos_by_store.length > 0 && distContainer) {
            distContainer.innerHTML = '';
            const colors = ['var(--brand-red)', 'var(--brand-orange)', 'var(--brand-orange)', 'var(--brand-orange)', 'var(--brand-orange)'];
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
        } else if (distContainer) {
            distContainer.innerHTML = '<div class="text-muted text-sm py-2">No out-of-stock issues detected.</div>';
        }

        renderAvailabilityChart(data.availability_breakdown);
        renderSyncCadenceChart(data.sync_cadence);
        renderAvgSyncAgeChart(data.avg_sync_age_by_store);
        renderTopStaleStores(data.top_stale_stores);
      })
      .catch(err => {
        console.error('Failed to load stores dashboard stats', err);
      });
  }

  function renderAvailabilityChart(breakdown) {
    const ctx = document.getElementById('chart-availability');
    if (!ctx || !breakdown || typeof Chart === 'undefined') return;
    
    if (availabilityChart) availabilityChart.destroy();
    
    availabilityChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['InStock', 'OutOfStock', 'PreOrder', 'Unknown'],
        datasets: [{
          data: [
            breakdown.InStock || 0, 
            breakdown.OutOfStock || 0, 
            breakdown.PreOrder || 0, 
            breakdown.Unknown || 0
          ],
          backgroundColor: ['#10b981', '#f97316', '#3b82f6', '#9ca3af'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });
  }

  function renderSyncCadenceChart(cadenceData) {
    const ctx = document.getElementById('chart-sync-cadence');
    if (!ctx || !cadenceData || !cadenceData.length || typeof Chart === 'undefined') return;
    
    if (syncCadenceChart) syncCadenceChart.destroy();
    
    const labels = cadenceData.map(d => d.date);
    const dataPoints = cadenceData.map(d => d.count);
    
    syncCadenceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Sync Volume',
          data: dataPoints,
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, display: false },
          x: { display: false }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  function renderAvgSyncAgeChart(storeData) {
    const ctx = document.getElementById('chart-sync-age');
    if (!ctx || !storeData || !storeData.length || typeof Chart === 'undefined') return;
    
    if (syncAgeChart) syncAgeChart.destroy();
    
    const topData = storeData.slice(0, 10);
    const labels = topData.map(d => d.name);
    const dataPoints = topData.map(d => d.avg_age_days);
    
    syncAgeChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Avg Sync Age (Days)',
          data: dataPoints,
          backgroundColor: '#3b82f6',
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  function renderTopStaleStores(storeData) {
    const container = document.getElementById('list-stale-stores');
    if (!container) return;
    
    if (!storeData || !storeData.length) {
      container.innerHTML = '<li class="text-center w-full py-4 text-muted">No stale stores found.</li>';
      return;
    }
    
    container.innerHTML = '';
    storeData.slice(0, 5).forEach((store, index) => {
      const li = document.createElement('li');
      li.className = 'overview-top-item flex items-center justify-between py-2 border-b border-border last:border-0';
      li.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="overview-top-rank text-muted font-mono text-sm">#${index + 1}</div>
          <div class="overview-top-name truncate font-medium" title="${store.name}">${store.name}</div>
        </div>
        <div class="overview-top-value text-right whitespace-nowrap">
            <span class="badge" style="background: rgba(var(--brand-red-rgb), 0.1); color: var(--brand-red);">${store.avg_age_days} days</span>
        </div>
      `;
      container.appendChild(li);
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

  let trackingCoverageChart = null;
  let deeplinkFreshnessChart = null;
  let programDistributionChart = null;

  function loadAffiliateStats() {
    fetch('/admin/providers/stores/affiliate_stats')
      .then(r => r.json())
      .then(data => {
        const statsAvg = document.getElementById('stats-avg-commission');
        if (statsAvg) statsAvg.textContent = (data.avg_commission_rate || 0).toFixed(2) + '%';
        
        const statsWith = document.getElementById('stats-links-with-commission');
        if (statsWith) statsWith.textContent = (data.links_with_commission || 0).toLocaleString();
        
        const statsWithout = document.getElementById('stats-links-without-commission');
        if (statsWithout) statsWithout.textContent = (data.links_without_commission || 0).toLocaleString();
        
        const statsTop = document.getElementById('stats-top-program');
        if (statsTop) statsTop.textContent = data.top_program || 'None';
        
        // Commission Gap Alert
        const totalLinks = (data.links_with_commission || 0) + (data.links_without_commission || 0);
        if (totalLinks > 0) {
            const gapPct = ((data.links_without_commission || 0) / totalLinks) * 100;
            if (gapPct > 25) {
                const alertContainer = document.getElementById('commission-gap-alert-container');
                const alertText = document.getElementById('commission-gap-alert-text');
                if (alertContainer && alertText) {
                    alertText.textContent = `${gapPct.toFixed(1)}% of your tracked links are missing a commission rate. You are likely losing attribution on these products.`;
                    alertContainer.style.display = 'flex';
                }
            }
        }
        
        renderTrackingCoverageChart(data.tracking_coverage);
        renderDeeplinkFreshnessChart(data.deeplink_freshness);
        renderProgramDistributionChart(data.program_distribution);
        renderTopCommissionStores(data.commission_rate_ranking);
      })
      .catch(err => {
        console.error('Failed to load affiliate stats', err);
      });
  }

  function renderTrackingCoverageChart(coverage) {
    const ctx = document.getElementById('chart-tracking-coverage');
    if (!ctx || !coverage || typeof Chart === 'undefined') return;
    
    if (trackingCoverageChart) trackingCoverageChart.destroy();
    
    trackingCoverageChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(coverage),
        datasets: [{
          data: Object.values(coverage),
          backgroundColor: ['#10b981', '#f97316'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });
  }

  function renderDeeplinkFreshnessChart(freshness) {
    const ctx = document.getElementById('chart-deeplink-freshness');
    if (!ctx || !freshness || typeof Chart === 'undefined') return;
    
    if (deeplinkFreshnessChart) deeplinkFreshnessChart.destroy();
    
    deeplinkFreshnessChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(freshness),
        datasets: [{
          data: Object.values(freshness),
          backgroundColor: ['#10b981', '#3b82f6', '#f97316', '#ef4444'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });
  }

  function renderProgramDistributionChart(distribution) {
    const ctx = document.getElementById('chart-program-distribution');
    if (!ctx || !distribution || !distribution.length || typeof Chart === 'undefined') return;
    
    if (programDistributionChart) programDistributionChart.destroy();
    
    programDistributionChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: distribution.map(d => d.name),
        datasets: [{
          label: 'Number of Links',
          data: distribution.map(d => d.count),
          backgroundColor: '#8b5cf6',
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  function renderTopCommissionStores(storeData) {
    const container = document.getElementById('list-commission-stores');
    if (!container) return;
    
    if (!storeData || !storeData.length) {
      container.innerHTML = '<li class="text-center w-full py-4 text-muted">No commission data found.</li>';
      return;
    }
    
    container.innerHTML = '';
    storeData.slice(0, 5).forEach((store, index) => {
      const li = document.createElement('li');
      li.className = 'overview-top-item flex items-center justify-between py-2 border-b border-border last:border-0';
      li.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="overview-top-rank text-muted font-mono text-sm">#${index + 1}</div>
          <div class="overview-top-name truncate font-medium" title="${store.name}">${store.name}</div>
        </div>
        <div class="overview-top-value text-right whitespace-nowrap">
            <span class="badge" style="background: rgba(var(--brand-green-rgb), 0.1); color: var(--brand-green);">${store.avg_rate}%</span>
        </div>
      `;
      container.appendChild(li);
    });
  }

  let currencyMixChart = null;
  let priceStalenessChart = null;

  function loadPricingStats() {
    fetch('/admin/providers/stores/pricing_stats')
      .then(r => r.json())
      .then(data => {
        const statsNull = document.getElementById('stats-null-prices');
        if (statsNull) statsNull.textContent = (data.null_price_count || 0).toLocaleString();
        
        const statsStale = document.getElementById('stats-stale-prices');
        if (statsStale) statsStale.textContent = (data.stale_price_count || 0).toLocaleString();
        
        const statsDiscount = document.getElementById('stats-avg-discount');
        if (statsDiscount) statsDiscount.textContent = (data.avg_discount_percentage || 0).toFixed(1) + '%';
        
        // Alerts
        const alertsContainer = document.getElementById('pricing-alerts-container');
        const alertsList = document.getElementById('pricing-alerts-list');
        if (alertsContainer && alertsList) {
            alertsList.innerHTML = '';
            let showAlert = false;
            
            if (data.all_oos_items_count > 0) {
                showAlert = true;
                alertsList.innerHTML += `<div><strong>Complete OOS Detected:</strong> ${data.all_oos_items_count} items are entirely Out of Stock across all mapped stores.</div>`;
            }
            
            if (data.high_null_price_stores && data.high_null_price_stores.length > 0) {
                showAlert = true;
                data.high_null_price_stores.forEach(store => {
                    alertsList.innerHTML += `<div><strong>Missing Price Data:</strong> ${store.name} has a ${store.null_rate}% null-price rate. Sync may be broken.</div>`;
                });
            }
            
            if (showAlert) alertsContainer.style.display = 'block';
        }
        
        renderCurrencyMixChart(data.currency_mix);
        renderDiscountRanking(data.discount_depth_ranking);
        renderPriceStalenessChart(data.price_staleness_grid);
      })
      .catch(err => {
        console.error('Failed to load pricing stats', err);
      });
  }

  function renderCurrencyMixChart(currencyData) {
    const ctx = document.getElementById('chart-currency-mix');
    if (!ctx || !currencyData || typeof Chart === 'undefined') return;
    
    if (currencyMixChart) currencyMixChart.destroy();
    
    currencyMixChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(currencyData),
        datasets: [{
          data: Object.values(currencyData),
          backgroundColor: ['#3b82f6', '#10b981', '#f97316', '#8b5cf6', '#ef4444'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });
  }

  function renderDiscountRanking(storeData) {
    const container = document.getElementById('list-discount-stores');
    if (!container) return;
    
    if (!storeData || !storeData.length) {
      container.innerHTML = '<li class="text-center w-full py-4 text-muted">No discount data found.</li>';
      return;
    }
    
    container.innerHTML = '';
    storeData.slice(0, 5).forEach((store, index) => {
      const li = document.createElement('li');
      li.className = 'overview-top-item flex items-center justify-between py-2 border-b border-border last:border-0';
      li.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="overview-top-rank text-muted font-mono text-sm">#${index + 1}</div>
          <div class="overview-top-name truncate font-medium" title="${store.name}">${store.name}</div>
        </div>
        <div class="overview-top-value text-right whitespace-nowrap">
            <span class="badge" style="background: rgba(var(--brand-green-rgb), 0.1); color: var(--brand-green);">${store.avg_discount}% off</span>
        </div>
      `;
      container.appendChild(li);
    });
  }

  function renderPriceStalenessChart(gridData) {
    const ctx = document.getElementById('chart-price-staleness');
    if (!ctx || !gridData || !gridData.length || typeof Chart === 'undefined') return;
    
    if (priceStalenessChart) priceStalenessChart.destroy();
    
    const labels = gridData.map(d => d.name);
    const freshData = gridData.map(d => d.fresh);
    const staleData = gridData.map(d => d.stale);
    
    priceStalenessChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Fresh (< 7 days)',
            data: freshData,
            backgroundColor: '#10b981'
          },
          {
            label: 'Stale (> 7 days)',
            data: staleData,
            backgroundColor: '#f97316'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true },
          y: { stacked: true }
        },
        plugins: {
          legend: { position: 'top' }
        }
      }
    });
  }

  function applyStoreUrlFilters() {
    if (typeof applyUrlFilters !== "function") return;
    applyUrlFilters({
      search: "stores-search",
      network: "filter-network",
      country: "filter-country",
      sync_staleness: "filter-sync-staleness"
    });
  }

  function init() {
    window.storesController = new AdminListController({
      domain: 'stores',
      endpoint: '/admin/providers/stores',
      rowsEndpoint: '/admin/providers/stores/rows',
      filterIds: ['filter-network', 'filter-country', 'filter-sync-staleness'],
      searchId: 'stores-search',
      resetId: 'clear-stores-filters-btn',
      colspan: 10,
      autoInit: false
    });

    applyStoreUrlFilters();
    window.storesController.init();

    loadDashboardStats();
    loadCoverageStats();
    loadAffiliateStats();
    loadPricingStats();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
