// app/web/static/js/admin/pages/insights/index.js (partial — integrate into existing file)
import { getState, setState } from './state.js';
import { fetchInsightsData, fetchStrategyData, fetchAssetMappingData, fetchPublishingPlanData, fetchPerformanceFeedbackData, fetchExecutionGovernanceData } from './api.js';
import { getSpinnerHtml, getErrorStateHtml, getEmptyStateHtml } from './utilities.js';
import { renderContentStrategy } from './contentStrategy.js';
import { renderContentAssetMapping } from './assetMapping.js';
import { renderContentPublishingPlan } from './publishingPlan.js';
import { renderContentPerformanceFeedback } from './performanceFeedback.js';
import { renderAutonomousExecution } from './autonomousExecution.js';
import { renderExecutionGovernance } from './governance.js';

document.addEventListener("DOMContentLoaded", () => {
  initInsights();
});

function initInsights() {
  const timeframeSelect = document.getElementById("timeframe-select");
  if (timeframeSelect) {
    timeframeSelect.addEventListener("change", () => {
      const data = getState();
      if (data) data.selected_entity = null;
      fetchInsightsData(timeframeSelect.value)
        .then(data => {
          setState(data);
          // initial render via downstream modules (fetchStrategyData etc.)
        })
        .catch(() => {});
    });
  }

  const refreshBtn = document.getElementById("refresh-insights-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      const timeframe = timeframeSelect ? timeframeSelect.value : "7_days";
      const data = getState();
      if (data) data.selected_entity = null;
      fetchInsightsData(timeframe)
        .then(data => setState(data))
        .catch(() => {});
    });
  }

  const clearFilterBtn = document.getElementById("clear-filter-btn");
  if (clearFilterBtn) {
    clearFilterBtn.addEventListener("click", () => {
      const data = getState();
      if (data) {
        data.selected_entity = null;
        renderAllWidgets();
      }
    });
  }

  // Initial data load
  fetchInsightsData("7_days")
    .then(data => {
      setState(data);
      // trigger deferred loads
      fetchStrategyData("7_days");
      fetchAssetMappingData("7_days");
      fetchPublishingPlanData("7_days");
      fetchPerformanceFeedbackData("7_days");
      fetchExecutionGovernanceData("7_days");
    })
    .catch(err => {
      console.error(err);
      showErrorPlaceholders();
    });

  // Delegated handlers
  const topBody = document.getElementById('top-opportunities-body');
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

// Keep toggleEntityFilter, showSpinnerPlaceholders, showErrorPlaceholders, renderAllWidgets implementations (they can call the refactored module renderers).