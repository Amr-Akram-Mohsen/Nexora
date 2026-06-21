// app/web/static/js/admin/pages/insights/acquisitionSources.js

let acquisitionCharts = {};

export function renderAcquisitionSources(timeFrame = "7_days") {
  fetch(`/admin/insights/acquisition-data?time_frame=${timeFrame}`)
    .then(res => res.json())
    .then(data => {
      renderVelocityChart(data.velocity);
      renderContributionChart(data.contribution);
      renderAuthorityChart(data.authority);
      renderCoverageMatrix(data.matrix);
    })
    .catch(err => console.error("Failed to load acquisition data", err));
}

function renderVelocityChart(data) {
  const container = document.getElementById("acquisition-velocity-chart");
  if (!container) return;
  
  if (data.labels.length === 0) {
    container.innerHTML = "<div class='text-muted p-4 text-center'>No data available</div>";
    return;
  }
  
  if (!document.getElementById("velocityCanvas")) {
      container.innerHTML = '<canvas id="velocityCanvas"></canvas>';
  }
  
  const ctx = document.getElementById("velocityCanvas").getContext("2d");
  
  if (acquisitionCharts.velocity) {
      acquisitionCharts.velocity.destroy();
  }
  
  // Nexora theme colors
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
  data.datasets.forEach((ds, i) => {
      ds.borderColor = colors[i % colors.length];
      ds.backgroundColor = colors[i % colors.length] + '33'; // 20% opacity
      ds.borderWidth = 2;
      ds.fill = true;
      ds.tension = 0.4;
  });

  acquisitionCharts.velocity = new Chart(ctx, {
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

function renderContributionChart(data) {
  const container = document.getElementById("source-contribution-chart");
  if (!container) return;
  
  if (data.labels.length === 0) {
    container.innerHTML = "<div class='text-muted p-4 text-center'>No data available</div>";
    return;
  }
  
  if (!document.getElementById("contributionCanvas")) {
      container.innerHTML = '<canvas id="contributionCanvas"></canvas>';
  }
  
  const ctx = document.getElementById("contributionCanvas").getContext("2d");
  
  if (acquisitionCharts.contribution) {
      acquisitionCharts.contribution.destroy();
  }
  
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899', '#14b8a6', '#6366f1'];
  
  acquisitionCharts.contribution = new Chart(ctx, {
      type: 'doughnut',
      data: {
          labels: data.labels,
          datasets: [{
              data: data.data,
              backgroundColor: colors,
              borderWidth: 1
          }]
      },
      options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'right' } }
      }
  });
}

function renderAuthorityChart(data) {
  const container = document.getElementById("authority-distribution-chart");
  if (!container) return;
  
  if (data.labels.length === 0) {
    container.innerHTML = "<div class='text-muted p-4 text-center'>No data available</div>";
    return;
  }
  
  if (!document.getElementById("authorityCanvas")) {
      container.innerHTML = '<canvas id="authorityCanvas"></canvas>';
  }
  
  const ctx = document.getElementById("authorityCanvas").getContext("2d");
  
  if (acquisitionCharts.authority) {
      acquisitionCharts.authority.destroy();
  }
  
  acquisitionCharts.authority = new Chart(ctx, {
      type: 'bar',
      data: {
          labels: data.labels,
          datasets: [{
              label: "Sources",
              data: data.data,
              backgroundColor: '#6366f1',
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

function renderCoverageMatrix(data) {
    const container = document.getElementById("category-source-matrix-container");
    if (!container) return;
    
    if (data.sources.length === 0) {
        container.innerHTML = "<div class='text-muted p-4 text-center'>No data available</div>";
        return;
    }
    
    let html = `
    <table class="dashboard-table w-full text-left border-collapse whitespace-nowrap">
        <thead>
            <tr class="bg-gray-50 border-b border-border text-sm text-muted uppercase tracking-wider">
                <th class="p-3 font-bold sticky left-0 bg-gray-50 z-10 border-r border-border">Category</th>
    `;
    
    data.sources.forEach(src => {
        html += `<th class="p-3 font-bold text-center">${src}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    data.rows.forEach(row => {
        html += `<tr class="border-b border-border hover:bg-gray-50">
            <td class="p-3 font-medium sticky left-0 bg-white z-10 border-r border-border hover:bg-gray-50">${row.category}</td>`;
            
        data.sources.forEach(src => {
            const count = row.counts[src] || 0;
            // Calculate a color opacity based on count
            let bgClass = "";
            let textClass = "text-muted";
            if (count > 50) { bgClass = "bg-blue-100"; textClass = "text-blue-800 font-bold"; }
            else if (count > 10) { bgClass = "bg-blue-50"; textClass = "text-blue-700 font-medium"; }
            else if (count > 0) { textClass = "text-gray-700"; }
            
            html += `<td class="p-3 text-center text-sm ${bgClass} ${textClass}">${count}</td>`;
        });
        
        html += `</tr>`;
    });
    
    html += `</tbody></table>`;
    container.innerHTML = html;
}
