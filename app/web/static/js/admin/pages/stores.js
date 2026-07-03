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
    window.api.get('/admin/providers/stores/health_stats')
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
        if (distContainer) distContainer.innerHTML = data.oos_by_store_html || '<div class="text-muted text-sm py-2">No out-of-stock issues detected.</div>';

        renderAvailabilityChart(data.availability_breakdown);
        renderSyncCadenceChart(data.sync_cadence);
        renderAvgSyncAgeChart(data.avg_sync_age_by_store);
        const topStaleContainer = document.getElementById('list-stale-stores');
        if (topStaleContainer) topStaleContainer.innerHTML = data.top_stale_stores_html || '<li class="text-center w-full py-4 text-muted">No stale stores found.</li>';
      })
      .catch(err => {
        console.error('Failed to load stores dashboard stats', err);
      });
  }

  function renderAvailabilityChart(breakdown) {
    const ctx = document.getElementById('chart-availability');
    if (!ctx || !breakdown || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    availabilityChart = window.nexoraCharts.render('chart-availability', 'doughnut', {
        labels: ['InStock', 'OutOfStock', 'PreOrder', 'Unknown'],
        datasets: [{
          data: [
            breakdown.InStock || 0, 
            breakdown.OutOfStock || 0, 
            breakdown.PreOrder || 0, 
            breakdown.Unknown || 0
          ],
          backgroundColor: [palette[3], palette[1], palette[2], '#9ca3af'],
          borderWidth: 0
        }]
      }, {
        plugins: {
          legend: { position: 'right' }
        }
      });
  }

  function renderSyncCadenceChart(cadenceData) {
    const ctx = document.getElementById('chart-sync-cadence');
    if (!ctx || !cadenceData || !cadenceData.length || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    syncCadenceChart = window.nexoraCharts.render('chart-sync-cadence', 'line', {
        labels: labels,
        datasets: [{
          label: 'Sync Volume',
          data: dataPoints,
          borderColor: palette[5],
          backgroundColor: 'rgba(139, 92, 246, 0.1)',
          fill: true,
          tension: 0.4
        }]
      }, {
        scales: {
          y: { beginAtZero: true, display: false },
          x: { display: false }
        },
        plugins: {
          legend: { display: false }
        }
      });
  }

  function renderAvgSyncAgeChart(storeData) {
    const ctx = document.getElementById('chart-sync-age');
    if (!ctx || !storeData || !storeData.length || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    syncAgeChart = window.nexoraCharts.render('chart-sync-age', 'bar', {
        labels: labels,
        datasets: [{
          label: 'Avg Sync Age (Days)',
          data: dataPoints,
          backgroundColor: palette[2],
          borderRadius: 4
        }]
      }, {
        plugins: {
          legend: { display: false }
        }
      });
  }

  function renderTopStaleStores(storeData) {
    // Replaced by Jinja partial
  }

  function loadCoverageStats() {
    window.api.get('/admin/providers/stores/coverage_stats')
      .then(data => {
        // Render Category Coverage
        const catContainer = document.getElementById('stats-category-coverage');
        if (catContainer) catContainer.innerHTML = data.category_coverage_html;
        
        // Render Commission Rates
        const commContainer = document.getElementById('stats-commission-rates');
        if (commContainer) commContainer.innerHTML = data.commission_rates_html;
      })
      .catch(err => {
        console.error('Failed to load stores coverage stats', err);
      });
  }

  let trackingCoverageChart = null;
  let deeplinkFreshnessChart = null;
  let programDistributionChart = null;

  function loadAffiliateStats() {
    window.api.get('/admin/providers/stores/affiliate_stats')
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
                    alertContainer.classList.remove('is-hidden');
                }
            }
        }
        
        renderTrackingCoverageChart(data.tracking_coverage);
        renderDeeplinkFreshnessChart(data.deeplink_freshness);
        renderProgramDistributionChart(data.program_distribution);
        const commRankingContainer = document.getElementById('list-commission-stores');
        if (commRankingContainer) commRankingContainer.innerHTML = data.commission_rate_ranking_html;
      })
      .catch(err => {
        console.error('Failed to load affiliate stats', err);
      });
  }

  function renderTrackingCoverageChart(coverage) {
    const ctx = document.getElementById('chart-tracking-coverage');
    if (!ctx || !coverage || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    trackingCoverageChart = window.nexoraCharts.render('chart-tracking-coverage', 'doughnut', {
        labels: Object.keys(coverage),
        datasets: [{
          data: Object.values(coverage),
          backgroundColor: [palette[3], palette[1]],
          borderWidth: 0
        }]
      }, {
        plugins: {
          legend: { position: 'right' }
        }
      });
  }

  function renderDeeplinkFreshnessChart(freshness) {
    const ctx = document.getElementById('chart-deeplink-freshness');
    if (!ctx || !freshness || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    deeplinkFreshnessChart = window.nexoraCharts.render('chart-deeplink-freshness', 'doughnut', {
        labels: Object.keys(freshness),
        datasets: [{
          data: Object.values(freshness),
          backgroundColor: [palette[3], palette[2], palette[1], palette[4]],
          borderWidth: 0
        }]
      }, {
        plugins: {
          legend: { position: 'right' }
        }
      });
  }

  function renderProgramDistributionChart(distribution) {
    const ctx = document.getElementById('chart-program-distribution');
    if (!ctx || !distribution || !distribution.length || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    programDistributionChart = window.nexoraCharts.render('chart-program-distribution', 'bar', {
        labels: distribution.map(d => d.name),
        datasets: [{
          label: 'Number of Links',
          data: distribution.map(d => d.count),
          backgroundColor: palette[5],
          borderRadius: 4
        }]
      }, {
        plugins: {
          legend: { display: false }
        }
      });
  }

  function renderTopCommissionStores(storeData) {
    // Replaced by Jinja partial
  }

  let currencyMixChart = null;
  let priceStalenessChart = null;

  function loadPricingStats() {
    window.api.get('/admin/providers/stores/pricing_stats')
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
            alertsList.innerHTML = data.pricing_alerts_html || '';
            if (data.pricing_alerts_html) alertsContainer.classList.remove('is-hidden');
        }
        
        renderCurrencyMixChart(data.currency_mix);
        
        const discountContainer = document.getElementById('list-discount-stores');
        if (discountContainer) discountContainer.innerHTML = data.discount_depth_ranking_html;

        renderPriceStalenessChart(data.price_staleness_grid);
      })
      .catch(err => {
        console.error('Failed to load pricing stats', err);
      });
  }

  function renderCurrencyMixChart(currencyData) {
    const ctx = document.getElementById('chart-currency-mix');
    if (!ctx || !currencyData || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    currencyMixChart = window.nexoraCharts.render('chart-currency-mix', 'doughnut', {
        labels: Object.keys(currencyData),
        datasets: [{
          data: Object.values(currencyData),
          backgroundColor: [palette[2], palette[3], palette[1], palette[5], palette[4]],
          borderWidth: 0
        }]
      }, {
        plugins: {
          legend: { position: 'right' }
        }
      });
  }

  function renderDiscountRanking(storeData) {
    // Replaced by Jinja partial
  }

  function renderPriceStalenessChart(gridData) {
    const ctx = document.getElementById('chart-price-staleness');
    if (!ctx || !gridData || !gridData.length || typeof Chart === 'undefined') return;
    
    const palette = window.nexoraCharts.getColors();
    priceStalenessChart = window.nexoraCharts.render('chart-price-staleness', 'bar', {
        labels: labels,
        datasets: [
          {
            label: 'Fresh (< 7 days)',
            data: freshData,
            backgroundColor: palette[3]
          },
          {
            label: 'Stale (> 7 days)',
            data: staleData,
            backgroundColor: palette[1]
          }
        ]
      }, {
        scales: {
          x: { stacked: true },
          y: { stacked: true }
        },
        plugins: {
          legend: { position: 'top' }
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
