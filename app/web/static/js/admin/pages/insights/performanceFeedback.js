import { getState } from './state.js';

export function renderContentPerformanceFeedback() {
  const panel = document.getElementById("content-feedback-panel");
  const evaluationsBody = document.getElementById("feedback-evaluations-body");
  const failuresList = document.getElementById("feedback-failures-list");
  const accuracyDiv = document.getElementById("strategy-accuracy-index");
  
  if (!panel || !evaluationsBody || !failuresList || !accuracyDiv) return;
  
  const data = getState();
  const feedbackData = data && data.content_performance_feedback;
  if (!feedbackData || !feedbackData.evaluation_results || feedbackData.evaluation_results.length === 0) {
    panel.style.display = "none";
    return;
  }
  
  panel.style.display = "grid";
  
  // Render Accuracy score
  accuracyDiv.textContent = `${feedbackData.average_accuracy.toFixed(1)}%`;
  
  // Render Evaluations list using string accumulation
  let evaluationsHtml = "";
  feedbackData.evaluation_results.forEach(item => {
    let evalBadgeClass = "badge-secondary";
    if (item.evaluation === "overperforming") evalBadgeClass = "badge-success";
    else if (item.evaluation === "underperforming") evalBadgeClass = "badge-danger";
    
    const platformIcon = item.platform === "youtube" ? "📺" : item.platform === "pinterest" ? "📌" : "📝";
    const titleText = item.title.length > 40 ? item.title.substring(0, 40) + "..." : item.title;
    
    evaluationsHtml += `
      <tr>
        <td>
          <div class="font-bold text-foreground">${platformIcon} ${titleText}</div>
          <div class="asset-mapping-item-meta mt-1">Entity: <strong>${item.entity}</strong> &middot; Intent: <code>${item.predicted_intent}</code></div>
        </td>
        <td class="col-metric">${item.expected_performance.ctr.toFixed(1)}%</td>
        <td class="col-metric font-bold text-foreground">${item.actual_performance.ctr.toFixed(1)}%</td>
        <td>
          <span class="status-badge ${evalBadgeClass}">
            ${item.evaluation}
          </span>
        </td>
        <td class="text-muted">
          ${item.reason}
        </td>
      </tr>
    `;
  });
  evaluationsBody.innerHTML = evaluationsHtml;
  
  // Render Failures list using string accumulation
  const failures = feedbackData.failures_detected || [];
  if (failures.length === 0) {
    failuresList.innerHTML = `
      <div class="text-center text-muted p-4" style="font-style: italic;">
        No performance failures detected. All strategies are performing within thresholds.
      </div>
    `;
  } else {
    let failuresHtml = "";
    failures.forEach(fail => {
      let severityBadge = "badge-secondary";
      if (fail.severity === "high") severityBadge = "badge-danger";
      else if (fail.severity === "medium") severityBadge = "badge-warning";
      
      failuresHtml += `
        <div class="failure-card">
          <div class="failure-header">
            <span class="failure-type">
              ⚠️ ${fail.failure_type.replace('_', ' ')}
            </span>
            <span class="status-badge ${severityBadge}">
              ${fail.severity.toUpperCase()}
            </span>
          </div>
          <div class="failure-title">${fail.title}</div>
          <p class="failure-cause">
            <strong>Cause:</strong> ${fail.root_cause}
          </p>
          <div class="failure-recommendation">
            <strong>Recommendation:</strong> ${fail.recommendation}
          </div>
        </div>
      `;
    });
    failuresList.innerHTML = failuresHtml;
  }
}
