// app/web/static/js/admin/pages/distribution/index.js
import { getSelectedEntity, setSelectedEntity } from '../insights/state.js';
import { fetchAndInjectHtml } from '../insights/utilities.js';
import { renderContentPublishingPlan } from '../insights/publishingPlan.js';
import { renderAutonomousExecution } from '../insights/autonomousExecution.js';
import { renderExecutionGovernance } from '../insights/governance.js';
import { renderSocialDistribution, initSocialDistributionFilters } from '../insights/socialDistribution.js';

document.addEventListener("DOMContentLoaded", () => {
  initDistribution();
  initSocialDistributionFilters();
});

function initDistribution() {
  const timeframeSelect = document.getElementById("timeframe-select");
  if (timeframeSelect) {
    timeframeSelect.addEventListener("change", () => {
      const timeframe = timeframeSelect.value;
      setSelectedEntity(null);
      
      loadMainWidgets(timeframe)
        .then(() => {
          renderAllWidgets();
        })
        .catch(err => {
          console.error(err);
        });
    });
  }

  const refreshBtn = document.getElementById("refresh-distribution-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      const timeframe = timeframeSelect ? timeframeSelect.value : "7_days";
      setSelectedEntity(null);
      
      fetch(`/admin/distribution/recompute?layer=all&time_frame=${timeframe}`, { method: 'POST' })
        .then(() => loadMainWidgets(timeframe))
        .then(() => {
          renderAllWidgets();
        })
        .catch(err => {
          console.error(err);
        });
    });
  }

  // Initial data load
  const initialTimeframe = timeframeSelect ? timeframeSelect.value : "7_days";
  loadMainWidgets(initialTimeframe)
    .then(() => {
      renderAllWidgets();
    })
    .catch(err => {
      console.error(err);
    });

  // Delegated handler for Action Queue accordion expansion
  const actionQueue = document.getElementById('action-queue-list');
  if (actionQueue) {
    actionQueue.addEventListener('click', (e) => {
      const card = e.target.closest('.insights-opp-card');
      if (!card) return;
      if (e.target.tagName === 'A') return;
      const details = card.querySelector('.action-card-details');
      const arrow = card.querySelector('.expand-arrow');
      if (!details) return;
      const isCollapsed = details.style.display === '' || details.style.display === 'none';
      details.style.display = isCollapsed ? 'block' : 'none';
      if (arrow) arrow.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
    });
  }
}

export function loadMainWidgets(timeFrame) {
  const promises = [
    fetchAndInjectHtml(`/admin/distribution/widget/health-alerts`, 'distribution-health-alerts-wrapper', ''),
    fetchAndInjectHtml(`/admin/distribution/widget/overview-kpis`, 'distribution-overview-kpis-container', 'Loading overview metrics...', 7),
    fetchAndInjectHtml(`/admin/distribution/widget/action-queue?time_frame=${timeFrame}`, 'action-queue-list', 'Compiling action guidance...'),
    fetchAndInjectHtml(`/admin/distribution/widget/scheduling-queue`, 'scheduling-queue-list', 'Loading scheduled posts...'),
    fetchAndInjectHtml(`/admin/distribution/widget/platform-performance`, 'platform-performance-container', 'Loading platform performance...'),
    fetchAndInjectHtml(`/admin/distribution/widget/coverage-analytics`, 'coverage-analytics-container', 'Loading asset coverage...'),
  ];
  return Promise.all(promises);
}

export function renderAllWidgets() {
  renderContentPublishingPlan();
  renderAutonomousExecution();
  renderExecutionGovernance();
  renderSocialDistribution();
}
