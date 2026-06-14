// ==============================
// ADMIN — SOURCES CONTROL PANEL
// sources.js
// ==============================

(function () {
  'use strict';

  function renderSourceRow(src) {
    const template = document.getElementById('sources-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    const link = clone.querySelector('.source-cell-name .source-cell-link');
    if (link) {
      link.href = `https://${src.domain}`;
      link.textContent = src.name;
    }

    clone.querySelector('.source-cell-count').textContent = src.content_count.toLocaleString();
    clone.querySelector('.source-cell-time').textContent = src.last_crawl ? formatDate(src.last_crawl, true) : '—';
    clone.querySelector('.source-cell-success-rate').textContent = typeof src.success_rate === 'number' ? `${src.success_rate.toFixed(1)}%` : '100.0%';
    clone.querySelector('.source-cell-failures').textContent = src.failure_count.toLocaleString();
    clone.querySelector('.source-cell-engagement').textContent = src.engagement.toLocaleString();

    const statusCell = clone.querySelector('.source-cell-status');
    statusCell.innerHTML = "";
    const badge = document.createElement("span");
    badge.className = "status-badge";
    if (src.status === 'healthy') {
      badge.classList.add("active");
      badge.textContent = "Healthy";
    } else if (src.status === 'warning') {
      badge.classList.add("inactive", "badge-orange");
      badge.textContent = "Warning";
    } else {
      badge.classList.add("inactive");
      badge.textContent = "Failed";
    }
    statusCell.appendChild(badge);

    clone.querySelector('.source-cell-inspect').href = `/admin/contents?source=${src.slug}`;

    return tr;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const controller = new AdminListController({
      domain: 'sources',
      endpoint: '/admin/providers/sources',
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
      rowTemplateId: 'sources-row-template',
      defaultPerPage: 20,
      colspan: 8,
      itemsKey: 'sources',
      renderRow: renderSourceRow,
      autoInit: false
    });
    controller.init();
  });
})();
