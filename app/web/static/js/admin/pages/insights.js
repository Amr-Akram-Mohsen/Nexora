// ==========================================
// DECISION-MAKING INTELLIGENCE DASHBOARD ENGINE
// ==========================================

let globalInsightsData = null;

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

function fetchInsightsData(timeFrame) {
  showSpinnerPlaceholders();

  fetch(`/admin/insights/data?time_frame=${timeFrame}`)
    .then(res => {
      if (!res.ok) throw new Error("Failed to fetch insights data");
      return res.json();
    })
    .then(data => {
      globalInsightsData = data;
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

function fetchStrategyData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/strategy?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch strategy data");
      return res.json();
    })
    .then(data => {
      if (!globalInsightsData) globalInsightsData = {};
      globalInsightsData.content_strategy = data;
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

function fetchAssetMappingData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/assets?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch asset mapping data");
      return res.json();
    })
    .then(data => {
      if (!globalInsightsData) globalInsightsData = {};
      globalInsightsData.content_asset_mapping = data;
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

function fetchPublishingPlanData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/publishing-plan?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch publishing plan");
      return res.json();
    })
    .then(data => {
      if (!globalInsightsData) globalInsightsData = {};
      globalInsightsData.content_publishing_plan = data;
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

function fetchPerformanceFeedbackData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/performance?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch performance feedback");
      return res.json();
    })
    .then(data => {
      if (!globalInsightsData) globalInsightsData = {};
      globalInsightsData.content_performance_feedback = data;
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

function fetchExecutionGovernanceData(timeFrame) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  fetch(`/admin/insights/governance?time_frame=${timeFrame}`, { signal: controller.signal })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error("Failed to fetch execution governance");
      return res.json();
    })
    .then(data => {
      if (!globalInsightsData) globalInsightsData = {};
      globalInsightsData.execution_governance = data;
      renderExecutionGovernance();
      
      // Also render autonomous execution if available inside execution_governance payload
      // (Wait, execution_plan was originally separate, but governance calculates everything. 
      // Let's copy execution_plan calculation to globalInsightsData if available in governance to preserve fallback render)
      if (data && data.execution_plan) {
         globalInsightsData.execution_plan = data.execution_plan;
         renderAutonomousExecution();
      } else {
         // Fallback if cached governance contains raw plan structure
         globalInsightsData.execution_plan = data;
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

function showSpinnerPlaceholders() {
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

function showErrorPlaceholders() {
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

function renderAllWidgets() {
  if (!globalInsightsData) return;

  renderRecommendationPerformance();
  renderRecommendationIntelligence();
  renderTopOpportunities();
  renderActionQueue();
  renderContentCoverageMatrix();
  renderIntentOpportunities();
  renderBrandOpportunities();
}

// (1.5) Recommendation Intelligence Summary
function renderRecommendationIntelligence() {
  const panel = document.getElementById("recommendation-intelligence-panel");
  const metrics = globalInsightsData.recommendation_performance;
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
      ? `<span class="status-badge success font-bold" style="background: rgba(16,185,129,0.1); color: var(--brand-green-dark);">${bench.best_category.name}</span> with <strong>${bench.best_category.ctr.toFixed(2)}%</strong> CTR (+${bench.best_category.deviation.toFixed(2)}% dev)`
      : `<span class="status-badge secondary">N/A</span>`;

    const worstText = bench.worst_category && bench.worst_category.name !== "N/A" 
      ? `<span class="status-badge danger font-bold" style="background: rgba(239,68,68,0.1); color: var(--brand-red);">${bench.worst_category.name}</span> with <strong>${bench.worst_category.ctr.toFixed(2)}%</strong> CTR (${bench.worst_category.deviation.toFixed(2)}% dev)`
      : `<span class="status-badge secondary">N/A</span>`;

    benchmarkDiv.innerHTML = `
      <div style="font-size: var(--text-xs); color: var(--muted-foreground); display: flex; flex-direction: column; gap: 0.5rem;">
        <div>🏆 Best Performing Category: ${bestText}</div>
        <div>⚠️ Worst Performing Category: ${worstText}</div>
        <div style="margin-top: 0.25rem; border-top: 1px solid var(--border); padding-top: 0.25rem;">
          📊 Taxonomy CTR Baseline: <strong>${bench.average_baseline.toFixed(2)}%</strong>
        </div>
      </div>
    `;
  } else {
    benchmarkDiv.innerHTML = `<p class="text-muted text-xs">No benchmark data available.</p>`;
  }

  // 2. Render Quality Scores Breakdown Table
  const scoresTbody = document.getElementById("quality-scores-table-body");
  scoresTbody.innerHTML = "";
  
  const qScores = metrics.quality_scores;
  if (qScores) {
    // A. Render Recommendation Types
    for (const [rtype, data] of Object.entries(qScores.recommendation_types)) {
      const typeLabel = rtype === "related_content" ? "Related Content" 
                      : rtype === "related_product" ? "Related Products" 
                      : "Shop Products";
      scoresTbody.innerHTML += `
        <tr>
          <td><span class="status-badge secondary font-bold" style="padding: 1px 4px; font-size: 10px;">Rec Type</span></td>
          <td><span class="font-bold text-foreground" style="font-size: 11px;">${typeLabel}</span></td>
          <td class="col-metric" style="font-size: 11px;">${data.ctr.toFixed(2)}%</td>
          <td class="col-metric font-bold text-foreground" style="color: #6366f1; font-size: 11px;">${data.quality_score.toFixed(2)}</td>
        </tr>
      `;
    }

    // B. Render Page Types
    for (const [ptype, data] of Object.entries(qScores.page_types)) {
      const pageLabel = ptype === "content" ? "Content Pages" : "Product Pages";
      scoresTbody.innerHTML += `
        <tr>
          <td><span class="status-badge info font-bold" style="padding: 1px 4px; font-size: 10px;">Page Context</span></td>
          <td><span class="font-bold text-foreground" style="font-size: 11px;">${pageLabel}</span></td>
          <td class="col-metric" style="font-size: 11px;">${data.ctr.toFixed(2)}%</td>
          <td class="col-metric font-bold text-foreground" style="color: #10b981; font-size: 11px;">${data.quality_score.toFixed(2)}</td>
        </tr>
      `;
    }

    // C. Render Top 3 Categories by Quality Score
    const sortedCats = Object.entries(qScores.categories).sort((a, b) => b[1].quality_score - a[1].quality_score);
    sortedCats.slice(0, 3).forEach(([catName, data]) => {
      scoresTbody.innerHTML += `
        <tr>
          <td><span class="status-badge purple font-bold" style="padding: 1px 4px; font-size: 10px;">Category</span></td>
          <td><span class="font-bold text-foreground" style="font-size: 11px;">${catName}</span></td>
          <td class="col-metric" style="font-size: 11px;">${data.ctr.toFixed(2)}%</td>
          <td class="col-metric font-bold text-foreground" style="font-size: 11px;">${data.quality_score.toFixed(2)}</td>
        </tr>
      `;
    });
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
    card.className = "insights-opp-card";
    card.style.background = rtype === "related_product" ? "linear-gradient(135deg, rgba(16, 185, 129, 0.02) 0%, rgba(59, 130, 246, 0.02) 100%)" : 
                           rtype === "shop_product" ? "linear-gradient(135deg, rgba(245, 158, 11, 0.02) 0%, rgba(239, 68, 68, 0.02) 100%)" :
                           "linear-gradient(135deg, rgba(99, 102, 241, 0.02) 0%, rgba(168, 85, 247, 0.02) 100%)";
    card.style.border = "1px solid var(--border)";
    card.style.padding = "1rem";
    card.style.position = "relative";
    
    const action = data.action_suggestion;

    card.innerHTML = `
      <span class="opp-tag" style="background-color: transparent; border: none; padding: 0; right: 1rem; top: 1rem; font-size: 11px; position: absolute;">
        CTR: <strong class="status-badge ${badgeClass}" style="padding: 1px 6px; font-size: 11px; border-radius: 4px;">${data.ctr.toFixed(2)}% (${data.classification})</strong>
      </span>
      
      <h4 class="font-bold text-base mb-1" style="font-size: var(--text-base); font-weight: var(--weight-bold); margin-bottom: 0.25rem;">${typeLabel} Module</h4>
      <p style="font-size: var(--text-xs); color: var(--muted-foreground); margin-bottom: 0.5rem; font-style: italic;">
        <strong>Issue:</strong> ${action.issue}
      </p>
      
      <p style="font-size: var(--text-sm); margin-bottom: 0.75rem; color: var(--foreground);">
        <strong>Diagnosis:</strong> ${action.diagnosis}
      </p>

      <div class="opp-action" style="background: var(--card); border: 1px dashed rgba(99, 102, 241, 0.25); display: flex; flex-direction: column; align-items: flex-start; gap: 0.25rem; font-weight: normal; font-size: var(--text-sm); padding: 0.75rem; border-radius: var(--radius-md);">
        <div style="color: var(--foreground); display: flex; align-items: center; gap: 0.25rem; margin-bottom: 0.25rem; font-weight: var(--weight-bold);">
          <span>💡 Recommended Action:</span>
        </div>
        <div style="color: #6366f1; font-weight: var(--weight-bold); margin-bottom: 0.25rem;">
          ${action.recommended_action}
        </div>
        <div style="font-size: var(--text-xs); color: var(--muted-foreground); border-top: 1px solid var(--border); width: 100%; padding-top: 0.25rem; margin-top: 0.25rem;">
          <strong>Impact:</strong> ${action.expected_impact} &middot; Confidence: <strong>${(action.confidence * 100).toFixed(0)}%</strong>
        </div>
      </div>
    `;

    suggestionsContainer.appendChild(card);
  }
}

// (1) Recommendation Performance
function renderRecommendationPerformance() {
  const container = document.getElementById("recommendation-ctr-grid");
  const metrics = globalInsightsData.recommendation_performance;
  if (!metrics) {
    container.innerHTML = getEmptyStateHtml("No recommendation performance tracked.");
    return;
  }

  container.innerHTML = `
    <div class="dashboard-stat-card border">
      <p class="dashboard-stat-label">Overall CTR</p>
      <p class="dashboard-stat-value">${metrics.overall_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Across all recommendation slots</p>
    </div>
    <div class="dashboard-stat-card border">
      <p class="dashboard-stat-label">Related Products CTR</p>
      <p class="dashboard-stat-value">${metrics.related_products_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Clicks on related product listings</p>
    </div>
    <div class="dashboard-stat-card border">
      <p class="dashboard-stat-label">Related Content CTR</p>
      <p class="dashboard-stat-value">${metrics.related_content_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Clicks on suggested articles/guides</p>
    </div>
    <div class="dashboard-stat-card border">
      <p class="dashboard-stat-label">Shop Products CTR</p>
      <p class="dashboard-stat-value">${metrics.shop_products_ctr.toFixed(2)}%</p>
      <p class="dashboard-stat-meta">Clicks on primary shop links</p>
    </div>
  `;
}

// (2) Content Coverage Matrix
function renderContentCoverageMatrix() {
  const tbody = document.getElementById("coverage-matrix-body");
  const items = globalInsightsData.coverage_matrix || [];
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No matrix data available.</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  items.forEach(item => {
    tbody.innerHTML += `
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
}

// (3) Intent Opportunity Analysis
function renderIntentOpportunities() {
  const container = document.getElementById("intent-opportunities-list");
  const items = globalInsightsData.intent_opportunities || [];
  if (items.length === 0) {
    container.innerHTML = getEmptyStateHtml("No intent distribution gaps identified.");
    return;
  }

  container.innerHTML = "";
  items.forEach(item => {
    const div = document.createElement("div");
    div.className = "insights-opp-card";

    let distHtml = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; margin-bottom: 0.75rem;">';
    for (const [intentName, count] of Object.entries(item.distribution)) {
      distHtml += `<span class="status-badge secondary font-normal" style="font-size: 11px; padding: 2px 6px;">${intentName}: <strong>${count}</strong></span>`;
    }
    distHtml += '</div>';

    div.innerHTML = `
      <h3 class="opp-title" style="padding-right: 0;" title="${item.category_name}">${item.category_name}</h3>
      ${distHtml}
      <div class="opp-action">
        <span style="font-size: 16px;">🎯</span>
        <span>Opportunity: <strong>${item.opportunity}</strong></span>
      </div>
    `;
    container.appendChild(div);
  });
}

// (4) Brand Opportunity Analysis
function renderBrandOpportunities() {
  const tbody = document.getElementById("brand-opportunities-body");
  const items = globalInsightsData.brand_opportunities || [];
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No brand opportunities recorded.</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  items.forEach(item => {
    const badgeClass = item.opportunity ? "badge-success" : "badge-secondary";
    const badgeText = item.opportunity ? "🚀 Expansion Opportunity" : "Covered";

    tbody.innerHTML += `
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
}

// (5) Top Opportunities
function renderTopOpportunities() {
  const tbody = document.getElementById("top-opportunities-body");
  const items = globalInsightsData.top_opportunities || [];
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No opportunities ranked yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = "";
  items.forEach((item, index) => {
    const typeBadgeClass = item.type === "Category" ? "info" : "purple";
    tbody.innerHTML += `
      <tr>
        <td><span class="font-bold">${index + 1}</span></td>
        <td><span class="font-bold text-foreground">${item.entity}</span></td>
        <td><span class="status-badge ${typeBadgeClass} font-bold">${item.type}</span></td>
        <td class="col-metric font-bold text-foreground">${item.score.toFixed(2)}</td>
        <td><span class="text-muted">${item.reason}</span></td>
      </tr>
    `;
  });
}

// (6) Insight Actions Queue
function renderActionQueue() {
  const container = document.getElementById("action-queue-list");
  const items = globalInsightsData.action_queue || [];
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
      <span class="opp-tag ${item.priority === 'High' ? 'brand' : 'cat'}" style="background-color: transparent; border: 1px solid var(--border); padding: 0.25rem 0.6rem;">
        Priority: <strong class="status-badge ${priorityBadgeClass}" style="padding: 1px 4px; font-size: 10px;">${item.priority}</strong>
      </span>
      <h3 class="opp-title" style="padding-right: 8rem; white-space: normal; overflow: visible;" title="${item.title}">${item.title}</h3>
      
      <div class="opp-metrics" style="margin-top: 0.5rem; margin-bottom: 0.75rem;">
        <div class="opp-metric-item">Target: <strong>${item.target}</strong></div>
        <div class="opp-metric-item">Type: <strong>${item.type}</strong></div>
        <div class="opp-metric-item">Confidence: <strong>${(item.confidence * 100).toFixed(0)}%</strong></div>
      </div>
      
      <div class="opp-action" style="background: rgba(99, 102, 241, 0.05); border-color: rgba(99, 102, 241, 0.15);">
        <span style="font-size: 16px;">💡</span>
        <span>Impact: <strong>${item.impact}</strong></span>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderContentStrategy() {
  const panel = document.getElementById("content-strategy-panel");
  const tbody = document.getElementById("content-strategy-table-body");
  const items = globalInsightsData.content_strategy || [];
  
  if (!panel || !tbody) return;
  if (items.length === 0) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";
  tbody.innerHTML = "";
  
  items.forEach(item => {
    const ytList = item.youtube.map(title => `<li style="margin-bottom: 0.5rem; line-height: 1.4;">📺 <strong>${title}</strong></li>`).join("");
    const pinList = item.pinterest.map(title => `<li style="margin-bottom: 0.5rem; line-height: 1.4;">📌 <strong>${title}</strong></li>`).join("");
    const blogList = item.blog.map(title => `<li style="margin-bottom: 0.5rem; line-height: 1.4;">📝 <strong>${title}</strong></li>`).join("");
    
    tbody.innerHTML += `
      <tr>
        <td style="vertical-align: top; text-align: center; padding: 1rem;"><span class="font-bold text-lg text-indigo-500" style="font-size: 1.25rem; font-weight: var(--weight-bold); color: #6366f1;">#${item.priority_rank}</span></td>
        <td style="vertical-align: top; min-width: 150px; padding: 1rem;">
          <div class="font-bold text-foreground" style="font-size: var(--text-base); font-weight: var(--weight-bold); color: var(--foreground);">${item.entity}</div>
          <span class="status-badge ${item.type === 'category' ? 'info' : 'purple'}" style="margin-top: 0.25rem; font-size: 10px; font-weight: var(--weight-bold);">${item.type.toUpperCase()}</span>
          <div style="font-size: 11px; color: var(--muted-foreground); margin-top: 0.5rem; font-style: italic; white-space: normal; line-height: 1.3;">
            ${item.reasoning || ''}
          </div>
        </td>
        <td style="vertical-align: top; white-space: normal; padding: 1rem;">
          <ul style="list-style: none; padding-left: 0; margin: 0; font-size: var(--text-sm);">
            ${ytList}
          </ul>
        </td>
        <td style="vertical-align: top; white-space: normal; padding: 1rem;">
          <ul style="list-style: none; padding-left: 0; margin: 0; font-size: var(--text-sm);">
            ${pinList}
          </ul>
        </td>
        <td style="vertical-align: top; white-space: normal; padding: 1rem;">
          <ul style="list-style: none; padding-left: 0; margin: 0; font-size: var(--text-sm);">
            ${blogList}
          </ul>
        </td>
      </tr>
    `;
  });
}

function renderContentAssetMapping() {
  const panel = document.getElementById("content-asset-mapping-panel");
  const tbody = document.getElementById("asset-mapping-table-body");
  const items = globalInsightsData.content_asset_mapping || [];
  
  if (!panel || !tbody) return;
  if (items.length === 0) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";
  tbody.innerHTML = "";
  
  items.forEach(item => {
    // 1. Compile existing assets HTML
    let existingHtml = '<ul style="list-style: none; padding-left: 0; margin: 0; font-size: 13px; display: flex; flex-direction: column; gap: 0.5rem;">';
    if (item.existing_assets && item.existing_assets.length > 0) {
      item.existing_assets.forEach(asset => {
        let actionBadge = "";
        if (asset.action === "reuse") {
          actionBadge = '<span class="status-badge success font-bold" style="padding: 1px 4px; font-size: 10px; background: rgba(16,185,129,0.1); color: var(--brand-green-dark);">REUSE</span>';
        } else if (asset.action === "update") {
          actionBadge = '<span class="status-badge warning font-bold" style="padding: 1px 4px; font-size: 10px;">UPDATE</span>';
        } else if (asset.action === "repurpose") {
          actionBadge = '<span class="status-badge info font-bold" style="padding: 1px 4px; font-size: 10px; background: rgba(59, 130, 246, 0.1); color: #3b82f6;">REPURPOSE</span>';
        }
        
        const typeIcon = asset.type === "video" ? "🎥" : asset.type === "article" ? "📄" : "🛍️";
        existingHtml += `
          <li style="border-bottom: 1px dashed var(--border); padding-bottom: 0.35rem; white-space: normal;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-sm); flex-wrap: wrap; margin-bottom: 0.25rem;">
              <div style="font-weight: var(--weight-bold);">${typeIcon} ${asset.title}</div>
              <div>${actionBadge}</div>
            </div>
            <div style="font-size: 11px; color: var(--muted-foreground);">Relevance Match: ${(asset.relevance_score * 100).toFixed(0)}%</div>
          </li>
        `;
      });
    } else {
      existingHtml += '<li class="text-muted" style="font-style: italic;">No matching assets found in database.</li>';
    }
    existingHtml += '</ul>';
    
    // 2. Compile missing assets HTML
    let missingHtml = '<ul style="list-style: none; padding-left: 0; margin: 0; font-size: 13px; display: flex; flex-direction: column; gap: 0.5rem;">';
    if (item.missing_assets && item.missing_assets.length > 0) {
      item.missing_assets.forEach(gap => {
        const typeBadge = `<span class="status-badge secondary" style="font-size: 9px; font-weight: bold; background: rgba(168, 85, 247, 0.1); color: #a855f7;">${gap.content_type.toUpperCase()}</span>`;
        const priorityBadge = gap.priority === "high" 
          ? '<span class="status-badge danger font-bold" style="padding: 1px 4px; font-size: 9px; background: rgba(239, 68, 68, 0.1); color: var(--brand-red);">CREATE (HIGH)</span>'
          : gap.priority === "medium"
            ? '<span class="status-badge warning font-bold" style="padding: 1px 4px; font-size: 9px;">CREATE (MED)</span>'
            : '<span class="status-badge secondary font-bold" style="padding: 1px 4px; font-size: 9px;">CREATE (LOW)</span>';
            
        missingHtml += `
          <li style="border-bottom: 1px dashed var(--border); padding-bottom: 0.35rem; white-space: normal;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-sm); flex-wrap: wrap; margin-bottom: 0.25rem;">
              <div style="font-weight: var(--weight-bold);">${typeBadge} ${gap.missing_topic}</div>
              <div>${priorityBadge}</div>
            </div>
          </li>
        `;
      });
    } else {
      missingHtml += '<li class="text-muted" style="font-style: italic;">No content gaps identified.</li>';
    }
    missingHtml += '</ul>';
    
    tbody.innerHTML += `
      <tr>
        <td style="vertical-align: top; min-width: 140px; padding: 1rem;">
          <div class="font-bold text-foreground" style="font-size: var(--text-base); font-weight: var(--weight-bold); color: var(--foreground);">${item.entity}</div>
          <span class="status-badge ${item.type === 'category' ? 'info' : 'purple'}" style="margin-top: 0.25rem; font-size: 10px; font-weight: var(--weight-bold);">${item.type.toUpperCase()}</span>
          <div style="font-size: 11px; color: var(--muted-foreground); margin-top: 0.5rem; font-style: italic;">
            Score: <strong>${item.opportunity_score.toFixed(2)}</strong>
          </div>
        </td>
        <td style="vertical-align: top; white-space: normal; padding: 1rem;">
          ${existingHtml}
        </td>
        <td style="vertical-align: top; white-space: normal; padding: 1rem;">
          ${missingHtml}
        </td>
      </tr>
    `;
  });
}

function renderContentPublishingPlan() {
  const panel = document.getElementById("content-publishing-plan-panel");
  const gridContainer = document.getElementById("publishing-plan-grid-container");
  const summaryBar = document.getElementById("publishing-plan-summary");
  
  if (!panel || !gridContainer || !summaryBar) return;
  
  const planData = globalInsightsData.content_publishing_plan;
  if (!planData || !planData.weekly_plan || planData.weekly_plan.length === 0) {
    panel.style.display = "none";
    return;
  }
  
  panel.style.display = "block";
  gridContainer.innerHTML = "";
  
  // Calculate summary metrics across all weekly tasks
  let totalTasks = 0;
  let platformCounts = { youtube: 0, pinterest: 0, blog: 0 };
  let actionCounts = { reuse: 0, update: 0, create: 0, postpone: 0 };
  
  planData.weekly_plan.forEach(weekData => {
    (weekData.tasks || []).forEach(task => {
      totalTasks++;
      if (platformCounts[task.platform] !== undefined) {
        platformCounts[task.platform]++;
      }
      if (actionCounts[task.action] !== undefined) {
        actionCounts[task.action]++;
      }
    });
  });
  
  // Render Summary Metrics Bar
  summaryBar.innerHTML = `
    <div class="publishing-summary-item">🎯 Total Scheduled: <strong>${totalTasks}</strong></div>
    <div class="publishing-summary-item">📺 Platform Mix: <strong>YouTube: ${platformCounts.youtube}</strong> &middot; <strong>Pinterest: ${platformCounts.pinterest}</strong> &middot; <strong>Blog: ${platformCounts.blog}</strong></div>
    <div class="publishing-summary-item">🛠️ Actions: <strong>Create: ${actionCounts.create}</strong> &middot; <strong>Update: ${actionCounts.update}</strong> &middot; <strong>Reuse: ${actionCounts.reuse}</strong> &middot; <strong>Postpone: ${actionCounts.postpone}</strong></div>
  `;
  
  // Render Columns
  planData.weekly_plan.forEach(weekData => {
    const column = document.createElement("div");
    column.className = "overview-panel";
    column.style.display = "flex";
    column.style.flexDirection = "column";
    column.style.minHeight = "200px";
    column.style.background = "var(--card)";
    column.style.border = "1px solid var(--border)";
    column.style.borderRadius = "var(--radius-lg)";
    
    // Header colors based on Week
    let headerStyle = "background: rgba(99, 102, 241, 0.05); color: var(--foreground);";
    let statusLabel = "";
    if (weekData.week === "Week 1") {
      headerStyle = "background: rgba(239, 68, 68, 0.05); border-bottom: 2px solid var(--brand-red); padding: 1rem; display: flex; justify-content: space-between; align-items: center;";
      statusLabel = '<span class="status-badge danger font-bold" style="font-size: 10px; background: rgba(239,68,68,0.1); color: var(--brand-red);">HIGH URGENCY</span>';
    } else if (weekData.week === "Week 2") {
      headerStyle = "background: rgba(245, 158, 11, 0.05); border-bottom: 2px solid var(--brand-orange); padding: 1rem; display: flex; justify-content: space-between; align-items: center;";
      statusLabel = '<span class="status-badge warning font-bold" style="font-size: 10px;">MEDIUM</span>';
    } else {
      headerStyle = "background: var(--secondary); border-bottom: 2px solid var(--muted-foreground); padding: 1rem; display: flex; justify-content: space-between; align-items: center;";
      statusLabel = '<span class="status-badge secondary font-bold" style="font-size: 10px;">LOW PRIORITY</span>';
    }
    
    let taskCardsHtml = "";
    const tasks = weekData.tasks || [];
    if (tasks.length === 0) {
      taskCardsHtml = `
        <div class="text-center text-muted p-4" style="font-style: italic; font-size: var(--text-xs); margin-top: auto; margin-bottom: auto;">
          No tasks scheduled for this period.
        </div>
      `;
    } else {
      tasks.forEach(task => {
        let actionBadgeClass = "badge-secondary";
        if (task.action === "create") actionBadgeClass = "badge-danger";
        else if (task.action === "update") actionBadgeClass = "badge-warning";
        else if (task.action === "reuse") actionBadgeClass = "badge-success";
        
        const platformIcon = task.platform === "youtube" ? "📺" : task.platform === "pinterest" ? "📌" : "📝";
        const platformName = task.platform.toUpperCase();
        
        taskCardsHtml += `
          <div class="insights-opp-card" style="border: 1px solid var(--border); padding: 0.875rem; background: var(--card); border-radius: var(--radius-md); margin-bottom: 0.75rem; position: relative;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.25rem;">
              <span style="font-size: 11px; font-weight: bold; color: var(--muted-foreground); display: flex; align-items: center; gap: 4px;">
                <span>${platformIcon}</span> ${platformName}
              </span>
              <span class="status-badge ${actionBadgeClass}" style="font-size: 10px; font-weight: bold; text-transform: uppercase; padding: 1px 6px; border-radius: 4px;">
                ${task.action}
              </span>
            </div>
            
            <h4 style="font-size: 14px; font-weight: bold; margin: 0 0 0.25rem 0; color: var(--foreground);">${task.entity}</h4>
            <p style="font-size: 11px; color: var(--muted-foreground); margin: 0 0 0.5rem 0;">Type: <strong>${task.content_type}</strong> &middot; Source: <code>${task.source}</code></p>
            
            <div style="font-size: 12px; line-height: 1.3; color: var(--foreground); padding: 0.5rem; background: rgba(99, 102, 241, 0.02); border-left: 3px solid #6366f1; border-radius: 2px;">
              ${task.reason}
            </div>
          </div>
        `;
      });
    }
    
    column.innerHTML = `
      <div class="publishing-column-header" style="${headerStyle}">
        <div class="font-bold text-sm" style="font-size: var(--text-sm); font-weight: var(--weight-bold);">${weekData.week}</div>
        <div>${statusLabel}</div>
      </div>
      <div style="padding: 1rem; overflow-y: auto; flex: 1; max-height: 480px;">
        ${taskCardsHtml}
      </div>
    `;
    gridContainer.appendChild(column);
  });
}

function renderContentPerformanceFeedback() {
  const panel = document.getElementById("content-feedback-panel");
  const evaluationsBody = document.getElementById("feedback-evaluations-body");
  const failuresList = document.getElementById("feedback-failures-list");
  const accuracyDiv = document.getElementById("strategy-accuracy-index");
  
  if (!panel || !evaluationsBody || !failuresList || !accuracyDiv) return;
  
  const feedbackData = globalInsightsData.content_performance_feedback;
  if (!feedbackData || !feedbackData.evaluation_results || feedbackData.evaluation_results.length === 0) {
    panel.style.display = "none";
    return;
  }
  
  panel.style.display = "grid";
  evaluationsBody.innerHTML = "";
  failuresList.innerHTML = "";
  
  // Render Accuracy score
  accuracyDiv.textContent = `${feedbackData.average_accuracy.toFixed(1)}%`;
  
  // Render Evaluations list
  feedbackData.evaluation_results.forEach(item => {
    let evalBadgeClass = "badge-secondary";
    if (item.evaluation === "overperforming") evalBadgeClass = "badge-success";
    else if (item.evaluation === "underperforming") evalBadgeClass = "badge-danger";
    
    const platformIcon = item.platform === "youtube" ? "📺" : item.platform === "pinterest" ? "📌" : "📝";
    const titleText = item.title.length > 40 ? item.title.substring(0, 40) + "..." : item.title;
    
    evaluationsBody.innerHTML += `
      <tr>
        <td style="white-space: normal; padding: 0.75rem;">
          <div style="font-weight: bold; color: var(--foreground);">${platformIcon} ${titleText}</div>
          <div style="font-size: 10px; color: var(--muted-foreground); margin-top: 0.15rem;">Entity: <strong>${item.entity}</strong> &middot; Intent: <code>${item.predicted_intent}</code></div>
        </td>
        <td class="col-metric" style="vertical-align: middle;">${item.expected_performance.ctr.toFixed(1)}%</td>
        <td class="col-metric" style="vertical-align: middle; font-weight: bold; color: var(--foreground);">${item.actual_performance.ctr.toFixed(1)}%</td>
        <td style="vertical-align: middle;">
          <span class="status-badge ${evalBadgeClass}" style="font-size: 10px; font-weight: bold; text-transform: uppercase; padding: 1px 6px; border-radius: 4px;">
            ${item.evaluation}
          </span>
        </td>
        <td style="white-space: normal; vertical-align: middle; color: var(--muted-foreground); line-height: 1.3;">
          ${item.reason}
        </td>
      </tr>
    `;
  });
  
  // Render Failures list
  const failures = feedbackData.failures_detected || [];
  if (failures.length === 0) {
    failuresList.innerHTML = `
      <div class="text-center text-muted p-4" style="font-style: italic; font-size: var(--text-xs);">
        No performance failures detected. All strategies are performing within thresholds.
      </div>
    `;
  } else {
    failures.forEach(fail => {
      let severityBadge = "badge-secondary";
      if (fail.severity === "high") severityBadge = "badge-danger";
      else if (fail.severity === "medium") severityBadge = "badge-warning";
      
      failuresList.innerHTML += `
        <div class="insights-opp-card" style="border: 1px solid var(--border); padding: 0.75rem; background: var(--card); border-radius: var(--radius-md); position: relative; width: 100%;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.25rem; flex-wrap: wrap; gap: 0.25rem;">
            <span style="font-size: 11px; font-weight: bold; color: var(--brand-red); text-transform: uppercase;">
              ⚠️ ${fail.failure_type.replace('_', ' ')}
            </span>
            <span class="status-badge ${severityBadge}" style="font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;">
              ${fail.severity.toUpperCase()}
            </span>
          </div>
          <div style="font-weight: bold; font-size: 12px; margin-bottom: 0.25rem; color: var(--foreground);">${fail.title}</div>
          <p style="font-size: 11px; color: var(--muted-foreground); margin: 0 0 0.5rem 0; line-height: 1.3;">
            <strong>Cause:</strong> ${fail.root_cause}
          </p>
          <div class="opp-action" style="background: rgba(239, 68, 68, 0.02); border: 1px dashed rgba(239, 68, 68, 0.2); font-size: 11px; padding: 0.5rem; border-radius: var(--radius-md); font-weight: normal; color: var(--foreground); display: block; line-height: 1.3;">
            <strong>Recommendation:</strong> ${fail.recommendation}
          </div>
        </div>
      `;
    });
  }
}

function renderAutonomousExecution() {
  const panel = document.getElementById("autonomous-execution-panel");
  const gridContainer = document.getElementById("execution-plan-grid-container");
  const summaryBar = document.getElementById("execution-plan-summary");
  
  if (!panel || !gridContainer || !summaryBar) return;
  
  const executionData = globalInsightsData.execution_plan;
  if (!executionData) {
    panel.style.display = "none";
    return;
  }
  
  panel.style.display = "block";
  gridContainer.innerHTML = "";
  
  const auto = executionData.auto_execute || [];
  const review = executionData.needs_review || [];
  const blocked = executionData.blocked || [];
  
  // Render Summary Metrics Bar
  summaryBar.innerHTML = `
    <div class="publishing-summary-item">🤖 Auto-Execute Queue: <span class="status-badge success font-bold" style="background: rgba(16,185,129,0.1); color: var(--brand-green-dark);">${auto.length}</span></div>
    <div class="publishing-summary-item">🤔 Needs Review Queue: <span class="status-badge warning font-bold">${review.length}</span></div>
    <div class="publishing-summary-item">❌ Blocked Queue: <span class="status-badge danger font-bold" style="background: rgba(239,68,68,0.1); color: var(--brand-red);">${blocked.length}</span></div>
  `;
  
  const queues = [
    { name: "AUTO EXECUTE", list: auto, color: "rgba(16, 185, 129, 0.05)", border: "var(--brand-green)", status: "AUTO APPROVED" },
    { name: "NEEDS REVIEW", list: review, color: "rgba(245, 158, 11, 0.05)", border: "var(--brand-orange)", status: "PENDING REVIEW" },
    { name: "BLOCKED", list: blocked, color: "rgba(239, 68, 68, 0.05)", border: "var(--brand-red)", status: "SAFETY BLOCKED" }
  ];
  
  queues.forEach(q => {
    const column = document.createElement("div");
    column.className = "overview-panel";
    column.style.display = "flex";
    column.style.flexDirection = "column";
    column.style.minHeight = "200px";
    column.style.background = "var(--card)";
    column.style.border = `1px solid var(--border)`;
    column.style.borderRadius = "var(--radius-lg)";
    
    let headerStyle = `background: ${q.color}; border-bottom: 2px solid ${q.border}; padding: 1rem; display: flex; justify-content: space-between; align-items: center;`;
    
    let taskCardsHtml = "";
    if (q.list.length === 0) {
      taskCardsHtml = `
        <div class="text-center text-muted p-4" style="font-style: italic; font-size: var(--text-xs); margin-top: auto; margin-bottom: auto;">
          No items in this queue.
        </div>
      `;
    } else {
      q.list.forEach(task => {
        let actionBadgeClass = "badge-secondary";
        if (task.action === "create" || task.action === "publish") actionBadgeClass = "badge-danger";
        else if (task.action === "update") actionBadgeClass = "badge-warning";
        else if (task.action === "reuse") actionBadgeClass = "badge-success";
        
        const platformIcon = task.platform === "youtube" ? "📺" : task.platform === "pinterest" ? "📌" : "📝";
        const platformName = task.platform.toUpperCase();
        
        let riskHtml = "";
        if (task.risk_factors && task.risk_factors.length > 0) {
          riskHtml = `<div style="margin-top: 0.5rem; font-size: 11px; color: var(--brand-red); font-weight: bold; line-height: 1.3;">`;
          task.risk_factors.forEach(risk => {
            riskHtml += `<div>⚠️ ${risk}</div>`;
          });
          riskHtml += `</div>`;
        }
        
        let executionLogHtml = "";
        if (task.execution_log) {
          executionLogHtml = `
            <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(16, 185, 129, 0.02); border: 1px dashed rgba(16, 185, 129, 0.2); border-radius: 4px; font-size: 10px; font-family: monospace; line-height: 1.3; color: var(--brand-green-dark);">
              <strong>Status:</strong> ${task.execution_log.status.toUpperCase()}<br/>
              <strong>Sim Published:</strong> <a href="${task.execution_log.published_url}" target="_blank" style="text-decoration: underline; color: #10b981;">${task.execution_log.published_url}</a><br/>
              <strong>Timestamp:</strong> ${task.execution_log.timestamp}
            </div>
          `;
        }
        
        taskCardsHtml += `
          <div class="insights-opp-card" style="border: 1px solid var(--border); padding: 0.875rem; background: var(--card); border-radius: var(--radius-md); margin-bottom: 0.75rem; position: relative;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.25rem;">
              <span style="font-size: 11px; font-weight: bold; color: var(--muted-foreground); display: flex; align-items: center; gap: 4px;">
                <span>${platformIcon}</span> ${platformName}
              </span>
              <span class="status-badge ${actionBadgeClass}" style="font-size: 10px; font-weight: bold; text-transform: uppercase; padding: 1px 6px; border-radius: 4px;">
                ${task.action}
              </span>
            </div>
            
            <h4 style="font-size: 14px; font-weight: bold; margin: 0 0 0.25rem 0; color: var(--foreground);">${task.entity}</h4>
            <p style="font-size: 11px; color: var(--muted-foreground); margin: 0 0 0.5rem 0;">Confidence Score: <strong style="color: #6366f1;">${(task.confidence_score * 100).toFixed(0)}%</strong></p>
            
            <div style="font-size: 12px; line-height: 1.3; color: var(--foreground); padding: 0.5rem; background: rgba(99, 102, 241, 0.02); border-left: 3px solid #6366f1; border-radius: 2px;">
              ${task.reason}
            </div>
            
            ${riskHtml}
            ${executionLogHtml}
          </div>
        `;
      });
    }
    
    column.innerHTML = `
      <div class="publishing-column-header" style="${headerStyle}">
        <div class="font-bold text-sm" style="font-size: var(--text-sm); font-weight: var(--weight-bold);">${q.name}</div>
        <div><span class="status-badge" style="font-size: 10px; font-weight: bold; background: ${q.color}; border: 1px solid ${q.border};">${q.status}</span></div>
      </div>
      <div style="padding: 1rem; overflow-y: auto; flex: 1; max-height: 480px;">
        ${taskCardsHtml}
      </div>
    `;
  });
}


function renderExecutionGovernance() {
  const panel = document.getElementById("execution-governance-panel");
  const gridContainer = document.getElementById("execution-governance-grid-container");
  const summaryBar = document.getElementById("execution-governance-summary");
  
  if (!panel || !gridContainer || !summaryBar) return;
  
  const govData = globalInsightsData.execution_governance;
  if (!govData) {
    panel.style.display = "none";
    return;
  }
  
  panel.style.display = "block";
  gridContainer.innerHTML = "";
  
  const queued = govData.queued_tasks || [];
  const approved = govData.approved_tasks || [];
  const blocked = govData.blocked_tasks || [];
  
  // Render Summary Metrics Bar
  summaryBar.innerHTML = `
    <div class="publishing-summary-item">🛡️ Governance Mode: <span class="status-badge info font-bold" style="background: rgba(59,130,246,0.1); color: #3b82f6;">${govData.mode}</span></div>
    <div class="publishing-summary-item">✅ Safe / Executed: <span class="status-badge success font-bold" style="background: rgba(16,185,129,0.1); color: var(--brand-green-dark);">${approved.length}</span></div>
    <div class="publishing-summary-item">⏳ Needs Approval: <span class="status-badge warning font-bold">${queued.length}</span></div>
    <div class="publishing-summary-item">❌ Blocked Tasks: <span class="status-badge danger font-bold" style="background: rgba(239,68,68,0.1); color: var(--brand-red);">${blocked.length}</span></div>
  `;
  
  const queues = [
    { name: "SAFE / EXECUTED", list: approved, color: "rgba(16, 185, 129, 0.05)", border: "var(--brand-green)", status: "SAFE FOR PRODUCTION" },
    { name: "NEEDS APPROVAL", list: queued, color: "rgba(245, 158, 11, 0.05)", border: "var(--brand-orange)", status: "APPROVAL GATED" },
    { name: "BLOCKED", list: blocked, color: "rgba(239, 68, 68, 0.05)", border: "var(--brand-red)", status: "SAFETY RESTRICTED" }
  ];
  
  queues.forEach(q => {
    const column = document.createElement("div");
    column.className = "overview-panel";
    column.style.display = "flex";
    column.style.flexDirection = "column";
    column.style.minHeight = "200px";
    column.style.background = "var(--card)";
    column.style.border = `1px solid var(--border)`;
    column.style.borderRadius = "var(--radius-lg)";
    
    let headerStyle = `background: ${q.color}; border-bottom: 2px solid ${q.border}; padding: 1rem; display: flex; justify-content: space-between; align-items: center;`;
    
    let taskCardsHtml = "";
    if (q.list.length === 0) {
      taskCardsHtml = `
        <div class="text-center text-muted p-4" style="font-style: italic; font-size: var(--text-xs); margin-top: auto; margin-bottom: auto;">
          No tasks in this queue.
        </div>
      `;
    } else {
      q.list.forEach(task => {
        let actionBadgeClass = "badge-secondary";
        if (task.action === "create" || task.action === "publish") actionBadgeClass = "badge-danger";
        else if (task.action === "update") actionBadgeClass = "badge-warning";
        else if (task.action === "reuse") actionBadgeClass = "badge-success";
        
        const platformIcon = task.platform === "youtube" ? "📺" : task.platform === "pinterest" ? "📌" : "📝";
        const platformName = task.platform.toUpperCase();
        
        let riskBadgeClass = "badge-success";
        if (task.risk_level === "HIGH") riskBadgeClass = "badge-danger";
        else if (task.risk_level === "MEDIUM") riskBadgeClass = "badge-warning";
        
        let riskReasonsHtml = "";
        if (task.risk_reasons && task.risk_reasons.length > 0) {
          riskReasonsHtml = `<div style="margin-top: 0.5rem; font-size: 11px; color: var(--brand-red); font-weight: bold; line-height: 1.3;">`;
          task.risk_reasons.forEach(reason => {
            riskReasonsHtml += `<div>⚠️ ${reason}</div>`;
          });
          riskReasonsHtml += `</div>`;
        }
        
        let executionLogHtml = "";
        if (task.execution_log) {
          executionLogHtml = `
            <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(16, 185, 129, 0.02); border: 1px dashed rgba(16, 185, 129, 0.2); border-radius: 4px; font-size: 10px; font-family: monospace; line-height: 1.3; color: var(--brand-green-dark);">
              <strong>Status:</strong> ${task.execution_log.status.toUpperCase()}<br/>
              <strong>Sim Published:</strong> <a href="${task.execution_log.mock_url}" target="_blank" style="text-decoration: underline; color: #10b981;">${task.execution_log.mock_url}</a>
            </div>
          `;
        }
        
        taskCardsHtml += `
          <div class="insights-opp-card" style="border: 1px solid var(--border); padding: 0.875rem; background: var(--card); border-radius: var(--radius-md); margin-bottom: 0.75rem; position: relative;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.25rem;">
              <span style="font-size: 11px; font-weight: bold; color: var(--muted-foreground); display: flex; align-items: center; gap: 4px;">
                <span>${platformIcon}</span> ${platformName}
              </span>
              <span class="status-badge ${actionBadgeClass}" style="font-size: 10px; font-weight: bold; text-transform: uppercase; padding: 1px 6px; border-radius: 4px;">
                ${task.action}
              </span>
            </div>
            
            <h4 style="font-size: 14px; font-weight: bold; margin: 0 0 0.25rem 0; color: var(--foreground);">${task.entity}</h4>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
              <span style="font-size: 11px; color: var(--muted-foreground);">Decision Score: <strong style="color: #6366f1;">${(task.decision_score * 100).toFixed(0)}%</strong></span>
              <span class="status-badge ${riskBadgeClass}" style="font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;">
                ${task.risk_level} RISK
              </span>
            </div>
            
            <div style="font-size: 11px; color: var(--muted-foreground); margin-bottom: 0.5rem; display: flex; justify-content: space-between;">
              <span>Timeline: <strong>${task.scheduled_time}</strong></span>
              <span>Status: <strong style="text-transform: uppercase;">${task.status}</strong></span>
            </div>
            
            ${riskReasonsHtml}
            ${executionLogHtml}
          </div>
        `;
      });
    }
    
    column.innerHTML = `
      <div class="publishing-column-header" style="${headerStyle}">
        <div class="font-bold text-sm" style="font-size: var(--text-sm); font-weight: var(--weight-bold);">${q.name}</div>
        <div><span class="status-badge" style="font-size: 10px; font-weight: bold; background: ${q.color}; border: 1px solid ${q.border};">${q.status}</span></div>
      </div>
      <div style="padding: 1rem; overflow-y: auto; flex: 1; max-height: 480px;">
        ${taskCardsHtml}
      </div>
    `;
    gridContainer.appendChild(column);
  });
}



