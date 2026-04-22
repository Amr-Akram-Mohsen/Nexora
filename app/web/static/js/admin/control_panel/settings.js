/**
 * Nexora Control Panel - Settings Management
 */

document.addEventListener("DOMContentLoaded", () => {
  initSettings();
});

function initSettings() {
  // --- TODO: Fetch actual system settings from API when available ---
  // fetch('/api/settings').then(...)

  // Cache Controls
  const clearCacheBtn = document.getElementById("clear-cache-btn");
  if (clearCacheBtn) {
    clearCacheBtn.addEventListener("click", () => {
      // TODO: Implement server-side cache clearing API
      console.log("Clear cache requested");
      alert("Cache clearing functionality is not yet connected to the backend.");
    });
  }

  // Maintenance Mode
  const maintenanceToggle = document.getElementById("maintenance-toggle");
  if (maintenanceToggle) {
    maintenanceToggle.addEventListener("change", (e) => {
      // TODO: Implement maintenance mode toggle API
      const status = e.target.checked ? "enabled" : "disabled";
      console.log(`Maintenance mode ${status} requested`);
      // UI only feedback since backend is missing
    });
  }

  // Reset System (Danger Zone)
  const resetBtn = document.getElementById("reset-system-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (typeof showModal === "function") {
        showModal(
          "Reset System",
          "WARNING: This will reset all system configurations. This action is irreversible. Are you sure?",
          () => {
            // TODO: Implement system reset API
            console.warn("System reset requested");
          }
        );
      } else if (confirm("DANGER: Are you sure you want to reset the system?")) {
        console.warn("System reset requested");
      }
    });
  }

  // Load basic system info (Placeholder since no API exists)
  loadSystemInfo();
}

function loadSystemInfo() {
  const container = document.getElementById("system-info");
  if (!container) return;

  // --- TODO: Replace with real system metrics API ---
  container.innerHTML = `
    <ul style="list-style: none; padding: 0; margin: 0; font-size: 0.875rem; color: var(--muted-foreground)">
      <li style="margin-bottom: 0.5rem"><strong>Backend Status:</strong> <span style="color: green">● Online</span></li>
      <li style="margin-bottom: 0.5rem"><strong>Version:</strong> 1.2.0-restructured</li>
      <li style="margin-bottom: 0.5rem"><strong>Environment:</strong> Development</li>
      <li><small>API endpoints for system settings are pending backend implementation.</small></li>
    </ul>
  `;
}
