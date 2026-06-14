import { getState } from './state.js';

export function renderContentAssetMapping() {
  const panel = document.getElementById("content-asset-mapping-panel");
  const tbody = document.getElementById("asset-mapping-table-body");
  const data = getState();
  const items = (data && data.content_asset_mapping) || [];
  
  if (!panel || !tbody) return;
  if (items.length === 0) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";
  
  let html = "";
  items.forEach(item => {
    // 1. Compile existing assets HTML
    let existingHtml = '<ul class="asset-mapping-list">';
    if (item.existing_assets && item.existing_assets.length > 0) {
      item.existing_assets.forEach(asset => {
        let actionBadge = "";
        if (asset.action === "reuse") {
          actionBadge = '<span class="status-badge badge-green font-bold">REUSE</span>';
        } else if (asset.action === "update") {
          actionBadge = '<span class="status-badge badge-warning font-bold">UPDATE</span>';
        } else if (asset.action === "repurpose") {
          actionBadge = '<span class="status-badge badge-blue font-bold">REPURPOSE</span>';
        }
        
        const typeIcon = asset.type === "video" ? "🎥" : asset.type === "article" ? "📄" : "🛍️";
        existingHtml += `
          <li class="asset-mapping-item">
            <div class="asset-mapping-item-header">
              <div class="asset-mapping-item-title">${typeIcon} ${asset.title}</div>
              <div>${actionBadge}</div>
            </div>
            <div class="asset-mapping-item-meta">Relevance Match: ${(asset.relevance_score * 100).toFixed(0)}%</div>
          </li>
        `;
      });
    } else {
      existingHtml += '<li class="text-muted asset-mapping-item" style="font-style: italic;">No matching assets found in database.</li>';
    }
    existingHtml += '</ul>';
    
    // 2. Compile missing assets HTML
    let missingHtml = '<ul class="asset-mapping-list">';
    if (item.missing_assets && item.missing_assets.length > 0) {
      item.missing_assets.forEach(gap => {
        const typeBadge = `<span class="status-badge badge-purple font-bold">${gap.content_type.toUpperCase()}</span>`;
        const priorityBadge = gap.priority === "high" 
          ? '<span class="status-badge badge-danger font-bold">CREATE (HIGH)</span>'
          : gap.priority === "medium"
            ? '<span class="status-badge badge-warning font-bold">CREATE (MED)</span>'
            : '<span class="status-badge badge-secondary font-bold">CREATE (LOW)</span>';
            
        missingHtml += `
          <li class="asset-mapping-item">
            <div class="asset-mapping-item-header">
              <div class="asset-mapping-item-title">${typeBadge} ${gap.missing_topic}</div>
              <div>${priorityBadge}</div>
            </div>
          </li>
        `;
      });
    } else {
      missingHtml += '<li class="text-muted asset-mapping-item" style="font-style: italic;">No content gaps identified.</li>';
    }
    missingHtml += '</ul>';
    
    html += `
      <tr>
        <td>
          <div class="font-bold text-foreground text-base">${item.entity}</div>
          <span class="status-badge ${item.type === 'category' ? 'badge-blue' : 'badge-purple'} font-bold">${item.type.toUpperCase()}</span>
          <div class="asset-mapping-item-meta mt-2">
            Score: <strong>${item.opportunity_score.toFixed(2)}</strong>
          </div>
        </td>
        <td>
          ${existingHtml}
        </td>
        <td>
          ${missingHtml}
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}
