// app/web/static/js/admin/pages/insights/performanceFeedback.js
import { getSelectedEntity } from './state.js';
import { fetchAndInjectHtml } from './utilities.js';

export function renderContentPerformanceFeedback() {
  const panel = document.getElementById("content-feedback-panel");
  if (!panel) return;

  const timeframe = document.getElementById("timeframe-select")?.value || "7_days";
  const selectedEntity = getSelectedEntity();
  const entityFilter = selectedEntity ? `&entity=${encodeURIComponent(selectedEntity)}` : '';

  fetchAndInjectHtml(
    `/admin/insights/widget/performance-feedback?time_frame=${timeframe}${entityFilter}`,
    'content-feedback-panel',
    'Evaluating content metrics...',
    null,
    { hideElementIdOnEmpty: 'content-feedback-panel', displayStyle: 'grid' }
  );
}