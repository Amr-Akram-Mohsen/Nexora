// ==============================
// ADMIN — RECOMMENDATIONS
// recommendations.js
// ==============================

(function () {
  'use strict';

  let listController;
  let loadedMatches = [];

  function loadStats() {
    fetch('/admin/recommendations/stats')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('rec-stats-row');
        container.className = 'dashboard-stats-grid';
        container.innerHTML = '';

        const template = document.getElementById('rec-stat-card-template');
        const stats = [
          { icon: '🔗', label: 'Total Matches',     value: data.total_matches   },
          { icon: '📰', label: 'Linked Contents',   value: data.linked_contents },
          { icon: '🛍️', label: 'Linked Products',  value: data.linked_items    },
        ];

        stats.forEach(c => {
          const clone = template.content.cloneNode(true);
          clone.querySelector('.dashboard-stat-icon').textContent = c.icon;
          clone.querySelector('.dashboard-stat-value').textContent = (c.value || 0).toLocaleString();
          clone.querySelector('.dashboard-stat-label').textContent = c.label;
          container.appendChild(clone);
        });
      })
      .catch(() => {
        document.getElementById('rec-stats-row').innerHTML =
          '<p class="hint grid-full-width">Could not load stats.</p>';
      });
  }

  function renderRecRow(m) {
    const template = document.getElementById('rec-row-template');
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector('tr');

    clone.querySelector('.rec-content-title').textContent = m.content_title;
    clone.querySelector('.rec-content-id').textContent = `#${m.content_id}`;
    clone.querySelector('.rec-content-type').textContent = m.content_type || '—';
    clone.querySelector('.rec-content-views').textContent = (m.content_views || 0).toLocaleString();
    clone.querySelector('.rec-item-name').textContent = m.item_name;
    clone.querySelector('.rec-item-id').textContent = `#${m.item_id}`;
    clone.querySelector('.rec-item-type').textContent = m.item_type || '—';
    clone.querySelector('.rec-item-clicks').textContent = (m.item_clicks || 0).toLocaleString();

    const inspectBtn = clone.querySelector('.inspect-btn');
    inspectBtn.dataset.contentId = m.content_id;
    inspectBtn.dataset.itemId = m.item_id;

    return tr;
  }

  function unlinkMatch(contentId, itemId, btn, modal) {
    showModal(
      'Remove Association',
      `Remove the link between this content and product? The association can be re-created by running the matcher.`,
      () => {
        if (btn) btn.disabled = true;
        fetch(`/admin/recommendations/matches/${contentId}/${itemId}`, { method: 'DELETE' })
          .then(r => r.json())
          .then(d => {
            if (d.success) {
              showToast('Association removed.', 'success');
              listController.load(listController.currentPage);
              loadStats();
              if (modal) modal.classList.remove("active");
            } else {
              showToast(d.error || 'Unlink failed.', 'error');
              if (btn) btn.disabled = false;
            }
          })
          .catch(() => { showToast('Unlink failed.', 'error'); if (btn) btn.disabled = false; });
      }
    );
  }

  function showInspectModal(match) {
    const modal = document.getElementById("inspect-rec-modal");
    const body = document.getElementById("inspect-rec-modal-body");
    const titleEl = document.getElementById("inspect-rec-modal-title");

    titleEl.textContent = "Recommendation Association Detail";

    const template = document.getElementById("rec-inspect-template");
    const clone = template.content.cloneNode(true);

    clone.querySelector(".inspect-content-id").textContent = `#${match.content_id}`;
    clone.querySelector(".inspect-content-title").textContent = match.content_title;
    clone.querySelector(".inspect-content-type").textContent = match.content_type || "—";
    clone.querySelector(".inspect-content-views").textContent = (match.content_views || 0).toLocaleString();

    clone.querySelector(".inspect-item-id").textContent = `#${match.item_id}`;
    clone.querySelector(".inspect-item-name").textContent = match.item_name;
    clone.querySelector(".inspect-item-type").textContent = match.item_type || "—";
    clone.querySelector(".inspect-item-clicks").textContent = (match.item_clicks || 0).toLocaleString();

    // Bind action button inside inspect modal
    const unlinkBtn = clone.querySelector(".inspect-unlink-btn");
    if (unlinkBtn) {
      unlinkBtn.addEventListener("click", () => {
        unlinkMatch(match.content_id, match.item_id, unlinkBtn, modal);
      });
    }

    body.innerHTML = "";
    body.appendChild(clone);
    modal.classList.add("active");
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadStats();

    listController = new AdminListController({
      domain: 'rec',
      endpoint: '/admin/recommendations/matches',
      tbodyId: 'recs-table-body',
      searchId: 'rec-search',
      filterIds: [],
      perPageId: 'rec-per-page',
      prevBtnId: 'rec-prev-btn',
      nextBtnId: 'rec-next-btn',
      indicatorId: 'rec-page-indicator',
      infoId: 'rec-pagination-info',
      countId: 'rec-count',
      clearBtnId: 'clear-rec-filters-btn',
      refreshBtnId: 'refresh-recs-btn',
      rowTemplateId: 'rec-row-template',
      defaultPerPage: 25,
      colspan: 5,
      itemsKey: 'items',
      renderRow: renderRecRow,
      onLoaded: (data) => {
        loadedMatches = data.items || [];
      },
      autoInit: false
    });
    listController.init();

    // Delegate inspect action
    document.getElementById('recs-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'inspect-rec') {
        const contentId = parseInt(btn.dataset.contentId, 10);
        const itemId = parseInt(btn.dataset.itemId, 10);
        const match = loadedMatches.find(m => m.content_id === contentId && m.item_id === itemId);
        if (match) {
          showInspectModal(match);
        }
      }
    });
  });
})();

