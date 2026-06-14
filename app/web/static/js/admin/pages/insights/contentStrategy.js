import { getState } from './state.js';

export function renderContentStrategy() {
  const panel = document.getElementById("content-strategy-panel");
  const tbody = document.getElementById("content-strategy-table-body");
  const data = getState();
  const items = (data && data.content_strategy) || [];
  
  if (!panel || !tbody) return;
  if (items.length === 0) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";
  
  let html = "";
  items.forEach(item => {
    const ytList = item.youtube.map(title => `<li class="asset-mapping-item">📺 <strong>${title}</strong></li>`).join("");
    const pinList = item.pinterest.map(title => `<li class="asset-mapping-item">📌 <strong>${title}</strong></li>`).join("");
    const blogList = item.blog.map(title => `<li class="asset-mapping-item">📝 <strong>${title}</strong></li>`).join("");
    
    const priorityAttr = item.priority_score ? `data-priority-score="${item.priority_score}"` : '';
    const lifecycleAttr = item.lifecycle_tag ? `data-lifecycle-tag="${item.lifecycle_tag}"` : '';

    html += `
      <tr ${priorityAttr} ${lifecycleAttr}>
        <td class="text-center"><span class="strategy-table-rank">#${item.priority_rank}</span></td>
        <td>
          <div class="font-bold text-foreground text-base">${item.entity}</div>
          <span class="status-badge ${item.type === 'category' ? 'badge-blue' : 'badge-purple'} font-bold">${item.type.toUpperCase()}</span>
          <div class="asset-mapping-item-meta mt-2">
            ${item.reasoning || ''}
          </div>
        </td>
        <td>
          <ul class="asset-mapping-list">
            ${ytList}
          </ul>
        </td>
        <td>
          <ul class="asset-mapping-list">
            ${pinList}
          </ul>
        </td>
        <td>
          <ul class="asset-mapping-list">
            ${blogList}
          </ul>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}
