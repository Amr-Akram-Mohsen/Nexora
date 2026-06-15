// app/web/static/js/admin/pages/insights/governance.js
import { getState } from './state.js';
import { renderKanbanGrid, renderSummaryBar } from './utilities.js';

function makeTaskCard(task) {
  const card = document.createElement('div');
  card.className = 'kanban-task-card';
  const platformIcon = task.platform === 'youtube' ? '📺' : task.platform === 'pinterest' ? '📌' : '📝';
  const actionBadgeClass = task.action === 'create' || task.action === 'publish' ? 'badge-danger' : task.action === 'update' ? 'badge-warning' : 'badge-success';

  let riskReasonsHtml = '';
  if (task.risk_reasons && task.risk_reasons.length > 0) {
    riskReasonsHtml = '<div class="kanban-task-risk">';
    task.risk_reasons.forEach(r => { riskReasonsHtml += `<div>⚠️ ${r}</div>`; });
    riskReasonsHtml += '</div>';
  }

  let executionLogHtml = '';
  if (task.execution_log) {
    const url = task.execution_log.mock_url || '';
    executionLogHtml = `<div class="kanban-task-log"><strong>Status:</strong> ${String(task.execution_log.status || '').toUpperCase()}${url ? `<br/><strong>Sim Published:</strong> <a href="${url}" target="_blank">${url}</a>` : ''}</div>`;
  }

  let riskBadgeClass = 'badge-success';
  if (task.risk_level === 'HIGH') riskBadgeClass = 'badge-danger';
  else if (task.risk_level === 'MEDIUM') riskBadgeClass = 'badge-warning';

  card.innerHTML = `
    <div class="kanban-task-header">
      <span class="kanban-task-platform">${platformIcon} ${task.platform.toUpperCase()}</span>
      <span class="status-badge ${actionBadgeClass}">${task.action}</span>
    </div>
    <h4 class="kanban-task-title">${task.entity}</h4>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.5rem;flex-wrap:wrap;gap:.5rem;">
      <span class="kanban-task-meta">Decision Score: <strong style="color:#6366f1;">${(task.decision_score * 100).toFixed(0)}%</strong></span>
      <span class="status-badge ${riskBadgeClass}">${task.risk_level} RISK</span>
    </div>
    <div class="kanban-task-meta" style="display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap;">
      <span>Timeline: <strong>${task.scheduled_time}</strong></span>
      <span>Status: <strong style="text-transform:uppercase;">${task.status}</strong></span>
    </div>
    ${riskReasonsHtml}
    ${executionLogHtml}
  `;
  return card;
}

export function renderExecutionGovernance() {
  const panel = document.getElementById("execution-governance-panel");
  const gridContainer = document.getElementById("execution-governance-grid-container");
  const summaryBar = document.getElementById("execution-governance-summary");
  if (!panel || !gridContainer || !summaryBar) return;

  const data = getState();
  const govData = data && data.execution_governance;
  if (!govData) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";

  const queued = govData.queued_tasks || [];
  const approved = govData.approved_tasks || [];
  const blocked = govData.blocked_tasks || [];

  renderSummaryBar(summaryBar, [
    `🛡️ Governance Mode: <span class="status-badge badge-blue font-bold">${govData.mode}</span>`,
    `✅ Safe / Executed: <span class="status-badge badge-success font-bold">${approved.length}</span>`,
    `⏳ Needs Approval: <span class="status-badge badge-warning font-bold">${queued.length}</span>`,
    `❌ Blocked Tasks: <span class="status-badge badge-danger font-bold">${blocked.length}</span>`
  ]);

  const queues = [
    { name: 'SAFE / EXECUTED', headerClass: 'auto-execute', statusLabel: '<span class="status-badge badge-secondary font-bold">SAFE FOR PRODUCTION</span>', list: approved },
    { name: 'NEEDS APPROVAL', headerClass: 'needs-review', statusLabel: '<span class="status-badge badge-secondary font-bold">APPROVAL GATED</span>', list: queued },
    { name: 'BLOCKED', headerClass: 'blocked', statusLabel: '<span class="status-badge badge-secondary font-bold">SAFETY RESTRICTED</span>', list: blocked }
  ];

  renderKanbanGrid(gridContainer, queues, makeTaskCard);
}