/**
 * Nexora Control Panel — Settings Management
 */

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
  bindIntegrationActions();
}


// ==============================
// SYSTEM INFO
// ==============================
function loadSystemInfo() {
  const container = document.getElementById("system-info");
  if (!container) return;

  // Simulated — replace with real /api/system/info when available
  const info = [
    { label: "Backend Status",  value: `<span style="color:var(--success,#22c55e)">● Online</span>` },
    { label: "Version",         value: "1.3.0" },
    { label: "Environment",     value: "Development" },
    { label: "Python",          value: "3.x / Flask" },
    { label: "Database",        value: "PostgreSQL (SQLAlchemy)" },
  ];

  container.innerHTML = `
    <ul class="system-info-list">
      ${info.map(row => `
        <li class="system-info-row">
          <span class="system-info-label">${row.label}</span>
          <span class="system-info-value">${row.value}</span>
        </li>
      `).join("")}
    </ul>
    <p class="hint" style="margin-top:1rem;">Live metrics endpoint is pending backend implementation.</p>
  `;
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

    // TODO: replace with fetch('/api/system/cache', { method: 'DELETE' }) when ready
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = "Clear Cache";
      showSettingsToast("Cache cleared successfully.", "success");
    }, 900);
  });
}


// ==============================
// MAINTENANCE MODE
// ==============================
function bindMaintenanceMode() {
  const toggle = document.getElementById("maintenance-toggle");
  const hint = document.getElementById("maintenance-status-hint");
  if (!toggle) return;

  toggle.addEventListener("change", (e) => {
    const on = e.target.checked;
    const status = on ? "enabled" : "disabled";

    if (hint) {
      hint.innerHTML = `Maintenance mode is currently <strong>${status}</strong>.`;
    }

    showSettingsToast(`Maintenance mode ${status}. (Backend connection pending)`, on ? "warning" : "success");

    // TODO: fetch('/api/system/maintenance', { method: 'POST', body: JSON.stringify({enabled: on}) })
    console.log(`[Settings] Maintenance mode ${status}`);
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
        "WARNING: This will reset all system configurations. This action is irreversible. Are you absolutely sure?",
        () => {
          showSettingsToast("System reset requested. (Backend connection pending)", "error");
          console.warn("[Settings] System reset requested");
        }
      );
    } else if (confirm("DANGER: Are you sure you want to reset the system?")) {
      showSettingsToast("System reset requested. (Backend connection pending)", "error");
    }
  });
}


// ==============================
// INTEGRATIONS
// ==============================
function loadIntegrationsStatus() {
  const container = document.getElementById("integrations-monitor");
  if (!container) return;

  fetch('/api/dashboard/integrations/status')
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";
      if (!data || data.length === 0) {
        container.innerHTML = `<p class="hint">No integrations found.</p>`;
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

        const row = document.createElement("div");
        row.className = "integration-row";
        row.innerHTML = `
          <span class="integration-name">${intg.name.toUpperCase()}</span>
          <span class="integration-status ${statusClass}">${statusText}</span>
          <span class="integration-meta" style="flex:1; text-align:right;">
            Reqs Today: <strong>${intg.requests_today}</strong>
            <span style="margin:0 0.5rem;color:var(--border);">|</span>
            Last Fetch: ${lastFetchStr}
          </span>
        `;
        container.appendChild(row);
      });
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `<p class="hint" style="color:var(--brand-red);">Failed to load integration status.</p>`;
    });
}

function loadIngestionLogs() {
  const container = document.getElementById("ingestion-log-container");
  if (!container) return;

  fetch('/api/dashboard/integrations/logs')
    .then(res => res.json())
    .then(logs => {
      container.innerHTML = "";
      if (!logs || logs.length === 0) {
        container.innerHTML = `<p class="hint">No ingestion logs found.</p>`;
        return;
      }
      
      const ul = document.createElement("ul");
      ul.className = "activity-feed";
      
      logs.forEach(log => {
        const li = document.createElement("li");
        li.className = "activity-item";
        
        const timeAgo = log.time ? new Date(log.time).toLocaleString() : "Recently";
        const statusClass = log.status === "Success" ? "status-ok" : "status-error";
        
        li.innerHTML = `
          <div class="activity-icon ${log.status === "Success" ? "icon-like" : "icon-dislike"}">
            ${log.status === "Success" ? "✅" : "❌"}
          </div>
          <div class="activity-content">
            <p class="activity-text">
              <strong>${log.source}</strong> fetched <span class="activity-target">${log.category}</span>
              <span class="integration-status ${statusClass}" style="float:right">${log.status}</span>
            </p>
            <p class="activity-meta" style="margin-bottom:0.25rem;">Query: "${log.query}"</p>
            <p class="activity-meta">${timeAgo} ${log.failures > 0 ? `• Failures: ${log.failures}` : ''}</p>
          </div>
        `;
        ul.appendChild(li);
      });
      
      container.appendChild(ul);
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `<p class="hint" style="color:var(--brand-red);">Failed to load ingestion logs.</p>`;
    });
}

function bindIntegrationActions() {
  const actions = [
    { id: "run-ingestion-btn", endpoint: "/api/dashboard/run-ingestion" },
    { id: "run-cleaner-btn", endpoint: "/api/dashboard/run-cleaner" },
    { id: "run-enrichment-btn", endpoint: "/api/dashboard/run-enrichment" }
  ];

  actions.forEach(act => {
    const btn = document.getElementById(act.id);
    if (!btn) return;
    btn.addEventListener("click", () => {
      btn.disabled = true;
      const originalText = btn.textContent;
      btn.textContent = "Running…";

      fetch(act.endpoint, { method: "POST" })
        .then(async (res) => {
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.message || "Task failed.");
          }
          return data;
        })
        .then(data => {
          showSettingsToast(data.message || "Task completed successfully.", "success");
        })
        .catch(err => {
          console.error(err);
          showSettingsToast(err.message || "Task failed to run.", "error");
        })
        .finally(() => {
          btn.disabled = false;
          btn.textContent = originalText;
          loadIntegrationsStatus();
          loadIngestionLogs();
        });
    });
  });
}

// ==============================
// TOAST
// ==============================
function showSettingsToast(msg, type = "success") {
  // Delegate to core.js if available
  if (typeof showToast === "function") {
    showToast(msg, type);
    return;
  }

  const toast = document.getElementById("settings-toast");
  if (!toast) return;

  toast.textContent = msg;
  toast.className = `settings-toast settings-toast-${type} settings-toast-show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("settings-toast-show"), 3200);
}
