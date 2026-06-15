// app/web/static/js/admin/pages/insights/api.js
import { getState, setState } from './state.js';
import { fetchJson, createTableStateRow } from './utilities.js';
import { renderContentStrategy } from './contentStrategy.js';
import { renderContentAssetMapping } from './assetMapping.js';
import { renderContentPublishingPlan } from './publishingPlan.js';
import { renderContentPerformanceFeedback } from './performanceFeedback.js';
import { renderAutonomousExecution } from './autonomousExecution.js';
import { renderExecutionGovernance } from './governance.js';

export function fetchInsightsData(timeFrame) {
  // callers will show spinners before calling this
  return fetchJson(`/admin/insights/data?time_frame=${timeFrame}`)
    .then(data => {
      setState(data);
      return data;
    });
}

export function fetchStrategyData(timeFrame) {
  return fetchJson(`/admin/insights/strategy?time_frame=${timeFrame}`)
    .then(data => {
      const state = getState() || {};
      state.content_strategy = data;
      setState(state);
      renderContentStrategy();
      return data;
    })
    .catch(err => {
      console.error('Strategy fetch failed:', err);
      const strategyBody = document.getElementById('content-strategy-table-body');
      if (strategyBody) {
        strategyBody.innerHTML = '';
        strategyBody.appendChild(createTableStateRow(5, '⚠️ Failed to generate content strategies.', 'error'));
      }
      throw err;
    });
}

export function fetchAssetMappingData(timeFrame) {
  return fetchJson(`/admin/insights/assets?time_frame=${timeFrame}`)
    .then(data => {
      const state = getState() || {};
      state.content_asset_mapping = data;
      setState(state);
      renderContentAssetMapping();
      return data;
    })
    .catch(err => {
      console.error('Asset mapping fetch failed:', err);
      const mappingBody = document.getElementById('asset-mapping-table-body');
      if (mappingBody) {
        mappingBody.innerHTML = '';
        mappingBody.appendChild(createTableStateRow(5, '⚠️ Failed to map strategy to assets.', 'error'));
      }
      throw err;
    });
}

export function fetchPublishingPlanData(timeFrame) {
  return fetchJson(`/admin/insights/publishing-plan?time_frame=${timeFrame}`)
    .then(data => {
      const state = getState() || {};
      state.content_publishing_plan = data;
      setState(state);
      renderContentPublishingPlan();
      return data;
    })
    .catch(err => {
      console.error('Publishing plan fetch failed:', err);
      const publishingContainer = document.getElementById('publishing-plan-grid-container');
      if (publishingContainer) {
        publishingContainer.innerHTML = '';
        publishingContainer.appendChild(createTableStateRow(1, '⚠️ Failed to load publishing calendar.', 'error'));
      }
      throw err;
    });
}

export function fetchPerformanceFeedbackData(timeFrame) {
  return fetchJson(`/admin/insights/performance?time_frame=${timeFrame}`)
    .then(data => {
      const state = getState() || {};
      state.content_performance_feedback = data;
      setState(state);
      renderContentPerformanceFeedback();
      return data;
    })
    .catch(err => {
      console.error('Performance feedback fetch failed:', err);
      const evaluationsBody = document.getElementById('feedback-evaluations-body');
      if (evaluationsBody) {
        evaluationsBody.innerHTML = '';
        evaluationsBody.appendChild(createTableStateRow(5, '⚠️ Failed to load performance evaluations.', 'error'));
      }
      const failuresList = document.getElementById('feedback-failures-list');
      if (failuresList) {
        failuresList.innerHTML = '<p class="text-danger">⚠️ Failed to run failure diagnostics.</p>';
      }
      throw err;
    });
}

export function fetchExecutionGovernanceData(timeFrame) {
  return fetchJson(`/admin/insights/governance?time_frame=${timeFrame}`)
    .then(data => {
      const state = getState() || {};
      state.execution_governance = data;
      // also set execution_plan if present
      if (data && data.execution_plan) state.execution_plan = data.execution_plan;
      setState(state);
      renderExecutionGovernance();
      if (state.execution_plan) renderAutonomousExecution();
      return data;
    })
    .catch(err => {
      console.error('Execution governance fetch failed:', err);
      const govContainer = document.getElementById('execution-governance-grid-container');
      if (govContainer) {
        govContainer.innerHTML = '';
        govContainer.appendChild(createTableStateRow(1, '⚠️ Failed to load execution governance.', 'error'));
      }
      const executionContainer = document.getElementById('execution-plan-grid-container');
      if (executionContainer) {
        executionContainer.innerHTML = '';
        executionContainer.appendChild(createTableStateRow(1, '⚠️ Failed to prepare autonomous execution plan.', 'error'));
      }
      throw err;
    });
}