// app/web/static/js/admin/pages/insights/performanceFeedback.js
import { getState } from './state.js';
import { getFiltered, createTableStateRow } from './utilities.js';

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

  accuracyDiv.textContent = `${feedbackData.average_accuracy.toFixed(1)}%`;

  let evaluationResults = feedbackData.evaluation_results || [];
  if (data && data.selected_entity) {
    evaluationResults = getFiltered(evaluationResults, data.selected_entity, 'entity');
  }

  evaluationsBody.innerHTML = '';
  const frag = document.createDocumentFragment();

  if (evaluationResults.length === 0) {
    frag.appendChild(createTableStateRow(5, `No evaluations matching filter "${data.selected_entity}".`, 'muted'));
  } else {
    evaluationResults.forEach(item => {
      const tr = document.createElement('tr');
      let evalBadgeClass = "badge-secondary";
      if (item.evaluation === "overperforming") evalBadgeClass = "badge-success";
      else if (item.evaluation === "underperforming") evalBadgeClass = "badge-danger";

      const platformIcon = item.platform === "youtube" ? "📺" : item.platform === "pinterest" ? "📌" : "📝";
      const titleText = item.title.length > 40 ? item.title.substring(0, 40) + "..." : item.title;

      tr.innerHTML = `
        <td>
          <div class="font-bold text-foreground">${platformIcon} ${titleText}</div>
          <div class="asset-mapping-item-meta mt-1">Entity: <strong>${item.entity}</strong> &middot; Intent: <code>${item.predicted_intent}</code></div>
        </td>
        <td class="col-metric">${item.expected_performance.ctr.toFixed(1)}%</td>
        <td class="col-metric font-bold text-foreground">${item.actual_performance.ctr.toFixed(1)}%</td>
        <td><span class="status-badge ${evalBadgeClass}">${item.evaluation}</span></td>
        <td class="text-muted">${item.reason}</td>
      `;
      frag.appendChild(tr);
    });
  }
  evaluationsBody.appendChild(frag);

  let failures = feedbackData.failures_detected || [];
  if (data && data.selected_entity) {
    failures = failures.filter(fail => (fail.title && fail.title.toLowerCase().includes(data.selected_entity.toLowerCase())) || (fail.entity && fail.entity.toLowerCase().includes(data.selected_entity.toLowerCase())));
  }

  failuresList.innerHTML = '';
  if (failures.length === 0) {
    const div = document.createElement('div');
    div.className = 'text-center text-muted p-4';
    div.style.fontStyle = 'italic';
    div.textContent = `No performance failures detected matching filter${data.selected_entity ? ` "${data.selected_entity}"` : ""}.`;
    failuresList.appendChild(div);
  } else {
    const frag2 = document.createDocumentFragment();
    failures.forEach(fail => {
      const card = document.createElement('div');
      card.className = 'failure-card';
      let severityBadge = "badge-secondary";
      if (fail.severity === "high") severityBadge = "badge-danger";
      else if (fail.severity === "medium") severityBadge = "badge-warning";
      card.innerHTML = `
        <div class="failure-header">
          <span class="failure-type">⚠️ ${String(fail.failure_type || '').replace('_',' ')}</span>
          <span class="status-badge ${severityBadge}">${fail.severity.toUpperCase()}</span>
        </div>
        <div class="failure-title">${fail.title}</div>
        <p class="failure-cause"><strong>Cause:</strong> ${fail.root_cause}</p>
        <div class="failure-recommendation"><strong>Recommendation:</strong> ${fail.recommendation}</div>
      `;
      frag2.appendChild(card);
    });
    failuresList.appendChild(frag2);
  }
}