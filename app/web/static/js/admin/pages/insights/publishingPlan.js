// app/web/static/js/admin/pages/insights/publishingPlan.js
import { getSelectedEntity } from './state.js';
import { fetchAndInjectHtml } from './utilities.js';

export function renderContentPublishingPlan() {
  const panel = document.getElementById('content-publishing-plan-panel');
  if (!panel) return;

  const timeframe = document.getElementById("timeframe-select")?.value || "7_days";
  const selectedEntity = getSelectedEntity();
  const entityFilter = selectedEntity ? `&entity=${encodeURIComponent(selectedEntity)}` : '';

  fetchAndInjectHtml(
    `/admin/distribution/widget/publishing-plan?time_frame=${timeframe}${entityFilter}`,
    'publishing-plan-body-wrapper',
    'Orchestrating weekly publishing schedule...',
    null,
    { hideElementIdOnEmpty: 'content-publishing-plan-panel' }
  );
}