document.addEventListener("DOMContentLoaded", () => {
    fetchIngestionsStatus();
    fetchIngestionsLogs();

    const refreshBtn = document.getElementById("refresh-logs-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            fetchIngestionsStatus();
            fetchIngestionsLogs();
        });
    }
});

function fetchIngestionsStatus() {
    if (typeof fetchAndInjectHtml === 'function') {
        fetchAndInjectHtml("/admin/ingestions/status?format=html", "ingestions-status-grid", "Loading channels...", null);
    }
}

function fetchIngestionsLogs() {
    if (typeof fetchAndInjectHtml === 'function') {
        fetchAndInjectHtml("/admin/ingestions/logs?format=html", "ingestions-logs-tbody", "Loading events...", 6);
    }
}
