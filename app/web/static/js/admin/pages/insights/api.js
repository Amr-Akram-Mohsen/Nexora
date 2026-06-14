import { getState, setState } from './state.js';
import { renderAllWidgets, showSpinnerPlaceholders, showErrorPlaceholders } from './index.js';
import { renderContentStrategy } from './contentStrategy.js';
import { renderContentAssetMapping } from './assetMapping.js';
import { renderContentPublishingPlan } from './publishingPlan.js';
import { renderContentPerformanceFeedback } from './performanceFeedback.js';
import { renderAutonomousExecution } from './autonomousExecution.js';
import { renderExecutionGovernance } from './governance.js';

export function fetchInsightsData(timeFrame) {
  showSpinnerPlaceholders();

  fetch(`/admin/insights/data?time_frame=${timeFrame}`)
    .then(res => {
      if (!res.ok) throw new Error("Failed to fetch insights data");
      return res.json();
    })
    .then(data => {
      setState(data);
      renderAllWidgets();
      
      // Trigger lazy fetches for deferred layers in parallel
      fetchStrategyData(timeFrame);
      fetchAssetMappingData(timeFrame);
      fetchPublishingPlanData(timeFrame);
      fetchPerformanceFeedbackData(timeFrame);
      fetchExecutionGovernanceData(timeFrame);
    })
    .catch(err => {
      console.error(err);
      showErrorPlaceholders();
    });
}

export function fetchStrategyData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/strategy?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch strategy data");
      return res.json();
    })
    .then(data => {
      let state = getState();
      if (!state) {
        state = {};
        setState(state);
      }
      state.content_strategy = data;
      renderContentStrategy();
    })
    .catch(err => {
      console.error("Strategy fetch failed:", err);
      const strategyBody = document.getElementById("content-strategy-table-body");
      if (strategyBody) {
        strategyBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">⚠️ Failed to generate content strategies.</td></tr>`;
      }
    });
}

export function fetchAssetMappingData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/assets?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch asset mapping data");
      return res.json();
    })
    .then(data => {
      let state = getState();
      if (!state) {
        state = {};
        setState(state);
      }
      state.content_asset_mapping = data;
      renderContentAssetMapping();
    })
    .catch(err => {
      console.error("Asset mapping fetch failed:", err);
      const mappingBody = document.getElementById("asset-mapping-table-body");
      if (mappingBody) {
        mappingBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">⚠️ Failed to map strategy to assets.</td></tr>`;
      }
    });
}

export function fetchPublishingPlanData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/publishing-plan?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch publishing plan");
      return res.json();
    })
    .then(data => {
      let state = getState();
      if (!state) {
        state = {};
        setState(state);
      }
      state.content_publishing_plan = data;
      renderContentPublishingPlan();
    })
    .catch(err => {
      console.error("Publishing plan fetch failed:", err);
      const publishingContainer = document.getElementById("publishing-plan-grid-container");
      if (publishingContainer) {
        publishingContainer.innerHTML = `<div class="grid-full-width text-center text-danger">⚠️ Failed to load publishing calendar.</div>`;
      }
    });
}

export function fetchPerformanceFeedbackData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/performance?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch performance feedback");
      return res.json();
    })
    .then(data => {
      let state = getState();
      if (!state) {
        state = {};
        setState(state);
      }
      state.content_performance_feedback = data;
      renderContentPerformanceFeedback();
    })
    .catch(err => {
      console.error("Performance feedback fetch failed:", err);
      const evaluationsBody = document.getElementById("feedback-evaluations-body");
      if (evaluationsBody) {
        evaluationsBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">⚠️ Failed to load performance evaluations.</td></tr>`;
      }
      const failuresList = document.getElementById("feedback-failures-list");
      if (failuresList) {
        failuresList.innerHTML = `<p class="text-danger">⚠️ Failed to run failure diagnostics.</p>`;
      }
    });
}

export function fetchExecutionGovernanceData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/governance?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch execution governance");
      return res.json();
    })
    .then(data => {
      let state = getState();
      if (!state) {
        state = {};
        setState(state);
      }
      state.execution_governance = data;
      renderExecutionGovernance();
      
      // Also render autonomous execution if available inside execution_governance payload
      if (data && data.execution_plan) {
         state.execution_plan = data.execution_plan;
         renderAutonomousExecution();
      } else {
         // Fallback if cached governance contains raw plan structure
         state.execution_plan = data;
         renderAutonomousExecution();
      }
    })
    .catch(err => {
      console.error("Execution governance fetch failed:", err);
      const govContainer = document.getElementById("execution-governance-grid-container");
      if (govContainer) {
        govContainer.innerHTML = `<div class="grid-full-width text-center text-danger">⚠️ Failed to load execution governance.</div>`;
      }
      const executionContainer = document.getElementById("execution-plan-grid-container");
      if (executionContainer) {
        executionContainer.innerHTML = `<div class="grid-full-width text-center text-danger">⚠️ Failed to prepare autonomous execution plan.</div>`;
      }
    });
}
