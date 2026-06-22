// ==========================================
// OVERVIEW PAGE & ANALYTICS FUNCTIONS
// ==========================================

function renderDashboardOverview(containerId) {
  fetchAndInjectHtml('/admin/dashboard/widget/stats', containerId, 'Loading platform metrics...');
  fetchAndInjectHtml('/admin/dashboard/widget/catalog-health', 'catalog-health-container', 'Loading health indicators...');
  fetchAndInjectHtml('/admin/dashboard/widget/recent-ingest', 'recent-ingest-container', 'Loading ingest logs...');
  fetchAndInjectHtml('/admin/dashboard/widget/review-queue-aging', 'review-queue-aging-container', 'Loading review queue...');
  fetchAndInjectHtml('/admin/dashboard/widget/categories-distribution', 'categories-distribution-container', 'Loading category stats...');
  fetchAndInjectHtml('/admin/dashboard/widget/sources-distribution', 'sources-distribution-container', 'Loading source stats...');
  fetchAndInjectHtml('/admin/dashboard/widget/product-sources-distribution', 'product-sources-distribution-container', 'Loading product sources...');
  fetchAndInjectHtml('/admin/dashboard/widget/top-content-providers', 'top-content-providers-container', 'Loading provider performance...');
  fetchAndInjectHtml('/admin/dashboard/widget/top-product-providers', 'top-product-providers-container', 'Loading marketplace performance...');
  fetchAndInjectHtml('/admin/dashboard/widget/provider-activities', 'provider-activities-container', 'Loading provider status...');
}

function renderTopArticles(containerId) {
  fetchAndInjectHtml('/admin/dashboard/widget/top-articles', containerId, 'Loading articles...');
}

function renderTopItems(containerId) {
  fetchAndInjectHtml('/admin/dashboard/widget/top-items', containerId, 'Loading items...');
}

function renderInteractionBreakdown(containerId) {
  fetchAndInjectHtml('/admin/dashboard/widget/interactions-breakdown', containerId, 'Loading breakdown...');
}
