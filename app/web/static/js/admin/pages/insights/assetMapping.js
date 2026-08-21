// app/web/static/js/admin/pages/insights/assetMapping.js
import { getSelectedEntity } from './state.js';
import { fetchAndInjectHtml } from './utilities.js';

export function renderContentAssetMapping() {
  const panel = document.getElementById("content-asset-mapping-panel");
  const tbody = document.getElementById("asset-mapping-table-body");
  if (!panel || !tbody) return;

  const timeframe = document.getElementById("timeframe-select")?.value || "7_days";
  const selectedEntity = getSelectedEntity();
  const entityFilter = selectedEntity ? `&entity=${encodeURIComponent(selectedEntity)}` : '';

  // Initialize the toggle handler once on tbody
  if (!tbody._listenerInitialized) {
    tbody.addEventListener('click', (e) => {
      const btn = e.target.closest('.asset-mapping-details-toggle');
      if (!btn) return;
      const row = btn.closest('tr');
      if (!row) return;
      const detailsRow = row.nextElementSibling;
      if (!detailsRow) return;

      const icon = btn.querySelector('i');
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      if (expanded) {
        detailsRow.style.display = 'none';
        btn.setAttribute('aria-expanded', 'false');
        if (icon) {
          icon.classList.remove('fa-chevron-down');
          icon.classList.add('fa-chevron-right');
        }
      } else {
        detailsRow.style.display = 'table-row';
        btn.setAttribute('aria-expanded', 'true');
        if (icon) {
          icon.classList.remove('fa-chevron-right');
          icon.classList.add('fa-chevron-down');
        }
      }
    });
    tbody._listenerInitialized = true;
  }

  fetchAndInjectHtml(
    `/admin/insights/widget/asset-mapping?time_frame=${timeframe}${entityFilter}`,
    'asset-mapping-table-body',
    'Mapping strategy to assets...',
    5,
    { hideElementIdOnEmpty: 'content-asset-mapping-panel' }
  );
}
