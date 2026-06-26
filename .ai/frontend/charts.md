# Charts Architecture & Visualization Standards

Data visualization within Nexora (predominantly in the Admin Dashboard) relies exclusively on **Chart.js**. To maintain a cohesive aesthetic, enforce responsiveness, and prevent memory leaks, raw initialization of Chart.js within domain scripts is forbidden.

## The Core Wrapper: `nexoraCharts`

All charts must be instantiated via the core wrapper located at `app/web/static/js/core/charts.js`.

### Usage
```javascript
// Example: Rendering a chart in a domain script
window.nexoraCharts.render(
    'myCanvasId', // 1. Canvas ID
    'line',       // 2. Chart Type ('line', 'bar', 'doughnut')
    chartData,    // 3. Data Object (labels, datasets)
    {             // 4. Custom Options (Optional)
        plugins: {
            title: { display: true, text: 'Monthly Growth' }
        }
    }
);
```

### Why use the wrapper?
1.  **Memory Management:** The wrapper automatically detects if a chart instance already exists on the target canvas and cleanly calls `.destroy()` before rendering the new one. This prevents "canvas overlapping" bugs when data is refreshed via AJAX.
2.  **Design System Enforcement:** It automatically injects CSS variables (e.g., `--color-foreground`, `--color-border`) into the Chart.js configuration, ensuring the charts adapt instantly if the global theme (e.g., Dark Mode) changes.
3.  **Responsive Defaults:** Ensures `maintainAspectRatio: false` and responsive wrappers are consistently applied.

---

## Approved Chart Types

1.  **Line Charts (`'line'`):** Use strictly for continuous data over time (e.g., Engagement Trends, Traffic over 30 days). Always use smooth curves (`tension: 0.4`).
2.  **Bar Charts (`'bar'`):** Use for comparing discrete categories or entities (e.g., Top 5 Authors, Clicks per Store).
3.  **Doughnut Charts (`'doughnut'`):** Use for visualizing composition or distribution (e.g., Traffic by Device, Content by Category). Never use Pie charts; Doughnuts provide a cleaner aesthetic and allow for center-labeling.

---

## Data Injection (HTML to JS)

To adhere to the separation of concerns, the Python backend must not write inline JavaScript. Instead, pass the JSON payload directly into the DOM via a `data-*` attribute.

**Jinja Template:**
```html
<div class="chart-container">
    <canvas id="trafficChart" data-chart-payload='{{ chart_json_string | safe }}'></canvas>
</div>
```

**JavaScript:**
```javascript
const canvas = document.getElementById('trafficChart');
if (canvas && canvas.dataset.chartPayload) {
    const data = JSON.parse(canvas.dataset.chartPayload);
    window.nexoraCharts.render('trafficChart', 'line', data);
}
```

---

## Colors and Theming

Do not hardcode hex codes (e.g., `#ff0000`) in Chart.js dataset configurations.

**Rule:** Always fetch colors from the central theme engine to guarantee contrast and visual harmony.

```javascript
// Fetch standard palette sequence
const palette = window.nexoraCharts.getColors();

const myDataset = {
    label: 'Sales',
    data: [10, 20, 30],
    backgroundColor: palette[0], // Uses --brand-primary
    borderColor: palette[0],
};
```

---

## Tooltips and Legends

*   **Legends:** The wrapper defaults to placing legends at the `bottom` with `usePointStyle: true` for a cleaner look. Do not override this unless space constraints are extreme.
*   **Tooltips:** Ensure tooltips provide clear context. If formatting currency or percentages, utilize the Chart.js tooltip callbacks to format the raw data securely.

---

## Empty States & Loading States

A chart canvas without data is an invisible element that confuses users.

1.  **Loading:** While fetching AJAX data, hide the canvas container and display the `components/ui/spinner.html` component.
2.  **Empty State:** If the dataset is completely empty (e.g., `data.datasets[0].data.length === 0`), do not render the chart. Hide the canvas and display a fallback empty state (`components/ui/empty-state.html`) indicating "No data available for this period."

---

## Dashboard Layout Guidelines

*   **Containers:** Charts must be wrapped in a `.chart-container` `div` with a relative position and a strict height (e.g., `height: 300px`). Chart.js requires this wrapper to calculate responsive resizing correctly.
*   **Context:** Every chart must have a clear heading above it (e.g., an `h3`) explaining the metric, avoiding ambiguous standalone visualizations.
