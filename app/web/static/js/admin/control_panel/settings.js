/**
 * Nexora Control Panel — Settings Management
 */

(function () {
  'use strict';

  document.addEventListener("DOMContentLoaded", () => {
    initSettings();
  });

function initSettings() {
  loadSystemInfo();
  bindCacheControls();
  bindMaintenanceMode();
  bindDangerZone();
  loadIntegrationsStatus();
  loadIngestionLogs();
}


// ==============================
// SYSTEM INFO
// ==============================
function loadSystemInfo() {
  const container = document.getElementById("system-info");
  if (!container) return;

  fetch('/admin/system/info')
    .then(res => {
      if (!res.ok) throw new Error("Failed to fetch system info");
      return res.json();
    })
    .then(info => {
      container.innerHTML = `
        <ul class="system-info-list">
          ${info.map(row => {
            // Backend now returns a plain `status` string (no HTML).
            // Apply a visual class locally based on the value (R-11).
            let valueHtml = escapeHtml(row.value);
            if (row.status) {
              const cls = row.status === 'online' ? 'status-ok'
                        : row.status === 'error'  ? 'status-error'
                        : 'status-pending';
              valueHtml = `<span class="integration-status ${cls}">${escapeHtml(row.value)}</span>`;
            }
            return `
              <li class="system-info-row">
                <span class="system-info-label">${escapeHtml(row.label)}</span>
                <span class="system-info-value">${valueHtml}</span>
              </li>
            `;
          }).join('')}
        </ul>
      `;
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `<p class="hint error-text">Failed to load system info.</p>`;
    });
}


// ==============================
// CACHE CONTROLS
// ==============================
function bindCacheControls() {
  const btn = document.getElementById("clear-cache-btn");
  if (!btn) return;

  btn.addEventListener("click", () => {
    btn.disabled = true;
    btn.textContent = "Clearing…";

    fetch('/admin/system/cache', { method: 'DELETE' })
      .then(res => {
        if (!res.ok) throw new Error("Failed to clear cache");
        return res.json();
      })
      .then(data => {
        showSettingsToast(data.message || "Cache cleared successfully.", "success");
      })
      .catch(err => {
        console.error(err);
        showSettingsToast("Failed to clear cache.", "error");
      })
      .finally(() => {
        btn.disabled = false;
        btn.textContent = "Clear Cache";
      });
  });
}


// ==============================
// MAINTENANCE MODE
// ==============================
function bindMaintenanceMode() {
  const toggle = document.getElementById("maintenance-toggle");
  const hint = document.getElementById("maintenance-status-hint");
  if (!toggle) return;

  // Fetch current status from backend
  fetch('/admin/system/maintenance')
    .then(res => res.json())
    .then(data => {
      toggle.checked = data.enabled;
      if (hint) {
        hint.innerHTML = `Maintenance mode is currently <strong>${data.enabled ? "enabled" : "disabled"}</strong>.`;
      }
    })
    .catch(err => console.error("Failed to load maintenance status", err));

  toggle.addEventListener("change", (e) => {
    const on = e.target.checked;
    const status = on ? "enabled" : "disabled";

    toggle.disabled = true;

    fetch('/admin/system/maintenance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ enabled: on })
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to update maintenance mode");
        return res.json();
      })
      .then(data => {
        if (hint) {
          hint.innerHTML = `Maintenance mode is currently <strong>${status}</strong>.`;
        }
        showSettingsToast(`Maintenance mode ${status}.`, on ? "warning" : "success");
      })
      .catch(err => {
        console.error(err);
        toggle.checked = !on;
        showSettingsToast("Failed to update maintenance mode.", "error");
      })
      .finally(() => {
        toggle.disabled = false;
      });
  });
}


// ==============================
// DANGER ZONE
// ==============================
function bindDangerZone() {
  const resetBtn = document.getElementById("reset-system-btn");
  if (!resetBtn) return;

  resetBtn.addEventListener("click", () => {
    if (typeof showModal === "function") {
      showModal(
        "⚠️ Reset System",
        "WARNING: This will clear all ingestion logs, API usage stats, and system cache. This action is irreversible. Are you absolutely sure?",
        () => {
          resetBtn.disabled = true;
          fetch('/admin/system/reset', { method: 'POST' })
            .then(res => {
              if (!res.ok) throw new Error("Reset failed");
              return res.json();
            })
            .then(data => {
              showSettingsToast(data.message || "System reset completed.", "success");
              loadIntegrationsStatus();
              loadIngestionLogs();
            })
            .catch(err => {
              console.error(err);
              showSettingsToast("System reset failed.", "error");
            })
            .finally(() => {
              resetBtn.disabled = false;
            });
        }
      );
    }
  });
}


// ==============================
// INTEGRATIONS
// ==============================
function loadIntegrationsStatus() {
  const container = document.getElementById("integrations-monitor");
  const template = document.getElementById("integration-row-template");
  if (!container || !template) return;

  fetch('/admin/ingestions/status')
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";
      if (!data || data.length === 0) {
        container.innerHTML = `<p class="hint">No integration activity yet. Run a fetch job to populate data.</p>`;
        return;
      }

      data.forEach(intg => {
        let statusClass = "status-ok";
        let statusText = "Active";
        if (intg.errors > 0) {
          statusClass = "status-error";
          statusText = "Error";
        } else if (intg.requests_today === 0 && !intg.last_fetch) {
          statusClass = "status-pending";
          statusText = "Pending";
        }

        const lastFetchStr = intg.last_fetch ? new Date(intg.last_fetch).toLocaleString() : "Never";

        const node = template.content.cloneNode(true);


        node.querySelector(".integration-name").textContent = intg.name.toUpperCase();

        const statusEl = node.querySelector(".integration-status");
        statusEl.textContent = statusText;
        statusEl.classList.add(statusClass);

        node.querySelector(".meta-requests").textContent = `Reqs Today: ${intg.requests_today}`;
        node.querySelector(".meta-last-fetch").textContent = `Last Fetch: ${lastFetchStr}`;

        container.appendChild(node);
      });
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `<p class="hint error-text">Failed to load integration status.</p>`;
    });
}

let allIngestionLogs = [];
let currentLogFilter = 'all';

function loadIngestionLogs() {
  const container = document.getElementById("ingestion-log-container");
  if (!container) return;

  fetch('/admin/ingestions/logs')
    .then(res => res.json())
    .then(logs => {
      allIngestionLogs = logs || [];
      renderIngestionLogs();
      bindLogFilters();
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `<p class="hint error-text">Failed to load ingestion logs.</p>`;
    });
}

// function renderIngestionLogs() {
//   const container = document.getElementById("ingestion-log-container");
//   const template = document.getElementById("ingestion-log-template");

//   if (!container || !template) return;

//   container.innerHTML = "";

//   const filteredLogs = allIngestionLogs.filter(log => {
//     if (currentLogFilter === 'all') return true;
//     return log.type === currentLogFilter;
//   });

//   if (filteredLogs.length === 0) {
//     container.innerHTML = `<p class="hint">No ingestion logs found for this filter.</p>`;
//     return;
//   }

//   const ul = document.createElement("ul");
//   ul.className = "activity-feed";

//   filteredLogs.forEach(log => {
//     const li = document.createElement("li");
//     li.className = "activity-item";

//     const timeAgo = log.time ? new Date(log.time).toLocaleString() : "Recently";
//     const statusClass = log.status === "Success" ? "status-ok" : "status-error";

//     li.innerHTML = `
//       <div class="activity-icon ${log.status === "Success" ? "icon-like" : "icon-dislike"}">
//         ${log.status === "Success" ? "✅" : "❌"}
//       </div>
//       <div class="activity-content">
//         <p class="activity-text">
//           <strong>${log.source}</strong> fetched <span class="activity-target">${log.category}</span>
//           <span class="integration-status ${statusClass}" style="float:right">${log.status}</span>
//           <span class="integration-status status-badge admin" style="float:right; margin-right: 0.5rem;">${log.type.toUpperCase()}</span>
//         </p>
//         <p class="activity-meta" style="margin-bottom:0.25rem;">Query: "${log.query}"</p>
//         <p class="activity-meta">${timeAgo} ${log.failures > 0 ? `• Failures: ${log.failures}` : ''}</p>
//       </div>
//     `;
//     ul.appendChild(li);
//   });

//   container.appendChild(ul);
// }

function renderIngestionLogs() {
  const container = document.getElementById("ingestion-log-container");
  const template = document.getElementById("log-item-template");
  if (!container || !template) return;

  container.innerHTML = "";

  const filteredLogs = allIngestionLogs.filter(log => {
    if (currentLogFilter === 'all') return true;
    return log.type === currentLogFilter;
  });

  if (filteredLogs.length === 0) {
    container.innerHTML = `<p class="hint">No ingestion logs found.</p>`;
    return;
  }

  const ul = document.createElement("ul");
  ul.className = "activity-feed";

  filteredLogs.forEach(log => {
    const node = template.content.cloneNode(true);

    const timeAgo = log.time ? new Date(log.time).toLocaleString() : "Recently";
    const isSuccess = log.status === "Success";

    const icon = node.querySelector(".activity-icon");
    icon.textContent = isSuccess ? "✅" : "❌";
    icon.classList.add(isSuccess ? "icon-like" : "icon-dislike");

    node.querySelector(".log-source").textContent = log.source;
    node.querySelector(".log-category").textContent = log.category;

    const statusEl = node.querySelector(".log-status");
    statusEl.textContent = log.status;
    statusEl.classList.add(isSuccess ? "status-ok" : "status-error");

    node.querySelector(".log-type").textContent = log.type.toUpperCase();

    node.querySelector(".log-query").textContent = `Query: "${log.query}"`;
    node.querySelector(".log-time").textContent =
      `${timeAgo}${log.failures > 0 ? ` • Failures: ${log.failures}` : ''}`;

    ul.appendChild(node);
  });

  container.appendChild(ul);
}

function bindLogFilters() {
  const btnAll = document.getElementById("filter-all-logs");
  const btnArticles = document.getElementById("filter-article-logs");
  const btnItems = document.getElementById("filter-item-logs");
  if (!btnAll) return;

  const btns = [btnAll, btnArticles, btnItems];

  btnAll.onclick = () => { currentLogFilter = 'all'; updateActiveTab(btns, btnAll); renderIngestionLogs(); };
  btnArticles.onclick = () => { currentLogFilter = 'article'; updateActiveTab(btns, btnArticles); renderIngestionLogs(); };
  btnItems.onclick = () => { currentLogFilter = 'item'; updateActiveTab(btns, btnItems); renderIngestionLogs(); };
}

function updateActiveTab(btns, activeBtn) {
  btns.forEach(b => {
    b.classList.remove("active");
  });
  activeBtn.classList.add("active");
}

// ==============================
// TOAST
// ==============================
function showSettingsToast(msg, type = "success") {
  showToast(msg, type);
}

})();
