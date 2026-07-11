// app/web/static/js/admin/pages/deduplication.js
// Deduplication Workbench — interaction handlers.
// Requires: api.js wrapper (core/api.js), loading.js (core/loading.js)

(function () {
  'use strict';

  function removeCardById(id) {
    var card = document.getElementById('dup-product-' + id);
    if (card) {
      card.classList.add('is-removing');
      setTimeout(function () { card.remove(); }, 300);
    }
  }

  function removeGroupPanel(groupIndex) {
    var panel = document.getElementById('dup-group-' + groupIndex);
    if (panel) {
      panel.classList.add('is-removing');
      setTimeout(function () { panel.remove(); }, 300);
    }
  }

  function deleteDuplicate(id) {
    showModal(
      'Delete Duplicate',
      'Are you sure you want to delete this duplicate content? This action cannot be undone.',
      function () {
        removeCardById(id);
        window.api.post('/admin/contents/bulk', { action: 'delete', ids: [id] })
          .then(function (data) {
            if (data && data.success) {
              showToast('Duplicate deleted successfully.', 'success');
            } else {
              showToast((data && data.error) || 'Failed to delete product.', 'error');
              var card = document.getElementById('dup-product-' + id);
              if (card) card.classList.remove('is-removing');
            }
          })
          .catch(function () {
            var card = document.getElementById('dup-product-' + id);
            if (card) card.classList.remove('is-removing');
          });
      }
    );
  }

  function deleteAllButFirst(groupIndex, products) {
    if (!products || products.length <= 1) return;

    var sorted = products.slice().sort(function (a, b) { return a.id - b.id; });
    var idsToDelete = sorted.slice(1).map(function (i) { return i.id; });

    showModal(
      'Keep Oldest Only',
      'Delete ' + idsToDelete.length + ' duplicate(s) and keep only the oldest entry? This cannot be undone.',
      function () {
        removeGroupPanel(groupIndex);
        window.api.post('/admin/contents/bulk', { action: 'delete', ids: idsToDelete })
          .then(function (data) {
            if (data && data.success) {
              showToast('Kept oldest; removed ' + idsToDelete.length + ' duplicate(s).', 'success');
            } else {
              showToast((data && data.error) || 'Failed to delete products.', 'error');
              var panel = document.getElementById('dup-group-' + groupIndex);
              if (panel) panel.classList.remove('is-removing');
            }
          })
          .catch(function () {
            var panel = document.getElementById('dup-group-' + groupIndex);
            if (panel) panel.classList.remove('is-removing');
          });
      }
    );
  }

  // ── Event delegation ──
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;

    var action = btn.dataset.action;

    if (action === 'delete-dup') {
      var id = parseInt(btn.dataset.id, 10);
      deleteDuplicate(id);
      return;
    }

    if (action === 'keep-oldest') {
      var groupIndex = btn.dataset.group;
      var products;
      try {
        products = JSON.parse(btn.dataset.products);
      } catch (_) {
        products = [];
      }
      deleteAllButFirst(groupIndex, products);
    }
  });

})();
