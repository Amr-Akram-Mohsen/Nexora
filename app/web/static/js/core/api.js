function fetchAndInjectHtml(url, targetElementId, loadingText = "Loading...", colspan = null, options = {}) {
  const container = document.getElementById(targetElementId);
  if (!container) return Promise.resolve();

  if (container.tagName === 'TBODY' && colspan) {
    container.innerHTML = getTableSpinnerHtml(colspan, loadingText);
  } else {
    container.innerHTML = getSpinnerHtml(loadingText);
  }

  const fetchOptions = { ...options };
  if (fetchOptions.method && fetchOptions.method !== 'GET' && fetchOptions.method !== 'HEAD') {
      fetchOptions.headers = fetchOptions.headers || {};
      fetchOptions.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]')?.content || '';
  }

  return fetch(url, fetchOptions)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load ${url}`);
      const isEmpty = res.headers.get("X-Empty") === "true";
      return res.text().then(html => ({ html, isEmpty }));
    })
    .then(({ html, isEmpty }) => {
      if (isEmpty && options.hideElementIdOnEmpty) {
        const elToHide = document.getElementById(options.hideElementIdOnEmpty);
        if (elToHide) {
          elToHide.style.display = "none";
        }
      } else {
        if (options.hideElementIdOnEmpty) {
          const elToShow = document.getElementById(options.hideElementIdOnEmpty);
          if (elToShow) {
            elToShow.style.display = options.displayStyle || "block";
          }
        }
        container.innerHTML = html;
      }
    })
    .catch(err => {
      console.error(err);
      if (container.tagName === 'TBODY' && colspan) {
        container.innerHTML = getTableErrorStateHtml(colspan, "Failed to load data.");
      } else {
        container.innerHTML = getErrorStateHtml("Failed to load data.");
      }
    });
}

// JSON API WRAPPERS
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

async function apiRequest(url, method = 'GET', body = null, customHeaders = {}) {
    const headers = {
        'Accept': 'application/json',
        ...customHeaders
    };

    if (method !== 'GET' && method !== 'HEAD') {
        headers['X-CSRFToken'] = getCsrfToken();
        if (body && !(body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            body = JSON.stringify(body);
        }
    }

    try {
        const response = await fetch(url, { method, headers, body });
        let data = null;

        // Some endpoints return 204 No Content
        if (response.status === 204) return null;

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            data = await response.json();
        }

        if (!response.ok) {
            const errorMsg = data?.error || data?.message || `Error ${response.status}`;
            throw new Error(errorMsg);
        }

        return data;
    } catch (err) {
        if (typeof showToast === 'function') {
            showToast(err.message || 'An error occurred', 'error');
        } else {
            console.error('API Error:', err);
        }
        throw err;
    }
}

window.api = {
    get: (url, headers) => apiRequest(url, 'GET', null, headers),
    post: (url, body, headers) => apiRequest(url, 'POST', body, headers),
    put: (url, body, headers) => apiRequest(url, 'PUT', body, headers),
    delete: (url, headers) => apiRequest(url, 'DELETE', null, headers),
};
