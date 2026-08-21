(function() {
    function initChart() {
        if (typeof Chart === 'undefined') {
            setTimeout(initChart, 100);
            return;
        }

        const dataElement = document.getElementById('coverage-matrix-data');
        if (!dataElement) return;

        const canvas = document.getElementById('coverageMatrixChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        let rawData = [];
        try {
            rawData = JSON.parse(dataElement.textContent);
        } catch (e) {
            console.error("Failed to parse coverage matrix data:", e);
            return;
        }

        const chartData = {
            datasets: [{
                label: 'Categories',
                data: rawData,
                backgroundColor: function(context) {
                    const point = context.raw;
                    if (!point) return '#6b7280';
                    if (point.gapScore === 'High Gap') return '#ef4444'; // Danger
                    if (point.gapScore === 'Medium Gap') return '#eab308'; // Warning
                    return '#22c55e'; // Success
                },
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        };

        new Chart(ctx, {
            type: 'scatter',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const point = context.raw;
                                return `${point.name} (Coverage: ${point.x}, Demand: ${point.y})`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Content Coverage (Volume)'
                        },
                        beginAtZero: true
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Demand Score (Engagement)'
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChart);
    } else {
        initChart();
    }
})();
