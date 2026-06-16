// ==============================
// ADMIN — SOURCES CONTROL PANEL
// Refactored: HTML partial mode — no renderRow, no JS HTML building
// ==============================

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const controller = new AdminListController({
      domain: 'sources',
      endpoint: '/admin/providers/sources',
      rowsEndpoint: '/admin/providers/sources/rows',  // ← HTML partial mode
      tbodyId: 'sources-table-body',
      searchId: 'sources-search',
      filterIds: [],
      perPageId: 'sources-per-page',
      prevBtnId: 'sources-prev-btn',
      nextBtnId: 'sources-next-btn',
      indicatorId: 'sources-page-indicator',
      infoId: 'sources-pagination-info',
      countId: 'sources-count',
      clearBtnId: 'clear-sources-filters-btn',
      refreshBtnId: 'refresh-sources-btn',
      defaultPerPage: 20,
      colspan: 8,
      autoInit: false
    });
    controller.init();
  });
})();
