// app/web/static/js/admin/pages/dashboard.js
// Content Analytics Dashboard — chart initialisation.
// Requires: Chart.js (loaded via admin base), nexoraCharts wrapper (core/charts.js)

(function () {
  'use strict';

  // ── Apply data-pct widths via CSS custom property (no inline styles) ──
  document.querySelectorAll('.stacked-bar-segment[data-pct]').forEach(function (el) {
    el.style.setProperty('--seg-width', el.dataset.pct + '%');
  });

  document.querySelectorAll('.overview-breakdown-bar[data-pct]').forEach(function (el) {
    el.style.setProperty('--seg-width', el.dataset.pct + '%');
  });

  // ── Palette from the shared nexoraCharts colour engine ──
  var palette = window.nexoraCharts ? window.nexoraCharts.getColors() : [];

  var STATUS_COLORS = {
    complete:  palette[3] || '#27AE60',  // green
    failed:    palette[4] || '#EB5757',  // red
    pending:   palette[1] || '#F2994A',  // orange
    enriching: palette[2] || '#2D9CDB'   // teal
  };

  // ── Content by Type — Doughnut ──
  var typeCanvas = document.getElementById('chart-content-type');
  if (typeCanvas) {
    var typeLabels = JSON.parse(typeCanvas.dataset.chartLabels || '[]');
    var typeValues = JSON.parse(typeCanvas.dataset.chartValues || '[]');

    if (typeValues.length > 0 && typeValues.some(function (v) { return v > 0; })) {
      window.nexoraCharts.render(
        'chart-content-type',
        'doughnut',
        {
          labels: typeLabels,
          datasets: [{
            data: typeValues,
            backgroundColor: typeLabels.map(function (_, i) { return palette[i % palette.length]; }),
            borderWidth: 0,
            hoverOffset: 6
          }]
        },
        {
          cutout: '62%',
          plugins: {
            legend: { position: 'right' },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                  var pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                  return ' ' + ctx.label + ': ' + ctx.parsed.toLocaleString() + ' (' + pct + '%)';
                }
              }
            }
          }
        }
      );
    } else {
      renderEmptyState(typeCanvas.closest('.content-chart-canvas-wrap'), "No content type data available");
    }
  }

  // ── Enrichment Status — Horizontal Bar ──
  var enrichCanvas = document.getElementById('chart-enrichment-status');
  if (enrichCanvas) {
    var enrichLabels = JSON.parse(enrichCanvas.dataset.chartLabels || '[]');
    var enrichValues = JSON.parse(enrichCanvas.dataset.chartValues || '[]');

    if (enrichValues.length > 0 && enrichValues.some(function (v) { return v > 0; })) {
      var bgColors = enrichLabels.map(function (l) {
        var c = STATUS_COLORS[l] || palette[5];
        // Convert rgb(...) to rgba(..., 0.8) for bar backgrounds
        return c.indexOf('rgb(') === 0
          ? c.replace('rgb(', 'rgba(').replace(')', ', 0.8)')
          : c;
      });
      var borderColors = enrichLabels.map(function (l) {
        return STATUS_COLORS[l] || palette[5];
      });

      window.nexoraCharts.render(
        'chart-enrichment-status',
        'bar',
        {
          labels: enrichLabels,
          datasets: [{
            label: 'Articles',
            data: enrichValues,
            backgroundColor: bgColors,
            borderColor: borderColors,
            borderWidth: 1,
            borderRadius: 4
          }]
        },
        {
          indexAxis: 'y',
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function (ctx) { return ' ' + ctx.parsed.x.toLocaleString() + ' articles'; }
              }
            }
          },
          scales: {
            x: {
              beginAtZero: true,
              grid: { color: 'rgba(128,128,128,0.08)' },
              ticks: { font: { size: 11 } }
            },
            y: {
              grid: { display: false },
              ticks: {
                font: { size: 12 },
                callback: function (val, idx) {
                  var label = this.getLabelForValue(idx);
                  return label.charAt(0).toUpperCase() + label.slice(1);
                }
              }
            }
          }
        }
      );
    } else {
      renderEmptyState(enrichCanvas.closest('.content-chart-canvas-wrap'), "No enrichment data available");
    }
  }

})();
