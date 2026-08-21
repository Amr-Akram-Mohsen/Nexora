// app/web/static/js/admin/pages/insights/index.js
import { getSelectedEntity, setSelectedEntity } from './state.js';
import { fetchAndInjectHtml } from './utilities.js';
import { renderContentStrategy } from './contentStrategy.js';
import { renderContentAssetMapping } from './assetMapping.js';
import { renderContentPerformanceFeedback } from './performanceFeedback.js';
import { renderAcquisitionSources } from './acquisitionSources.js';

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
}

export function loadMainWidgets(timeFrame) {
  const promises = [
    fetchAndInjectHtml(`/admin/insights/widget/recommendations?time_frame=${timeFrame}`, 'recommendations-widget-container', 'Loading metrics...'),
    fetchAndInjectHtml(`/admin/insights/widget/top-opportunities?time_frame=${timeFrame}`, 'top-opportunities-table-body', 'Prioritizing entities...', 5),
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
  renderContentPerformanceFeedback();

  const timeframeSelect = document.getElementById("timeframe-select");
  const timeframe = timeframeSelect ? timeframeSelect.value : "7_days";
  renderAcquisitionSources(timeframe);
}
