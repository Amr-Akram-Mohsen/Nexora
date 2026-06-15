// app/web/static/js/admin/pages/insights/autonomousExecution.js
import { getState } from './state.js';
import { renderKanbanGrid, renderSummaryBar } from './utilities.js';

function makeTaskCard(task) {
  const card = document.createElement('div');
  card.className = 'kanban-task-card';
  const platformIcon = task.platform === 'youtube' ? '📺' : task.platform === 'pinterest' ? '📌' : '📝';
  const actionBadgeClass = task.action === 'create' || task.action === 'publish' ? 'badge-danger' : task.action === 'update' ? 'badge-warning' : 'badge-success';

  let riskHtml = '';
  if (task.risk_factors && task.risk_factors.length > 0) {
    riskHtml = '<div class="kanban-task-risk">';
    task.risk_factors.forEach(r => { riskHtml += `<div>⚠️ ${r}</div>`; });
    riskHtml += '</div>';
  }

  let executionLogHtml = '';
  if (task.execution_log) {
    const url = task.execution_log.published_url || task.execution_log.mock_url || '';
    executionLogHtml = `<div class="kanban-task-log"><strong>Status:</strong> ${String(task.execution_log.status || '').toUpperCase()}<br/>${url ? `<strong>Sim Published:</strong> <a href="${url}" target="_blank">${url}</a><br/>` : ''}<strong>Timestamp:</strong> ${task.execution_log.timestamp || ''}</div>`;
  }

  card.innerHTML = `
    <div class="kanban-task-header">
      <span class="kanban-task-platform">${platformIcon} ${task.platform.toUpperCase()}</span>
      <span class="status-badge ${actionBadgeClass}">${task.action}</span>
    </div>
    <h4 class="kanban-task-title">${task.entity}</h4>
    <p class="kanban-task-meta">Confidence Score: <strong style="color:#6366f1;">${(task.confidence_score * 100).toFixed(0)}%</strong></p>
    <div class="kanban-task-reason">${task.reason}</div>
    ${riskHtml}
    ${executionLogHtml}
  `;
  return card;
}

export function renderAutonomousExecution() {
  const panel = document.getElementById("autonomous-execution-panel");
  const gridContainer = document.getElementById("execution-plan-grid-container");
  const summaryBar = document.getElementById("execution-plan-summary");

  if (!panel || !gridContainer || !summaryBar) return;

  const data = getState();
  const executionData = data && data.execution_plan;
  if (!executionData) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";

  const auto = executionData.auto_execute || [];
  const review = executionData.needs_review || [];
  const blocked = executionData.blocked || [];

  renderSummaryBar(summaryBar, [
    `🤖 Auto-Execute Queue: <span class="status-badge badge-success font-bold">${auto.length}</span>`,
    `🤔 Needs Review Queue: <span class="status-badge badge-warning font-bold">${review.length}</span>`,
    `❌ Blocked Queue: <span class="status-badge badge-danger font-bold">${blocked.length}</span>`
  ]);

  const queues = [
    { name: 'AUTO EXECUTE', headerClass: 'auto-execute', statusLabel: '<span class="status-badge badge-secondary font-bold">AUTO APPROVED</span>', list: auto },
    { name: 'NEEDS REVIEW', headerClass: 'needs-review', statusLabel: '<span class="status-badge badge-secondary font-bold">PENDING REVIEW</span>', list: review },
    { name: 'BLOCKED', headerClass: 'blocked', statusLabel: '<span class="status-badge badge-secondary font-bold">SAFETY BLOCKED</span>', list: blocked }
  ];

  renderKanbanGrid(gridContainer, queues, makeTaskCard);
}