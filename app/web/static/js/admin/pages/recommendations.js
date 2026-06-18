// ==============================
// ADMIN — RECOMMENDATIONS
// Refactored: HTML partial mode — no renderRow, no JS HTML building
// ==============================

(function () {
  'use strict';

  let listController;

  function loadStats() {
    fetch('/admin/recommendations/stats')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('rec-stats-row');
        container.className = 'dashboard-stats-grid';
        container.innerHTML = '';

        const template = document.getElementById('rec-stat-card-template');
        const stats = [
          { icon: '🔗', label: 'Total Matches',    value: data.total_matches   },
          { icon: '📰', label: 'Linked Contents',  value: data.linked_contents },
          { icon: '🛍️', label: 'Linked Products', value: data.linked_items    },
        ];

        stats.forEach(c => {
          const clone = template.content.cloneNode(true);
          clone.querySelector('.dashboard-stat-icon').textContent  = c.icon;
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

  // ── Inspect Modal (server-rendered body) ──────────────────────
  function openInspectModal(contentId, itemId) {
    const modal   = document.getElementById("inspect-rec-modal");
    const body    = document.getElementById("inspect-rec-modal-body");
    const titleEl = document.getElementById("inspect-rec-modal-title");
    if (!modal || !body) return;

    body.innerHTML = '<div class="dashboard-loading"><div class="spinner"></div><p>Loading…</p></div>';
    titleEl.textContent = "Recommendation Association Detail";
    modal.classList.add("active");

    fetch(`/admin/recommendations/matches/${contentId}/${itemId}/inspect`)
      .then(r => r.text())
      .then(html => { body.innerHTML = html; })
      .catch(() => { body.innerHTML = "<p class='text-muted'>Could not load details.</p>"; });
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadStats();

    listController = new AdminListController({
      domain: 'rec',
      endpoint: '/admin/recommendations/matches',
      rowsEndpoint: '/admin/recommendations/matches/rows',  // ← HTML partial mode
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
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });
    listController.init();

    // Table body: inspect click delegation
    document.getElementById('recs-table-body').addEventListener('click', e => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'inspect-rec') {
        let contentId, itemId;
        if (btn.dataset.id) {
          const parts = btn.dataset.id.split('-');
          contentId = parseInt(parts[0], 10);
          itemId = parseInt(parts[1], 10);
        } else {
          contentId = parseInt(btn.closest('tr')?.id?.split('-')[2] || btn.dataset.contentId, 10);
          itemId    = parseInt(btn.closest('tr')?.id?.split('-')[3] || btn.dataset.itemId, 10);
        }
        openInspectModal(contentId, itemId);
      }
    });

    // Inspect modal: unlink action delegation (rendered by _inspect.html)
    const modal = document.getElementById("inspect-rec-modal");
    if (modal) {
      modal.addEventListener('click', e => {
        const btn = e.target.closest("[data-action='unlink-match']");
        if (!btn) return;
        const cid = parseInt(btn.dataset.contentId, 10);
        const iid = parseInt(btn.dataset.itemId, 10);
        unlinkMatch(cid, iid, btn, modal);
      });
    }
  });
})();
