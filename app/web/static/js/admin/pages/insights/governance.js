// app/web/static/js/admin/pages/insights/governance.js
import { fetchAndInjectHtml } from './utilities.js';

export function renderExecutionGovernance() {
  const panel = document.getElementById("execution-governance-panel");
  if (!panel) return;

  const timeframe = document.getElementById("timeframe-select")?.value || "7_days";

  fetchAndInjectHtml(
    `/admin/insights/widget/governance?time_frame=${timeframe}`,
    'execution-governance-body-wrapper',
    'Loading governance queues...',
    null,
    { hideElementIdOnEmpty: 'execution-governance-panel' }
  );
}