// app/web/static/js/admin/pages/insights/assetMapping.js
import { getState } from './state.js';
import { cloneTemplate, getFiltered } from './utilities.js';

export function renderContentAssetMapping() {
  const panel = document.getElementById("content-asset-mapping-panel");
  const tbody = document.getElementById("asset-mapping-table-body");
  const data = getState();
  const originalItems = (data && data.content_asset_mapping) || [];

  if (!panel || !tbody) return;
  if (originalItems.length === 0) {
    panel.style.display = "none";
    return;
  }
  panel.style.display = "block";

  let items = [...originalItems];
  if (data && data.selected_entity) {
    items = getFiltered(items, data.selected_entity, 'entity');
  }

  tbody.innerHTML = '';
  const frag = document.createDocumentFragment();

  items.forEach(item => {
    const rowClone = cloneTemplate('asset-mapping-row-template');
    if (!rowClone) return;
    const row = rowClone.querySelector('tr') || rowClone.querySelector('tr.asset-mapping-row');

    row.dataset.entity = item.entity || '';
    const entityEl = row.querySelector('[data-field="entity"]');
    const scoreEl = row.querySelector('[data-field="score"]');
    const existingCountEl = row.querySelector('[data-field="existing_count"]');
    const missingCountEl = row.querySelector('[data-field="missing_count"]');

    if (entityEl) entityEl.textContent = `${item.entity} | ${item.type.toUpperCase()}`;
    if (scoreEl) scoreEl.textContent = `Score: ${item.opportunity_score.toFixed(2)}`;
    if (existingCountEl) existingCountEl.textContent = `${(item.existing_assets || []).length} Assets`;
    if (missingCountEl) missingCountEl.textContent = `${(item.missing_assets || []).length} Gaps`;

    frag.appendChild(row);

    const detailsClone = cloneTemplate('asset-mapping-details-template');
    if (detailsClone) {
      const detailsRow = detailsClone.querySelector('tr') || detailsClone.querySelector('tr.asset-mapping-details-row');
      const existingList = detailsRow.querySelector('[data-field="existing_list"]');
      const missingList = detailsRow.querySelector('[data-field="missing_list"]');

      if (item.existing_assets && item.existing_assets.length > 0) {
        item.existing_assets.forEach(asset => {
          const li = document.createElement('li');
          li.className = 'asset-mapping-item';
          const typeIcon = asset.type === 'video' ? '🎥' : asset.type === 'article' ? '📄' : '🛍️';
          const actionBadge = asset.action ? `<span class="status-badge ${asset.action === 'reuse' ? 'badge-green' : asset.action === 'update' ? 'badge-warning' : 'badge-blue'}">${asset.action.toUpperCase()}</span>` : '';
          li.innerHTML = `<div class="asset-mapping-item-header"><div class="asset-mapping-item-title">${typeIcon} ${asset.title}</div><div>${actionBadge}</div></div><div class="asset-mapping-item-meta">Relevance Match: ${(asset.relevance_score * 100).toFixed(0)}%</div>`;
          existingList.appendChild(li);
        });
      } else {
        const li = document.createElement('li');
        li.className = 'text-muted asset-mapping-item';
        li.style.fontStyle = 'italic';
        li.textContent = 'No matching assets found in database.';
        existingList.appendChild(li);
      }

      if (item.missing_assets && item.missing_assets.length > 0) {
        item.missing_assets.forEach(gap => {
          const li = document.createElement('li');
          li.className = 'asset-mapping-item';
          const typeBadge = `<span class="status-badge badge-purple">${gap.content_type.toUpperCase()}</span>`;
          const priorityBadge = gap.priority === 'high' ? '<span class="status-badge badge-danger">CREATE (HIGH)</span>' : gap.priority === 'medium' ? '<span class="status-badge badge-warning">CREATE (MED)</span>' : '<span class="status-badge badge-secondary">CREATE (LOW)</span>';
          let metaHtml = '';
          if (gap.reason) metaHtml += `<div class="asset-mapping-item-meta mt-1"><strong>Reason:</strong> ${gap.reason}</div>`;
          if (gap.priority_justification) metaHtml += `<div class="asset-mapping-item-meta"><strong>Justification:</strong> ${gap.priority_justification}</div>`;
          li.innerHTML = `<div class="asset-mapping-item-header"><div class="asset-mapping-item-title">${typeBadge} ${gap.missing_topic}</div><div>${priorityBadge}</div></div>${metaHtml}`;
          missingList.appendChild(li);
        });
      } else {
        const li = document.createElement('li');
        li.className = 'text-muted asset-mapping-item';
        li.style.fontStyle = 'italic';
        li.textContent = 'No content gaps identified.';
        missingList.appendChild(li);
      }

      frag.appendChild(detailsRow);
    }
  });

  tbody.appendChild(frag);

  tbody.addEventListener('click', (e) => {
    const btn = e.target.closest('.asset-mapping-details-toggle');
    if (!btn) return;
    const row = btn.closest('tr');
    if (!row) return;
    const detailsRow = row.nextElementSibling;
    if (!detailsRow) return;

    const icon = btn.querySelector('i');
    const expanded = btn.getAttribute('aria-expanded') === 'true';
    if (expanded) {
      detailsRow.style.display = 'none';
      btn.setAttribute('aria-expanded', 'false');
      if (icon) {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-right');
      }
    } else {
      detailsRow.style.display = 'table-row';
      btn.setAttribute('aria-expanded', 'true');
      if (icon) {
        icon.classList.remove('fa-chevron-right');
        icon.classList.add('fa-chevron-down');
      }
    }
  });
}