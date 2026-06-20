// app/web/static/js/admin/pages/insights/index.js
import { getSelectedEntity, setSelectedEntity } from './state.js';
import { getSpinnerHtml, getErrorStateHtml, getEmptyStateHtml, fetchAndInjectHtml } from './utilities.js';
import { renderContentStrategy } from './contentStrategy.js';
import { renderContentAssetMapping } from './assetMapping.js';
import { renderContentPublishingPlan } from './publishingPlan.js';
import { renderContentPerformanceFeedback } from './performanceFeedback.js';
import { renderAutonomousExecution } from './autonomousExecution.js';
import { renderExecutionGovernance } from './governance.js';
import { renderSocialDistribution } from './socialDistribution.js';

document.addEventListener("DOMContentLoaded", () => {
  initInsights();
});

function initInsights() {
  const timeframeSelect = document.getElementById("timeframe-select");
  if (timeframeSelect) {
    timeframeSelect.addEventListener("change", () => {
      const timeframe = timeframeSelect.value;
      setSelectedEntity(null);
      updateFilterUI();
      
      loadMainWidgets(timeframe)
        .then(() => {
          renderAllWidgets();
        })
        .catch(err => {
          console.error(err);
        });
    });
  }

  const refreshBtn = document.getElementById("refresh-insights-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      const timeframe = timeframeSelect ? timeframeSelect.value : "7_days";
      setSelectedEntity(null);
      updateFilterUI();
      
      fetch(`/admin/insights/recompute?layer=all&time_frame=${timeframe}`, { method: 'POST' })
        .then(() => loadMainWidgets(timeframe))
        .then(() => {
          renderAllWidgets();
        })
        .catch(err => {
          console.error(err);
        });
    });
  }

  const clearFilterBtn = document.getElementById("clear-filter-btn");
  if (clearFilterBtn) {
    clearFilterBtn.addEventListener("click", () => {
      setSelectedEntity(null);
      updateFilterUI();
      renderAllWidgets();
    });
  }

  // Initial data load
  const initialTimeframe = timeframeSelect ? timeframeSelect.value : "7_days";
  updateFilterUI();
  loadMainWidgets(initialTimeframe)
    .then(() => {
      renderAllWidgets();
    })
    .catch(err => {
      console.error(err);
    });

  // Delegated handlers
  const topBody = document.getElementById('top-opportunities-table-body');
  if (topBody) {
    topBody.addEventListener('click', (e) => {
      const row = e.target.closest('tr.clickable-row');
      if (!row) return;
      const entity = row.dataset.entity;
      if (!entity) return;
      toggleEntityFilter(entity);
    });
  }

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
    fetchAndInjectHtml(`/admin/insights/widget/recommendations?time_frame=${timeFrame}`, 'recommendations-widget-container', 'Loading metrics...'),
    fetchAndInjectHtml(`/admin/insights/widget/top-opportunities?time_frame=${timeFrame}`, 'top-opportunities-table-body', 'Prioritizing entities...', 5),
    fetchAndInjectHtml(`/admin/insights/widget/action-queue?time_frame=${timeFrame}`, 'action-queue-list', 'Compiling action guidance...'),
    fetchAndInjectHtml(`/admin/insights/widget/coverage-matrix?time_frame=${timeFrame}`, 'coverage-matrix-table-body', 'Assessing category alignment...', 4),
    fetchAndInjectHtml(`/admin/insights/widget/intent-opportunities?time_frame=${timeFrame}`, 'intent-opportunities-list', 'Analyzing intent distributions...'),
    fetchAndInjectHtml(`/admin/insights/widget/brand-opportunities?time_frame=${timeFrame}`, 'brand-opportunities-table-body', 'Calculating brand expansion opportunities...', 4)
  ];
  return Promise.all(promises);
}

export function toggleEntityFilter(entity) {
  const selected = getSelectedEntity();
  if (selected === entity) {
    setSelectedEntity(null);
  } else {
    setSelectedEntity(entity);
  }
  
  updateFilterUI();
  renderAllWidgets();
}

export function updateFilterUI() {
  const selected = getSelectedEntity();
  const container = document.getElementById("active-filter-container");
  const badge = document.getElementById("active-filter-badge");
  if (!container || !badge) return;

  if (selected) {
    badge.textContent = selected;
    container.style.display = "flex";
  } else {
    container.style.display = "none";
  }
}

export function renderAllWidgets() {
  renderContentStrategy();
  renderContentAssetMapping();
  renderContentPublishingPlan();
  renderContentPerformanceFeedback();
  renderAutonomousExecution();
  renderExecutionGovernance();
  renderSocialDistribution();
}