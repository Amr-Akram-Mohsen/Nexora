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
