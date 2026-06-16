function fetchAndInjectHtml(url, targetElementId, loadingText = "Loading...", colspan = null, options = {}) {
  const container = document.getElementById(targetElementId);
  if (!container) return Promise.resolve();

  if (container.tagName === 'TBODY' && colspan) {
    container.innerHTML = getTableSpinnerHtml(colspan, loadingText);
  } else {
    container.innerHTML = getSpinnerHtml(loadingText);
  }

  return fetch(url)
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
