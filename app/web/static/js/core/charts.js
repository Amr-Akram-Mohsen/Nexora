/**
 * Nexora Core Chart Architecture
 * Provides generic wrapper around Chart.js
 * No business/domain logic.
 */

(function () {
    'use strict';

    // Store active chart instances by canvas ID to prevent overlaps and memory leaks
    const chartInstances = new Map();

    function getCssVar(varName, fallback) {
        const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
        return val || fallback;
    }

    /**
     * Initializes a chart, safely destroying any previous instance on the same canvas.
     * @param {string} canvasId - The DOM ID of the canvas element.
     * @param {string} type - 'line', 'doughnut', 'bar', etc.
     * @param {Object} data - Chart.js data object (labels, datasets).
     * @param {Object} customOptions - Chart.js options to merge with defaults.
     */
    function renderChart(canvasId, type, data, customOptions = {}) {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js is not loaded.');
            return null;
        }

        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        // Destroy existing instance to prevent overlapping rendering/memory leaks
        if (chartInstances.has(canvasId)) {
            chartInstances.get(canvasId).destroy();
            chartInstances.delete(canvasId);
        }

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: getCssVar('--color-foreground', '#333'),
                        usePointStyle: true,
                        padding: 20
                    }
                }
            }
        };

        // Merge defaults with custom options
        const options = { ...defaultOptions, ...customOptions };

        // Handle specific type overrides
        if (type === 'line' || type === 'bar') {
            options.scales = {
                x: {
                    grid: { display: false },
                    ticks: { color: getCssVar('--color-muted-foreground', '#666') }
                },
                y: {
                    grid: { color: getCssVar('--color-border', '#eee') },
                    ticks: { color: getCssVar('--color-muted-foreground', '#666') }
                },
                ...(customOptions.scales || {})
            };
        }

        const chart = new Chart(canvas, {
            type,
            data,
            options
        });

        chartInstances.set(canvasId, chart);
        return chart;
    }

    window.nexoraCharts = {
        render: renderChart,
        getColors: function() {
            return [
                getCssVar('--brand-primary', '#5D5FEF'),
                getCssVar('--brand-orange', '#F2994A'),
                getCssVar('--brand-teal', '#2D9CDB'),
                getCssVar('--brand-green', '#27AE60'),
                getCssVar('--brand-red', '#EB5757'),
                getCssVar('--brand-purple', '#9B51E0'),
            ];
        }
    };

})();
