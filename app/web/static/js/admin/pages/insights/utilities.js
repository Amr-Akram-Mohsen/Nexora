// app/web/static/js/admin/pages/insights/utilities.js

export function getSpinnerHtml(text = "Loading…", extraClass = "") {
  return window.getSpinnerHtml(text, extraClass);
}

export function getErrorStateHtml(message = "Failed to load data. Please try again.", extraClass = "") {
  return window.getErrorStateHtml(message, extraClass);
}

export function getEmptyStateHtml(message = "No products found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return window.getEmptyStateHtml(message, submessage, extraClass, icon);
}

export function fetchAndInjectHtml(url, targetElementId, loadingText = "Loading...", colspan = null, options = {}) {
  return window.fetchAndInjectHtml(url, targetElementId, loadingText, colspan, options);
}
