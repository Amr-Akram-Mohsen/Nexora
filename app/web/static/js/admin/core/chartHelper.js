/**
 * chartHelper.js
 * Automatically initializes Chart.js instances based on DOM data attributes.
 * Reduces repetitive chart setup boilerplate across admin dashboards.
 * Requires: window.nexoraCharts (from core/charts.js)
 */
document.addEventListener("DOMContentLoaded", function() {
    if (!window.nexoraCharts) {
        console.warn("chartHelper.js requires window.nexoraCharts to be loaded.");
        return;
    }

    const chartElements = document.querySelectorAll('canvas[data-chart]');

    chartElements.forEach(canvas => {
        const chartType = canvas.getAttribute('data-chart');
        const payloadId = canvas.getAttribute('data-chart-payload');
        const chartId = canvas.id;

        if (!chartId) {
            console.warn("chartHelper: Canvas is missing an ID.");
            return;
        }

        if (!payloadId) {
            console.warn(`chartHelper: Canvas ${chartId} is missing data-chart-payload.`);
            return;
        }

        const dataElement = document.getElementById(payloadId);
        if (!dataElement) {
            console.warn(`chartHelper: Payload element #${payloadId} not found.`);
            return;
        }

        try {
            const rawData = JSON.parse(dataElement.textContent);

            // Extract options if provided as a JSON attribute
            const optionsAttr = canvas.getAttribute('data-chart-options');
            let options = {};
            if (optionsAttr) {
                options = JSON.parse(optionsAttr);
            }

            // Render the chart using the centralized nexoraCharts wrapper
            window.nexoraCharts.render(chartId, chartType, rawData, options);

        } catch (e) {
            console.error(`chartHelper: Failed to parse data for chart ${chartId}`, e);
        }
    });
});
