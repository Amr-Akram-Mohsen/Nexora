// app/web/static/js/admin/pages/pipeline.js
// Pipeline Audit — stats loading and retry handling.
// Requires: api.js wrapper (core/api.js), loading.js (core/loading.js)

(function () {
  'use strict';

  var container  = document.getElementById('pipeline-stats-container');
  var refreshBtn = document.getElementById('refresh-pipeline-btn');

  if (!container || !refreshBtn) return;

  function setLoading(active) {
    refreshBtn.disabled = active;
    var icon = refreshBtn.querySelector('i');
    if (icon) {
      icon.classList.toggle('fa-spin', active);
    }
  }

  function loadStats() {
    setLoading(true);
    renderSpinner(container, 'Loading pipeline statistics…');

    fetchAndInjectHtml('/admin/contents/pipeline/stats/partial', 'pipeline-stats-container')
      .then(function () {
        setLoading(false);
      })
      .catch(function () {
        setLoading(false);
      });
  }

  function retryFailed(origin) {
    var label = origin || 'all origins';
    showModal(
      'Retry Failed Articles',
      'Requeue all failed articles from <strong>' + label + '</strong>? They will be re-processed in the background.',
      function () {
        window.api.post('/admin/contents/pipeline/retry', { origin: origin })
          .then(function (data) {
            if (data && data.success) {
              showToast('Successfully requeued ' + data.retried + ' articles.', 'success');
              loadStats();
            } else {
              showToast('Failed to retry articles.', 'error');
            }
          });
      }
    );
  }

  // ── Event delegation for retry buttons inside the dynamically loaded partial ──
  container.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-action="retry-failed"]');
    if (btn) {
      retryFailed(btn.dataset.origin);
    }
  });

  refreshBtn.addEventListener('click', loadStats);

  // Initial load
  loadStats();

})();
