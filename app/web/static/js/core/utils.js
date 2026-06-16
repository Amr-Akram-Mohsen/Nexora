function setLoading(button, isLoading) {
    if (!button) return;
    if (isLoading) {
        button.classList.add('is-loading');
    } else {
        button.classList.remove('is-loading');
    }
}

function toggleActive(el) {
    el.classList.toggle("active", !el.classList.contains('active'));
}

function getUrlQueryParams() {
  const params = {};
  const searchParams = new URLSearchParams(window.location.search);
  for (const [key, value] of searchParams.entries()) {
    params[key] = value;
  }
  return params;
}

function applyUrlFilters(filterMap) {
  const params = getUrlQueryParams();
  for (const [paramKey, elementId] of Object.entries(filterMap)) {
    if (params[paramKey] !== undefined) {
      const el = document.getElementById(elementId);
      if (el) {
        el.value = params[paramKey];
      }
    }
  }
}

function formatDate(str, includeTime = false) {
  if (!str) return "—";
  try {
    const d = new Date(str);
    const dateStr = d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    if (includeTime) {
      return dateStr + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }
    return dateStr;
  } catch {
    return str;
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "—";
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}
