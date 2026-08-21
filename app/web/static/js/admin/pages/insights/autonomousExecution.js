// app/web/static/js/admin/pages/insights/autonomousExecution.js
import { fetchAndInjectHtml } from './utilities.js';

export function renderAutonomousExecution() {
  const panel = document.getElementById("autonomous-execution-panel");
  if (!panel) return;

  const timeframe = document.getElementById("timeframe-select")?.value || "7_days";

  fetchAndInjectHtml(
    `/admin/distribution/widget/autonomous-execution?time_frame=${timeframe}`,
    'autonomous-execution-body-wrapper',
    'Preparing autonomous queues...'
  );
}
