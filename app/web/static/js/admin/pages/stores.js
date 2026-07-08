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
    window.api.get('/admin/stores/health_stats')
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
        
      })
      .catch(err => {
        console.error('Failed to load stores dashboard stats', err);
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
      endpoint: '/admin/stores',
      rowsEndpoint: '/admin/stores/rows',
      filterIds: ['filter-network', 'filter-country', 'filter-sync-staleness'],
      searchId: 'stores-search',
      resetId: 'clear-stores-filters-btn',
      colspan: 10,
      autoInit: false
    });

    applyStoreUrlFilters();
    window.storesController.init();

    loadDashboardStats();

  }

  document.addEventListener('DOMContentLoaded', init);
})();
