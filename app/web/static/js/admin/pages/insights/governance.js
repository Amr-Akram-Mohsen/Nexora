import { getState } from './state.js';

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
  gridContainer.innerHTML = "";
  
  const queued = govData.queued_tasks || [];
  const approved = govData.approved_tasks || [];
  const blocked = govData.blocked_tasks || [];
  
  // Render Summary Metrics Bar
  summaryBar.innerHTML = `
    <div class="publishing-summary-item">🛡️ Governance Mode: <span class="status-badge badge-blue font-bold">${govData.mode}</span></div>
    <div class="publishing-summary-item">✅ Safe / Executed: <span class="status-badge badge-success font-bold">${approved.length}</span></div>
    <div class="publishing-summary-item">⏳ Needs Approval: <span class="status-badge badge-warning font-bold">${queued.length}</span></div>
    <div class="publishing-summary-item">❌ Blocked Tasks: <span class="status-badge badge-danger font-bold">${blocked.length}</span></div>
  `;
  
  const queues = [
    { name: "SAFE / EXECUTED", list: approved, headerClass: "auto-execute", status: "SAFE FOR PRODUCTION" },
    { name: "NEEDS APPROVAL", list: queued, headerClass: "needs-review", status: "APPROVAL GATED" },
    { name: "BLOCKED", list: blocked, headerClass: "blocked", status: "SAFETY RESTRICTED" }
  ];
  
  queues.forEach(q => {
    const column = document.createElement("div");
    column.className = "kanban-column";
    
    let taskCardsHtml = "";
    if (q.list.length === 0) {
      taskCardsHtml = `
        <div class="text-center text-muted p-4" style="font-style: italic;">
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
          riskReasonsHtml = `<div class="kanban-task-risk">`;
          task.risk_reasons.forEach(reason => {
            riskReasonsHtml += `<div>⚠️ ${reason}</div>`;
          });
          riskReasonsHtml += `</div>`;
        }
        
        let executionLogHtml = "";
        if (task.execution_log) {
          executionLogHtml = `
            <div class="kanban-task-log">
              <strong>Status:</strong> ${task.execution_log.status.toUpperCase()}<br/>
              <strong>Sim Published:</strong> <a href="${task.execution_log.mock_url}" target="_blank">${task.execution_log.mock_url}</a>
            </div>
          `;
        }
        
        taskCardsHtml += `
          <div class="kanban-task-card">
            <div class="kanban-task-header">
              <span class="kanban-task-platform">
                <span>${platformIcon}</span> ${platformName}
              </span>
              <span class="status-badge ${actionBadgeClass}">
                ${task.action}
              </span>
            </div>
            
            <h4 class="kanban-task-title">${task.entity}</h4>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
              <span class="kanban-task-meta">Decision Score: <strong style="color: #6366f1;">${(task.decision_score * 100).toFixed(0)}%</strong></span>
              <span class="status-badge ${riskBadgeClass}">
                ${task.risk_level} RISK
              </span>
            </div>
            
            <div class="kanban-task-meta" style="display: flex; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap;">
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
      <div class="publishing-column-header ${q.headerClass}">
        <div class="font-bold text-sm">${q.name}</div>
        <div><span class="status-badge badge-secondary font-bold">${q.status}</span></div>
      </div>
      <div class="kanban-column-body">
        ${taskCardsHtml}
      </div>
    `;
    gridContainer.appendChild(column);
  });
}
