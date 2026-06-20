// ==============================
// ADMIN — RECOMMENDATIONS
// Refactored: HTML partial mode — no renderRow, no JS HTML building
// ==============================

(function () {
  'use strict';

  window.recController = null;

  function loadStats() {
    fetch('/admin/recommendations/stats')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('rec-stats-row');
        container.className = 'dashboard-stats-grid';
        container.innerHTML = '';

        const template = document.getElementById('rec-stat-card-template');
        const stats = [
          { icon: '🔗', label: 'Total Matches', value: data.total_matches },
          { icon: '📰', label: 'Linked Contents', value: data.linked_contents },
          { icon: '🛍️', label: 'Linked Products', value: data.linked_items },
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
              window.recController.load(window.recController.currentPage);
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



  document.addEventListener('DOMContentLoaded', () => {
    loadStats();

    window.recController = new AdminListController({
      domain: 'rec',
      endpoint: '/admin/recommendations/matches',
      rowsEndpoint: '/admin/recommendations/matches/rows',
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });
    window.recController.init();


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
