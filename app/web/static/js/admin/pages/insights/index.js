// app/web/static/js/admin/pages/insights/index.js
import { getSelectedEntity, setSelectedEntity } from './state.js';
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
      const timeframe = timeframeSelect.value;
      setSelectedEntity(null);
      updateFilterUI();
      
      loadMainWidgets(timeframe)
        .then(() => {
          renderAllWidgets();
        })
        .catch(err => {
          console.error(err);
          showErrorPlaceholders();
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
          showErrorPlaceholders();
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

export function loadMainWidgets(timeFrame) {
  showSpinnerPlaceholders();
  
  const widgets = [
    { url: `/admin/insights/widget/recommendations?time_frame=${timeFrame}`, id: 'recommendations-widget-container' },
    { url: `/admin/insights/widget/top-opportunities?time_frame=${timeFrame}`, id: 'top-opportunities-body' },
    { url: `/admin/insights/widget/action-queue?time_frame=${timeFrame}`, id: 'action-queue-list' },
    { url: `/admin/insights/widget/coverage-matrix?time_frame=${timeFrame}`, id: 'coverage-matrix-body' },
    { url: `/admin/insights/widget/intent-opportunities?time_frame=${timeFrame}`, id: 'intent-opportunities-list' },
    { url: `/admin/insights/widget/brand-opportunities?time_frame=${timeFrame}`, id: 'brand-opportunities-body' }
  ];

  return Promise.all(
    widgets.map(w => {
      const el = document.getElementById(w.id);
      if (!el) return Promise.resolve();
      return fetch(w.url)
        .then(res => {
          if (!res.ok) throw new Error(`Failed to load ${w.id}`);
          return res.text();
        })
        .then(html => {
          el.innerHTML = html;
        })
        .catch(err => {
          console.error(err);
          if (w.id.endsWith('-body')) {
            el.innerHTML = `<tr><td colspan="10" class="text-center text-danger">⚠️ Failed to load data.</td></tr>`;
          } else {
            el.innerHTML = `<div class="text-danger text-center p-4">⚠️ Failed to load data.</div>`;
          }
        });
    })
  );
}

export function showSpinnerPlaceholders() {
  const spinnerList = getSpinnerHtml("Loading metrics...", "loading-height-sm");
  
  const recGrid = document.getElementById("recommendations-widget-container");
  if (recGrid) recGrid.innerHTML = `<div class="grid-full-width">${spinnerList}</div>`;
  
  const topBody = document.getElementById("top-opportunities-body");
  if (topBody) topBody.innerHTML = `<tr><td colspan="5" class="text-center">${getSpinnerHtml("Prioritizing entities...", "loading-height-xs")}</td></tr>`;
  
  const actionList = document.getElementById("action-queue-list");
  if (actionList) actionList.innerHTML = getSpinnerHtml("Compiling action guidance...", "loading-height-sm");
  
  const coverageBody = document.getElementById("coverage-matrix-body");
  if (coverageBody) coverageBody.innerHTML = `<tr><td colspan="4" class="text-center">${getSpinnerHtml("Assessing category alignment...", "loading-height-xs")}</td></tr>`;
  
  const intentList = document.getElementById("intent-opportunities-list");
  if (intentList) intentList.innerHTML = getSpinnerHtml("Analyzing intent distributions...", "loading-height-sm");
  
  const brandBody = document.getElementById("brand-opportunities-body");
  if (brandBody) brandBody.innerHTML = `<tr><td colspan="4" class="text-center">${getSpinnerHtml("Calculating brand expansion opportunities...", "loading-height-xs")}</td></tr>`;

  const strategyBody = document.getElementById("content-strategy-table-body");
  if (strategyBody) {
    strategyBody.innerHTML = `<tr><td colspan="5" class="text-center">${getSpinnerHtml("Generating content strategies...", "loading-height-xs")}</td></tr>`;
  }

  const mappingBody = document.getElementById("asset-mapping-table-body");
  if (mappingBody) {
    mappingBody.innerHTML = `<tr><td colspan="3" class="text-center">${getSpinnerHtml("Mapping strategy to assets...", "loading-height-xs")}</td></tr>`;
  }

  const publishingContainer = document.getElementById("publishing-plan-grid-container");
  if (publishingContainer) {
    publishingContainer.innerHTML = `<div class="grid-full-width text-center">${getSpinnerHtml("Orchestrating weekly publishing schedule...", "loading-height-xs")}</div>`;
  }

  const evaluationsBody = document.getElementById("feedback-evaluations-body");
  if (evaluationsBody) {
    evaluationsBody.innerHTML = `<tr><td colspan="5" class="text-center">${getSpinnerHtml("Evaluating content metrics...", "loading-height-xs")}</td></tr>`;
  }
  
  const failuresList = document.getElementById("feedback-failures-list");
  if (failuresList) {
    failuresList.innerHTML = getSpinnerHtml("Checking failures...", "loading-height-xs");
  }

  const executionContainer = document.getElementById("execution-plan-grid-container");
  if (executionContainer) {
    executionContainer.innerHTML = `<div class="grid-full-width text-center">${getSpinnerHtml("Preparing autonomous queues...", "loading-height-xs")}</div>`;
  }

  const govContainer = document.getElementById("execution-governance-grid-container");
  if (govContainer) {
    govContainer.innerHTML = `<div class="grid-full-width text-center">${getSpinnerHtml("Loading governance queues...", "loading-height-xs")}</div>`;
  }
}

export function showErrorPlaceholders() {
  const errState = getErrorStateHtml("Unable to load intelligence metrics.");
  
  const recGrid = document.getElementById("recommendations-widget-container");
  if (recGrid) recGrid.innerHTML = `<div class="grid-full-width">${errState}</div>`;
  
  const topBody = document.getElementById("top-opportunities-body");
  if (topBody) topBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">⚠️ Failed to load opportunity rankings.</td></tr>`;
  
  const actionList = document.getElementById("action-queue-list");
  if (actionList) actionList.innerHTML = errState;
  
  const coverageBody = document.getElementById("coverage-matrix-body");
  if (coverageBody) coverageBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">⚠️ Failed to assess coverage gaps.</td></tr>`;
  
  const intentList = document.getElementById("intent-opportunities-list");
  if (intentList) intentList.innerHTML = errState;
  
  const brandBody = document.getElementById("brand-opportunities-body");
  if (brandBody) brandBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">⚠️ Failed to calculate brand opportunities.</td></tr>`;
  
  const strategyBody = document.getElementById("content-strategy-table-body");
  if (strategyBody) {
    strategyBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">⚠️ Failed to generate content strategies.</td></tr>`;
  }

  const mappingBody = document.getElementById("asset-mapping-table-body");
  if (mappingBody) {
    mappingBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">⚠️ Failed to map strategy to assets.</td></tr>`;
  }

  const publishingContainer = document.getElementById("publishing-plan-grid-container");
  if (publishingContainer) {
    publishingContainer.innerHTML = `<div class="grid-full-width text-center text-danger">⚠️ Failed to load publishing calendar.</div>`;
  }

  const evaluationsBody = document.getElementById("feedback-evaluations-body");
  if (evaluationsBody) {
    evaluationsBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">⚠️ Failed to load performance evaluations.</td></tr>`;
  }

  const failuresList = document.getElementById("feedback-failures-list");
  if (failuresList) {
    failuresList.innerHTML = `<p class="text-danger">⚠️ Failed to run failure diagnostics.</p>`;
  }

  const executionContainer = document.getElementById("execution-plan-grid-container");
  if (executionContainer) {
    executionContainer.innerHTML = `<div class="grid-full-width text-center text-danger">⚠️ Failed to prepare autonomous execution plan.</div>`;
  }

  const govContainer = document.getElementById("execution-governance-grid-container");
  if (govContainer) {
    govContainer.innerHTML = `<div class="grid-full-width text-center text-danger">⚠️ Failed to load execution governance.</div>`;
  }
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
}