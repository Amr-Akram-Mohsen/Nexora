(function () {
    'use strict';

    let charts = {};

    document.addEventListener("DOMContentLoaded", () => {
        fetchQualityData();
    });

    function fetchQualityData() {
        fetch("/admin/sources/quality-data")
            .then(res => res.json())
            .then(data => {
                const qBody = document.getElementById("quality-leaderboard-tbody");
                if (qBody) qBody.innerHTML = data.quality_leaderboard_html;

                const sBody = document.getElementById("scrape-leaderboard-tbody");
                if (sBody) sBody.innerHTML = data.scrape_leaderboard_html;

                const fBody = document.getElementById("freshness-index-tbody");
                if (fBody) fBody.innerHTML = data.freshness_index_html;

                renderWordCountChart(data.word_counts);
                renderYieldRateChart(data.yield_rate);
            })
            .catch(err => {
                console.error("Failed to load quality data", err);
                const tbodies = ['quality-leaderboard-tbody', 'scrape-leaderboard-tbody', 'freshness-index-tbody'];
                tbodies.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) renderTableErrorState(el, 4, "Failed to load data");
                });
            });
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
})();
