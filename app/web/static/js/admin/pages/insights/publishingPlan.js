import { getState } from './state.js';

export function renderContentPublishingPlan() {
  const panel = document.getElementById("content-publishing-plan-panel");
  const gridContainer = document.getElementById("publishing-plan-grid-container");
  const summaryBar = document.getElementById("publishing-plan-summary");
  
  if (!panel || !gridContainer || !summaryBar) return;
  
  const data = getState();
  const planData = data && data.content_publishing_plan;
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
    <div class="publishing-summary-bar">
      <div class="publishing-summary-item">🎯 Total Scheduled: <strong>${totalTasks}</strong></div>
      <div class="publishing-summary-item">📺 Platform Mix: <strong>YouTube: ${platformCounts.youtube}</strong> &middot; <strong>Pinterest: ${platformCounts.pinterest}</strong> &middot; <strong>Blog: ${platformCounts.blog}</strong></div>
      <div class="publishing-summary-item">🛠️ Actions: <strong>Create: ${actionCounts.create}</strong> &middot; <strong>Update: ${actionCounts.update}</strong> &middot; <strong>Reuse: ${actionCounts.reuse}</strong> &middot; <strong>Postpone: ${actionCounts.postpone}</strong></div>
    </div>
  `;
  
  // Render Columns
  planData.weekly_plan.forEach(weekData => {
    const column = document.createElement("div");
    column.className = "kanban-column";
    
    // Header colors based on Week
    let headerClass = "";
    let statusLabel = "";
    if (weekData.week === "Week 1") {
      headerClass = "blocked";
      statusLabel = '<span class="status-badge badge-danger font-bold">HIGH URGENCY</span>';
    } else if (weekData.week === "Week 2") {
      headerClass = "needs-review";
      statusLabel = '<span class="status-badge badge-warning font-bold">MEDIUM</span>';
    } else {
      headerClass = "auto-execute";
      statusLabel = '<span class="status-badge badge-secondary font-bold">LOW PRIORITY</span>';
    }
    
    let taskCardsHtml = "";
    const tasks = weekData.tasks || [];
    if (tasks.length === 0) {
      taskCardsHtml = `
        <div class="text-center text-muted p-4" style="font-style: italic;">
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
            <p class="kanban-task-meta">Type: <strong>${task.content_type}</strong> &middot; Source: <code>${task.source}</code></p>
            
            <div class="kanban-task-reason">
              ${task.reason}
            </div>
          </div>
        `;
      });
    }
    
    column.innerHTML = `
      <div class="publishing-column-header ${headerClass}">
        <div class="font-bold text-sm">${weekData.week}</div>
        <div>${statusLabel}</div>
      </div>
      <div class="kanban-column-body">
        ${taskCardsHtml}
      </div>
    `;
    gridContainer.appendChild(column);
  });
}
