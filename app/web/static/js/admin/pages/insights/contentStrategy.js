// app/web/static/js/admin/pages/insights/contentStrategy.js
import { getSelectedEntity } from './state.js';
import { fetchAndInjectHtml } from './utilities.js';

export function renderContentStrategy() {
  const panel = document.getElementById('content-strategy-panel');
  if (!panel) return;

  const timeframe = document.getElementById("timeframe-select")?.value || "7_days";
  const selectedEntity = getSelectedEntity();
  const entityFilter = selectedEntity ? `&entity=${encodeURIComponent(selectedEntity)}` : '';

  fetchAndInjectHtml(
    `/admin/insights/widget/content-strategy?time_frame=${timeframe}${entityFilter}`,
    'content-strategy-table-body',
    'Generating content strategies...',
    5,
    { hideElementIdOnEmpty: 'content-strategy-panel' }
  );
}
