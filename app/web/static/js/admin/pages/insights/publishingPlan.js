// app/web/static/js/admin/pages/insights/publishingPlan.js
import { getState } from './state.js';
import { renderKanbanGrid, renderSummaryBar } from './utilities.js';

function makeTaskCard(task) {
  const card = document.createElement('div');
  card.className = 'kanban-task-card';
  const platformIcon = task.platform === 'youtube' ? '📺' : task.platform === 'pinterest' ? '📌' : '📝';
  const actionBadgeClass = task.action === 'create' ? 'badge-danger' : task.action === 'update' ? 'badge-warning' : 'badge-success';
  card.innerHTML = `
    <div class="kanban-task-header">
      <span class="kanban-task-platform">${platformIcon} ${task.platform.toUpperCase()}</span>
      <span class="status-badge ${actionBadgeClass}">${task.action}</span>
    </div>
    <h4 class="kanban-task-title">${task.entity}</h4>
    <p class="kanban-task-meta">Type: <strong>${task.content_type}</strong> &middot; Source: <code>${task.source}</code></p>
    <div class="kanban-task-reason">${task.reason}</div>
  `;
  return card;
}

export function renderContentPublishingPlan() {
  const panel = document.getElementById('content-publishing-plan-panel');
  const gridContainer = document.getElementById('publishing-plan-grid-container');
  const summaryBar = document.getElementById('publishing-plan-summary');
  if (!panel || !gridContainer || !summaryBar) return;

  const data = getState();
  const planData = data && data.content_publishing_plan;
  if (!planData || !planData.weekly_plan || planData.weekly_plan.length === 0) {
    panel.style.display = 'none';
    return;
  }

  panel.style.display = 'block';

  let weeklyPlan = planData.weekly_plan;
  if (data && data.selected_entity) {
    weeklyPlan = weeklyPlan.map(week => ({
      ...week,
      tasks: (week.tasks || []).filter(task => task.entity.toLowerCase().includes(data.selected_entity.toLowerCase()))
    }));
  }

  const totalTasks = weeklyPlan.reduce((acc, w) => acc + ((w.tasks || []).length), 0);
  const platformCounts = { youtube: 0, pinterest: 0, blog: 0 };
  const actionCounts = { reuse: 0, update: 0, create: 0, postpone: 0 };
  weeklyPlan.forEach(week => {
    (week.tasks || []).forEach(task => {
      totalTasks; // no-op, we already have total
      if (platformCounts[task.platform] !== undefined) platformCounts[task.platform]++;
      if (actionCounts[task.action] !== undefined) actionCounts[task.action]++;
    });
  });

  renderSummaryBar(summaryBar, [
    `🎯 Total Scheduled: <strong>${totalTasks}</strong>`,
    `📺 Platform Mix: <strong>YouTube: ${platformCounts.youtube}</strong> &middot; <strong>Pinterest: ${platformCounts.pinterest}</strong> &middot; <strong>Blog: ${platformCounts.blog}</strong>`,
    `🛠️ Actions: <strong>Create: ${actionCounts.create}</strong> &middot; <strong>Update: ${actionCounts.update}</strong> &middot; <strong>Reuse: ${actionCounts.reuse}</strong> &middot; <strong>Postpone: ${actionCounts.postpone}</strong>`
  ]);

  const queues = weeklyPlan.map(weekData => {
    let headerClass = 'auto-execute';
    let statusLabel = '<span class="status-badge badge-secondary font-bold">LOW PRIORITY</span>';
    let name = weekData.week;
    if (weekData.week === 'Week 1') {
      headerClass = 'blocked';
      statusLabel = '<span class="status-badge badge-danger font-bold">HIGH URGENCY</span>';
      name = 'Week 1 (Days 1-7)';
    } else if (weekData.week === 'Week 2') {
      headerClass = 'needs-review';
      statusLabel = '<span class="status-badge badge-warning font-bold">MEDIUM</span>';
      name = 'Week 2 (Days 8-14)';
    }
    return { name, headerClass, statusLabel, list: weekData.tasks || [] };
  });

  renderKanbanGrid(gridContainer, queues, makeTaskCard);
}