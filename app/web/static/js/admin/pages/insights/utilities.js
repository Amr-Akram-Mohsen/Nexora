// app/web/static/js/admin/pages/insights/utilities.js
export function cloneTemplate(id) {
  const t = document.getElementById(id);
  if (!t) return null;
  return t.content.cloneNode(true);
}

export function fetchJson(url, { timeout = 15000, ...opts } = {}) {
  const controller = new AbortController();
  const signal = controller.signal;
  const fetchOpts = { signal, ...opts };
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  return fetch(url, fetchOpts)
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error(`Fetch failed (${res.status}) ${url}`);
      return res.json();
    });
}

export function getFiltered(items = [], selectedEntity, key = 'entity') {
  if (!selectedEntity) return items;
  const lower = selectedEntity.toLowerCase();
  return items.filter(it => (it[key] || '').toLowerCase().includes(lower));
}

export function createTableStateRow(colspan, message, type = 'info') {
  const tr = document.createElement('tr');
  const td = document.createElement('td');
  td.colSpan = colspan;
  td.className = 'text-center';
  td.textContent = message;
  if (type === 'error') td.classList.add('text-danger');
  else if (type === 'muted') td.classList.add('text-muted');
  tr.appendChild(td);
  return tr;
}

export function renderSummaryBar(container, items) {
  if (!container) return;
  container.innerHTML = '';
  items.forEach(it => {
    const div = document.createElement('div');
    div.className = 'publishing-summary-item';
    div.innerHTML = it; // small trusted snippets only
    container.appendChild(div);
  });
}

export function renderKanbanGrid(gridContainer, queues, itemRenderer) {
  if (!gridContainer) return;
  gridContainer.innerHTML = '';
  const frag = document.createDocumentFragment();

  queues.forEach(q => {
    const column = document.createElement('div');
    column.className = 'kanban-column';

    const header = document.createElement('div');
    header.className = `publishing-column-header ${q.headerClass || ''}`;
    header.innerHTML = `<div class="font-bold text-sm">${q.name}</div><div>${q.statusLabel || ''}</div>`;

    const body = document.createElement('div');
    body.className = 'kanban-column-body';

    if (!q.list || q.list.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'text-center text-muted p-4';
      empty.style.fontStyle = 'italic';
      empty.textContent = 'No items in this queue.';
      body.appendChild(empty);
    } else {
      q.list.forEach(item => {
        const node = itemRenderer(item);
        if (node) body.appendChild(node);
      });
    }

    column.appendChild(header);
    column.appendChild(body);
    frag.appendChild(column);
  });

  gridContainer.appendChild(frag);
}

export function getSpinnerHtml(text = "Loading…", extraClass = "") {
  return window.getSpinnerHtml(text, extraClass);
}

export function getErrorStateHtml(message = "Failed to load data. Please try again.", extraClass = "") {
  return window.getErrorStateHtml(message, extraClass);
}

export function getEmptyStateHtml(message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return window.getEmptyStateHtml(message, submessage, extraClass, icon);
}
