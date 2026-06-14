import { getState } from './state.js';
import { fetchInsightsData } from './api.js';
import { getSpinnerHtml, getErrorStateHtml, getEmptyStateHtml } from './utilities.js';

document.addEventListener("DOMContentLoaded", () => {
  initInsights();
});

function initInsights() {
  // Setup Timeframe selector listener
  const timeframeSelect = document.getElementById("timeframe-select");
  if (timeframeSelect) {
    timeframeSelect.addEventListener("change", () => {
      fetchInsightsData(timeframeSelect.value);
    });
  }

  // Setup Refresh button listener
  const refreshBtn = document.getElementById("refresh-insights-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      const timeframe = timeframeSelect ? timeframeSelect.value : "7_days";
      fetchInsightsData(timeframe);
    });
  }

  // Initial data load (default 7 days)
  fetchInsightsData("7_days");
}

export function showSpinnerPlaceholders() {
  const spinnerList = getSpinnerHtml("Loading metrics...", "loading-height-sm");
  document.getElementById("recommendation-ctr-grid").innerHTML = `<div class="grid-full-width">${spinnerList}</div>`;
  document.getElementById("top-opportunities-body").innerHTML = `<tr><td colspan="5" class="text-center">${getSpinnerHtml("Prioritizing entities...", "loading-height-xs")}</td></tr>`;
  document.getElementById("action-queue-list").innerHTML = getSpinnerHtml("Compiling action guidance...", "loading-height-sm");
  document.getElementById("coverage-matrix-body").innerHTML = `<tr><td colspan="4" class="text-center">${getSpinnerHtml("Assessing category alignment...", "loading-height-xs")}</td></tr>`;
  document.getElementById("intent-opportunities-list").innerHTML = getSpinnerHtml("Analyzing intent distributions...", "loading-height-sm");
  document.getElementById("brand-opportunities-body").innerHTML = `<tr><td colspan="4" class="text-center">${getSpinnerHtml("Calculating brand expansion opportunities...", "loading-height-xs")}</td></tr>`;
  
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
  document.getElementById("recommendation-ctr-grid").innerHTML = `<div class="grid-full-width">${errState}</div>`;
  document.getElementById("top-opportunities-body").innerHTML = `<tr><td colspan="5" class="text-center text-danger">⚠️ Failed to load opportunity rankings.</td></tr>`;
  document.getElementById("action-queue-list").innerHTML = errState;
  document.getElementById("coverage-matrix-body").innerHTML = `<tr><td colspan="4" class="text-center text-danger">⚠️ Failed to assess coverage gaps.</td></tr>`;
  document.getElementById("intent-opportunities-list").innerHTML = errState;
  document.getElementById("brand-opportunities-body").innerHTML = `<tr><td colspan="4" class="text-center text-danger">⚠️ Failed to calculate brand opportunities.</td></tr>`;
  
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

export function renderAllWidgets() {
  const data = getState();
  if (!data) return;

  renderRecommendationPerformance();
  renderRecommendationIntelligence();
  renderTopOpportunities();
  renderActionQueue();
  renderContentCoverageMatrix();
  renderIntentOpportunities();
  renderBrandOpportunities();
}

// (1.5) Recommendation Intelligence Summary
export function renderRecommendationIntelligence() {
  const panel = document.getElementById("recommendation-intelligence-panel");
  const data = getState();
  const metrics = data ? data.recommendation_performance : null;
  if (!panel) return;
  if (!metrics || !metrics.diagnoses) {
    panel.style.display = "none";
    return;
  }
  
  panel.style.display = "grid";

  // 1. Render Cross-Category Benchmarks
  const benchmarkDiv = document.getElementById("category-benchmark-summary");
  const bench = metrics.benchmarking;
  if (bench) {
    const bestText = bench.best_category && bench.best_category.name !== "N/A" 
      ? `<span class="status-badge badge-success font-bold">${bench.best_category.name}</span> with <strong>${bench.best_category.ctr.toFixed(2)}%</strong> CTR (+${bench.best_category.deviation.toFixed(2)}% dev)`
      : `<span class="status-badge secondary">N/A</span>`;

    const worstText = bench.worst_category && bench.worst_category.name !== "N/A" 
      ? `<span class="status-badge badge-danger font-bold">${bench.worst_category.name}</span> with <strong>${bench.worst_category.ctr.toFixed(2)}%</strong> CTR (${bench.worst_category.deviation.toFixed(2)}% dev)`
      : `<span class="status-badge secondary">N/A</span>`;

    benchmarkDiv.innerHTML = `
      <div class="benchmark-text-item">
        <div>🏆 Best Performing Category: ${bestText}</div>
        <div>⚠️ Worst Performing Category: ${worstText}</div>
        <div class="benchmark-divider">
          📊 Taxonomy CTR Baseline: <strong>${bench.average_baseline.toFixed(2)}%</strong>
        </div>
      </div>
    `;
  } else {
    benchmarkDiv.innerHTML = `<p class="text-muted text-xs">No benchmark data available.</p>`;
  }

  // 2. Render Quality Scores Breakdown Table
  const scoresTbody = document.getElementById("quality-scores-table-body");
  
  const qScores = metrics.quality_scores;
  if (qScores) {
    let scoresHtml = "";
    // A. Render Recommendation Types
    for (const [rtype, data] of Object.entries(qScores.recommendation_types)) {
      const typeLabel = rtype === "related_content" ? "Related Content" 
                      : rtype === "related_product" ? "Related Products" 
                      : "Shop Products";
      scoresHtml += `
        <tr>
          <td><span class="status-badge secondary font-bold badge-type-compact">Rec Type</span></td>
          <td><span class="font-bold text-foreground text-sm">${typeLabel}</span></td>
          <td class="col-metric text-xs">${data.ctr.toFixed(2)}%</td>
          <td class="col-metric font-bold text-brand-blue text-xs">${data.quality_score.toFixed(2)}</td>
        </tr>
      `;
    }

    // B. Render Page Types
    for (const [ptype, data] of Object.entries(qScores.page_types)) {
      const pageLabel = ptype === "content" ? "Content Pages" : "Product Pages";
      scoresHtml += `
        <tr>
          <td><span class="status-badge badge-blue font-bold badge-type-compact">Page Context</span></td>
          <td><span class="font-bold text-foreground text-sm">${pageLabel}</span></td>
          <td class="col-metric text-xs">${data.ctr.toFixed(2)}%</td>
          <td class="col-metric font-bold badge-green text-xs">${data.quality_score.toFixed(2)}</td>
        </tr>
      `;
    }

    // C. Render Top 3 Categories by Quality Score
    const sortedCats = Object.entries(qScores.categories).sort((a, b) => b[1].quality_score - a[1].quality_score);
    sortedCats.slice(0, 3).forEach(([catName, data]) => {
      scoresHtml += `
        <tr>
          <td><span class="status-badge badge-purple font-bold badge-type-compact">Category</span></td>
          <td><span class="font-bold text-foreground text-sm">${catName}</span></td>
          <td class="col-metric text-xs">${data.ctr.toFixed(2)}%</td>
          <td class="col-metric font-bold text-xs">${data.quality_score.toFixed(2)}</td>
        </tr>
      `;
    });
    scoresTbody.innerHTML = scoresHtml;
  } else {
    scoresTbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No quality score details.</td></tr>`;
  }

  // 3. Render Action Suggestions list
  const suggestionsContainer = document.getElementById("rec-action-suggestions-list");
  suggestionsContainer.innerHTML = "";

  for (const [rtype, data] of Object.entries(metrics.diagnoses)) {
    const typeLabel = rtype === "related_content" ? "Related Content" 
                    : rtype === "related_product" ? "Related Products" 
                    : "Shop Products";

    let badgeClass = "badge-secondary";
    if (data.classification === "High") badgeClass = "badge-success";
    else if (data.classification === "Medium") badgeClass = "badge-warning";
    else if (data.classification === "Low") badgeClass = "badge-danger";

    const card = document.createElement("div");
    card.className = `rec-action-card ${rtype === 'related_product' ? 'product' : rtype === 'shop_product' ? 'shop' : 'content'}`;
    
    const action = data.action_suggestion;

    card.innerHTML = `
      <span class="opp-tag rec-action-tag-wrap">
        CTR: <strong class="status-badge ${badgeClass}">${data.ctr.toFixed(2)}% (${data.classification})</strong>
      </span>
      
      <h4 class="rec-action-title">${typeLabel} Module</h4>
      <p class="rec-action-issue">
        <strong>Issue:</strong> ${action.issue}
      </p>
      
      <p class="rec-action-diagnosis">
        <strong>Diagnosis:</strong> ${action.diagnosis}
      </p>

      <div class="rec-action-box">
        <div class="rec-action-box-header">
          <span>💡 Recommended Action:</span>
        </div>
        <div class="rec-action-box-recommendation">
          ${action.recommended_action}
        </div>
        <div class="rec-action-box-meta">
          <strong>Impact:</strong> ${action.expected_impact} &middot; Confidence: <strong>${(action.confidence * 100).toFixed(0)}%</strong>
        </div>
      </div>
    `;

    suggestionsContainer.appendChild(card);
  }
}

// (1) Recommendation Performance
export function renderRecommendationPerformance() {
  const container = document.getElementById("recommendation-ctr-grid");
  const data = getState();
  const metrics = data ? data.recommendation_performance : null;
  if (!metrics) {
    container.innerHTML = getEmptyStateHtml("No recommendation performance tracked.");
    return;
  }

  container.innerHTML = `
    <div class="rec-stat-card">
      <p class="dashboard-stat-label">Overall CTR</p>
      <p class="dashboard-stat-value">${metrics.overall_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Across all recommendation slots</p>
    </div>
    <div class="rec-stat-card">
      <p class="dashboard-stat-label">Related Products CTR</p>
      <p class="dashboard-stat-value">${metrics.related_products_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Clicks on related product listings</p>
    </div>
    <div class="rec-stat-card">
      <p class="dashboard-stat-label">Related Content CTR</p>
      <p class="dashboard-stat-value">${metrics.related_content_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Clicks on suggested articles/guides</p>
    </div>
    <div class="rec-stat-card">
      <p class="dashboard-stat-label">Shop Products CTR</p>
      <p class="dashboard-stat-value">${metrics.shop_products_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Clicks on primary shop links</p>
    </div>
  `;
}

// (2) Content Coverage Matrix
export function renderContentCoverageMatrix() {
  const tbody = document.getElementById("coverage-matrix-body");
  const data = getState();
  const items = (data && data.coverage_matrix) || [];
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No matrix data available.</td></tr>`;
    return;
  }

  let html = "";
  items.forEach(item => {
    html += `
      <tr>
        <td class="font-bold text-foreground">${item.name}</td>
        <td class="col-metric"><span class="status-badge info font-bold">${item.demand}</span></td>
        <td class="col-metric"><span class="status-badge purple font-bold">${item.coverage}</span></td>
        <td>
          <span class="status-badge ${item.gap_class}">${item.gap_score}</span>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

// (3) Intent Opportunity Analysis
export function renderIntentOpportunities() {
  const container = document.getElementById("intent-opportunities-list");
  const data = getState();
  const items = (data && data.intent_opportunities) || [];
  if (items.length === 0) {
    container.innerHTML = getEmptyStateHtml("No intent distribution gaps identified.");
    return;
  }

  container.innerHTML = "";
  items.forEach(item => {
    const div = document.createElement("div");
    div.className = "insights-opp-card";

    let distHtml = '<div class="opp-metrics">';
    for (const [intentName, count] of Object.entries(item.distribution)) {
      distHtml += `<span class="status-badge secondary font-normal">${intentName}: <strong>${count}</strong></span>`;
    }
    distHtml += '</div>';

    div.innerHTML = `
      <h3 class="opp-title" title="${item.category_name}">${item.category_name}</h3>
      ${distHtml}
      <div class="opp-action">
        <span>🎯</span>
        <span>Opportunity: <strong>${item.opportunity}</strong></span>
      </div>
    `;
    container.appendChild(div);
  });
}

// (4) Brand Opportunity Analysis
export function renderBrandOpportunities() {
  const tbody = document.getElementById("brand-opportunities-body");
  const data = getState();
  const items = (data && data.brand_opportunities) || [];
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No brand opportunities recorded.</td></tr>`;
    return;
  }

  let html = "";
  items.forEach(item => {
    const badgeClass = item.opportunity ? "badge-success" : "badge-secondary";
    const badgeText = item.opportunity ? "🚀 Expansion Opportunity" : "Covered";

    html += `
      <tr>
        <td><span class="font-bold text-foreground">${item.name}</span></td>
        <td class="col-metric">${item.article_volume.toLocaleString()}</td>
        <td class="col-metric">
          <span class="trend-badge neutral font-bold">${item.engagement_level} (${item.engagement.toLocaleString()})</span>
        </td>
        <td>
          <span class="status-badge ${badgeClass}">${badgeText}</span>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

// (5) Top Opportunities
export function renderTopOpportunities() {
  const tbody = document.getElementById("top-opportunities-body");
  const data = getState();
  const items = (data && data.top_opportunities) || [];
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No opportunities ranked yet.</td></tr>`;
    return;
  }

  let html = "";
  items.forEach((item, index) => {
    const typeBadgeClass = item.type === "Category" ? "info" : "purple";
    html += `
      <tr>
        <td><span class="font-bold">${index + 1}</span></td>
        <td><span class="font-bold text-foreground">${item.entity}</span></td>
        <td><span class="status-badge ${typeBadgeClass} font-bold">${item.type}</span></td>
        <td class="col-metric font-bold text-foreground">${item.score.toFixed(2)}</td>
        <td><span class="text-muted">${item.reason}</span></td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

// (6) Insight Actions Queue
export function renderActionQueue() {
  const container = document.getElementById("action-queue-list");
  const data = getState();
  const items = (data && data.action_queue) || [];
  if (items.length === 0) {
    container.innerHTML = getEmptyStateHtml("No immediate actions required.");
    return;
  }

  container.innerHTML = "";
  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "insights-opp-card";

    let priorityBadgeClass = "badge-secondary";
    if (item.priority === "High") priorityBadgeClass = "badge-danger";
    else if (item.priority === "Medium") priorityBadgeClass = "badge-warning";

    card.innerHTML = `
      <span class="opp-tag ${item.priority === 'High' ? 'brand' : 'cat'}">
        Priority: <strong class="status-badge ${priorityBadgeClass}">${item.priority}</strong>
      </span>
      <h3 class="opp-title" title="${item.title}">${item.title}</h3>
      
      <div class="opp-metrics">
        <div class="opp-metric-item">Target: <strong>${item.target}</strong></div>
        <div class="opp-metric-item">Type: <strong>${item.type}</strong></div>
        <div class="opp-metric-item">Confidence: <strong>${(item.confidence * 100).toFixed(0)}%</strong></div>
      </div>
      
      <div class="opp-action">
        <span>💡</span>
        <span>Impact: <strong>${item.impact}</strong></span>
      </div>
    `;
    container.appendChild(card);
  });
}
