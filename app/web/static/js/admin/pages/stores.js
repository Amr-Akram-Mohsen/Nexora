// ==============================
// ADMIN — STORES CONTROL PANEL
// stores.js
// ==============================

(function () {
  'use strict';

  function renderStoreRow(st) {
    const template = document.getElementById('stores-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    const link = clone.querySelector('.store-cell-name .store-cell-link');
    if (link) {
      link.href = st.website;
      link.textContent = st.name;
    }

    // const slugEl = clone.querySelector('.store-cell-slug');
    // if (slugEl) {
    //   slugEl.textContent = st.slug;
    // }

    clone.querySelector('.store-cell-network').textContent = st.affiliate_network || 'Direct';
    clone.querySelector('.store-cell-count').textContent = st.product_count.toLocaleString();
    clone.querySelector('.store-cell-clicks').textContent = st.clicks.toLocaleString();
    clone.querySelector('.store-cell-ctr').textContent = typeof st.ctr === 'number' ? `${st.ctr.toFixed(2)}%` : '0.00%';
    clone.querySelector('.store-cell-conversions').textContent = st.conversions.toLocaleString();

    const statusCell = clone.querySelector('.store-cell-status');
    statusCell.innerHTML = "";
    const badge = document.createElement("span");
    badge.className = "status-badge";
    if (st.status === 'healthy') {
      badge.classList.add("active");
      badge.textContent = "Healthy";
    } else if (st.status === 'warning') {
      badge.classList.add("inactive", "badge-orange");
      badge.textContent = "Warning";
    } else {
      badge.classList.add("inactive");
      badge.textContent = "Failed";
    }
    statusCell.appendChild(badge);

    const inspectBtn = clone.querySelector('.store-cell-inspect');
    if (inspectBtn) {
      inspectBtn.href = `/admin/items?source=${st.slug}`;
    }

    return tr;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const controller = new AdminListController({
      domain: 'stores',
      endpoint: '/admin/providers/stores',
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
      rowTemplateId: 'stores-row-template',
      defaultPerPage: 20,
      colspan: 8,
      itemsKey: 'stores',
      renderRow: renderStoreRow,
      autoInit: false
    });
    controller.init();
  });
})();
