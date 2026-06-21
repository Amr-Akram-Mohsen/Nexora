// app/web/static/js/admin/pages/quality.js

document.addEventListener("DOMContentLoaded", () => {
    fetchQualityData();
});

let charts = {};

function fetchQualityData() {
    fetch("/admin/providers/sources/quality-data")
        .then(res => res.json())
        .then(data => {
            renderQualityLeaderboard(data.quality_leaderboard);
            renderScrapeLeaderboard(data.scrape_leaderboard);
            renderWordCountChart(data.word_counts);
            renderFreshnessIndex(data.freshness_index);
            renderYieldRateChart(data.yield_rate);
        })
        .catch(err => {
            console.error("Failed to load quality data", err);
            const tbodies = ['quality-leaderboard-tbody', 'scrape-leaderboard-tbody', 'freshness-index-tbody'];
            tbodies.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = `<tr><td colspan="4" class="p-8 text-center text-red-500">Failed to load data</td></tr>`;
            });
        });
}

function renderQualityLeaderboard(data) {
    const tbody = document.getElementById("quality-leaderboard-tbody");
    if (!tbody) return;
    
    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="p-8 text-center text-muted">No data available</td></tr>`;
        return;
    }
    
    let html = "";
    data.forEach(row => {
        let tierClass = "badge-gray";
        if (row.tier === "High") tierClass = "badge-success";
        else if (row.tier === "Medium") tierClass = "badge-warning";
        else if (row.tier === "Low") tierClass = "badge-danger";
        
        html += `<tr class="border-b border-border hover:bg-gray-50">
            <td class="p-4 font-medium">${row.source}</td>
            <td class="p-4 text-center font-bold">${row.avg_quality}</td>
            <td class="p-4 text-center"><span class="status-badge ${tierClass}">${row.tier}</span></td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

function renderScrapeLeaderboard(data) {
    const tbody = document.getElementById("scrape-leaderboard-tbody");
    if (!tbody) return;
    
    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="p-8 text-center text-muted">No data available</td></tr>`;
        return;
    }
    
    let html = "";
    data.forEach(row => {
        let healthClass = "badge-gray";
        if (row.health === "Healthy") healthClass = "badge-success";
        else if (row.health === "Warning") healthClass = "badge-warning";
        else if (row.health === "Critical") healthClass = "badge-danger";
        
        html += `<tr class="border-b border-border hover:bg-gray-50">
            <td class="p-4 font-medium">${row.source}</td>
            <td class="p-4 text-center font-bold">${row.scrape_pct}%</td>
            <td class="p-4"><span class="status-badge ${healthClass}">${row.health}</span></td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

function renderFreshnessIndex(data) {
    const tbody = document.getElementById("freshness-index-tbody");
    if (!tbody) return;
    
    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="p-8 text-center text-muted">No data available</td></tr>`;
        return;
    }
    
    let html = "";
    data.forEach(row => {
        let severityClass = "badge-gray";
        if (row.severity === "Healthy") severityClass = "badge-success";
        else if (row.severity === "Warning") severityClass = "badge-warning";
        else if (row.severity === "Critical") severityClass = "badge-danger";
        
        html += `<tr class="border-b border-border hover:bg-gray-50">
            <td class="p-4 font-medium">${row.source}</td>
            <td class="p-4 text-sm text-gray-500">${row.latest_ingested}</td>
            <td class="p-4 font-bold text-gray-700">${row.days_stale}</td>
            <td class="p-4"><span class="status-badge ${severityClass}">${row.severity}</span></td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

function renderWordCountChart(data) {
    const canvas = document.getElementById("wordCountCanvas");
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    if (charts.wordCount) charts.wordCount.destroy();
    
    charts.wordCount = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: "Avg Word Count",
                data: data.data,
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#e5e7eb' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderYieldRateChart(data) {
    const canvas = document.getElementById("yieldRateCanvas");
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    if (charts.yieldRate) charts.yieldRate.destroy();
    
    const colors = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6'];
    data.datasets.forEach((ds, i) => {
        ds.borderColor = colors[i % colors.length];
        ds.backgroundColor = 'transparent';
        ds.borderWidth = 2;
        ds.tension = 0.4;
    });

    charts.yieldRate = new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#e5e7eb' } },
                x: { grid: { display: false } }
            }
        }
    });
}
