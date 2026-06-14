export function getSpinnerHtml(text = "Loading…", extraClass = "") {
  return window.getSpinnerHtml(text, extraClass);
}

export function getErrorStateHtml(message = "Failed to load data. Please try again.", extraClass = "") {
  return window.getErrorStateHtml(message, extraClass);
}

export function getEmptyStateHtml(message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return window.getEmptyStateHtml(message, submessage, extraClass, icon);
}
