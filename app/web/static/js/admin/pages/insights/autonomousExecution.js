import { getState } from './state.js';

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
  gridContainer.innerHTML = "";
  
  const auto = executionData.auto_execute || [];
  const review = executionData.needs_review || [];
  const blocked = executionData.blocked || [];
  
  // Render Summary Metrics Bar
  summaryBar.innerHTML = `
    <div class="publishing-summary-item">🤖 Auto-Execute Queue: <span class="status-badge badge-success font-bold">${auto.length}</span></div>
    <div class="publishing-summary-item">🤔 Needs Review Queue: <span class="status-badge badge-warning font-bold">${review.length}</span></div>
    <div class="publishing-summary-item">❌ Blocked Queue: <span class="status-badge badge-danger font-bold">${blocked.length}</span></div>
  `;
  
  const queues = [
    { name: "AUTO EXECUTE", list: auto, headerClass: "auto-execute", status: "AUTO APPROVED" },
    { name: "NEEDS REVIEW", list: review, headerClass: "needs-review", status: "PENDING REVIEW" },
    { name: "BLOCKED", list: blocked, headerClass: "blocked", status: "SAFETY BLOCKED" }
  ];
  
  queues.forEach(q => {
    const column = document.createElement("div");
    column.className = "kanban-column";
    
    let taskCardsHtml = "";
    if (q.list.length === 0) {
      taskCardsHtml = `
        <div class="text-center text-muted p-4" style="font-style: italic;">
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
          riskHtml = `<div class="kanban-task-risk">`;
          task.risk_factors.forEach(risk => {
            riskHtml += `<div>⚠️ ${risk}</div>`;
          });
          riskHtml += `</div>`;
        }
        
        let executionLogHtml = "";
        if (task.execution_log) {
          executionLogHtml = `
            <div class="kanban-task-log">
              <strong>Status:</strong> ${task.execution_log.status.toUpperCase()}<br/>
              <strong>Sim Published:</strong> <a href="${task.execution_log.published_url}" target="_blank">${task.execution_log.published_url}</a><br/>
              <strong>Timestamp:</strong> ${task.execution_log.timestamp}
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
            <p class="kanban-task-meta">Confidence Score: <strong style="color: #6366f1;">${(task.confidence_score * 100).toFixed(0)}%</strong></p>
            
            <div class="kanban-task-reason">
              ${task.reason}
            </div>
            
            ${riskHtml}
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
