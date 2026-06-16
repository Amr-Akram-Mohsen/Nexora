// ==============================
// ADMIN — STORES CONTROL PANEL
// Refactored: HTML partial mode — no renderRow, no JS HTML building
// ==============================

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const controller = new AdminListController({
      domain: 'stores',
      endpoint: '/admin/providers/stores',
      rowsEndpoint: '/admin/providers/stores/rows',   // ← HTML partial mode
      tbodyId: 'stores-table-body',
      searchId: 'stores-search',
      filterIds: [],
      perPageId: 'stores-per-page',
      prevBtnId: 'stores-prev-btn',
      nextBtnId: 'stores-next-btn',
      indicatorId: 'stores-page-indicator',
      infoId: 'stores-pagination-info',
      countId: 'stores-count',
      clearBtnId: 'clear-stores-filters-btn',
      refreshBtnId: 'refresh-stores-btn',
      defaultPerPage: 20,
      colspan: 8,
      autoInit: false
    });
    controller.init();
  });
})();
