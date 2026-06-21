document.addEventListener("DOMContentLoaded", () => {
    fetchIngestionsStatus();
    fetchIngestionsLogs();

    const refreshBtn = document.getElementById("refresh-logs-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            const tbody = document.getElementById("ingestions-logs-tbody");
            if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="p-8 text-center text-muted"><i class="fa-solid fa-circle-notch fa-spin text-2xl mb-2"></i><p>Refreshing...</p></td></tr>';
            
            fetchIngestionsStatus();
            fetchIngestionsLogs();
        });
    }
});

function fetchIngestionsStatus() {
    fetch("/admin/ingestions/status")
        .then(res => res.json())
        .then(data => {
            const grid = document.getElementById("ingestions-status-grid");
            if (!grid) return;
            
            grid.innerHTML = "";
            if (data.length === 0) {
                grid.innerHTML = '<div class="col-span-full py-4 text-center text-muted">No channels found.</div>';
                return;
            }

            data.forEach(channel => {
                const isHealthy = channel.errors === 0;
                const statusColor = isHealthy ? "success" : "danger";
                const statusIcon = isHealthy ? "fa-check-circle" : "fa-triangle-exclamation";
                const lastFetch = channel.last_fetch ? new Date(channel.last_fetch).toLocaleString() : "Never";

                const card = document.createElement("a");
                // Link to sources list filtered by the channel name
                card.href = `/admin/sources?search=${channel.name}`;
                card.className = "card clickable-card";
                card.innerHTML = `
                    <div class="dashboard-stat-card border-l-4 border-${statusColor}">
                        <div class="dashboard-stat-icon flex items-center justify-center bg-${statusColor}-light text-${statusColor}">
                            <i class="fa-solid ${statusIcon}"></i>
                        </div>
                        <p class="dashboard-stat-label">${channel.name.toUpperCase()}</p>
                        <h3 class="dashboard-stat-value">${channel.requests_today} <span class="text-sm text-muted font-normal">reqs today</span></h3>
                        <p class="dashboard-stat-meta font-bold text-${statusColor}">
                            ${channel.errors} errors &bull; Last: ${lastFetch}
                        </p>
                    </div>
                `;
                grid.appendChild(card);
            });
        })
        .catch(err => console.error("Failed to fetch ingestion status", err));
}

function fetchIngestionsLogs() {
    fetch("/admin/ingestions/logs")
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("ingestions-logs-tbody");
            if (!tbody) return;
            
            tbody.innerHTML = "";
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-muted">No recent events.</td></tr>';
                return;
            }

            data.forEach(log => {
                const isSuccess = log.status === "Success";
                const statusBadge = isSuccess 
                    ? '<span class="badge badge-success">Success</span>' 
                    : `<span class="badge badge-danger" title="${log.failures} failures">Error</span>`;
                const timeStr = log.time ? new Date(log.time).toLocaleString() : "—";
                
                const tr = document.createElement("tr");
                tr.className = "border-b border-border last:border-0 hover:bg-gray-50";
                tr.innerHTML = `
                    <td class="p-4 text-sm text-muted whitespace-nowrap">${timeStr}</td>
                    <td class="p-4 font-medium"><span class="badge badge-secondary">${log.source}</span></td>
                    <td class="p-4 text-sm capitalize">${log.type}</td>
                    <td class="p-4 text-sm max-w-xs truncate" title="${log.query || '—'}">${log.query || "—"}</td>
                    <td class="p-4 text-sm">${log.category || "—"}</td>
                    <td class="p-4">${statusBadge}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error("Failed to fetch ingestion logs", err));
}
