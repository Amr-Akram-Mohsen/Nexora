// app/web/static/js/admin/pages/insights/contentStrategy.js
import { getState } from './state.js';
import { getFiltered, createTableStateRow } from './utilities.js';

export function renderContentStrategy() {
  const panel = document.getElementById('content-strategy-panel');
  const tbody = document.getElementById('content-strategy-table-body');
  const data = getState();
  const originalItems = (data && data.content_strategy) || [];

  if (!panel || !tbody) return;
  if (originalItems.length === 0) {
    panel.style.display = 'none';
    return;
  }
  panel.style.display = 'block';

  let items = originalItems;
  if (data && data.selected_entity) items = getFiltered(items, data.selected_entity, 'entity');

  tbody.innerHTML = '';
  const frag = document.createDocumentFragment();

  if (items.length === 0) {
    frag.appendChild(createTableStateRow(5, `No content strategies found matching active filter "${data.selected_entity}".`, 'muted'));
  } else {
    items.forEach(item => {
      const tr = document.createElement('tr');
      if (item.priority_score) tr.setAttribute('data-priority-score', item.priority_score);
      tr.innerHTML = `
        <td class="text-center"><span class="strategy-table-rank">#${item.priority_rank}</span></td>
        <td>
          <div class="font-bold text-foreground text-base">${item.entity} | <span class="status-badge ${item.type === 'category' ? 'badge-blue' : 'badge-purple'}">${item.type.toUpperCase()}</span></div>
          <div class="asset-mapping-item-meta mt-2">${item.reasoning || ''}</div>
        </td>
        <td><ul class="asset-mapping-list">${(item.youtube || []).map(t => `<li class="asset-mapping-item">📺 <strong>${t}</strong></li>`).join('')}</ul></td>
        <td><ul class="asset-mapping-list">${(item.pinterest || []).map(t => `<li class="asset-mapping-item">📌 <strong>${t}</strong></li>`).join('')}</ul></td>
        <td><ul class="asset-mapping-list">${(item.blog || []).map(t => `<li class="asset-mapping-item">📝 <strong>${t}</strong></li>`).join('')}</ul></td>
      `;
      frag.appendChild(tr);
    });
  }

  tbody.appendChild(frag);
}