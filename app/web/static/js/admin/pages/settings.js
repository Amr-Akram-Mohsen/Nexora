/**
 * Nexora Control Panel — Settings Management (Refactored)
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
    bindLogFilters();
  }

  // ==============================
  // SYSTEM INFO
  // ==============================
  function loadSystemInfo() {
    fetchAndInjectHtml('/admin/system/widget/info', 'system-info', 'Loading system info...');
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

      window.api.delete('/admin/system/cache')
        .then(data => {
          showSettingsToast(data.message || "Cache cleared successfully.", "success");
        })
        .catch(err => {
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
    window.api.get('/admin/system/maintenance')
      .then(data => {
        toggle.checked = data.enabled;
        if (hint) {
          hint.replaceChildren();
          hint.appendChild(document.createTextNode("Maintenance mode is currently "));
          const strong = document.createElement("strong");
          strong.textContent = data.enabled ? "enabled" : "disabled";
          hint.appendChild(strong);
          hint.appendChild(document.createTextNode("."));
        }
      })
      .catch(err => console.error("Failed to load maintenance status", err));

    toggle.addEventListener("change", (e) => {
      const on = e.target.checked;
      const status = on ? "enabled" : "disabled";

      toggle.disabled = true;

      window.api.post('/admin/system/maintenance', { enabled: on })
        .then(data => {
          if (hint) {
            hint.replaceChildren();
            hint.appendChild(document.createTextNode("Maintenance mode is currently "));
            const strong = document.createElement("strong");
            strong.textContent = status;
            hint.appendChild(strong);
            hint.appendChild(document.createTextNode("."));
          }
          showSettingsToast(`Maintenance mode ${status}.`, on ? "warning" : "success");
        })
        .catch(err => {
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
            window.api.post('/admin/system/reset')
              .then(data => {
                showSettingsToast(data.message || "System reset completed.", "success");
                loadIntegrationsStatus();
                loadIngestionLogs();
              })
              .catch(err => {
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
    fetchAndInjectHtml('/admin/system/widget/integrations', 'integrations-monitor', 'Loading status...');
  }

  // ==============================
  // INGESTION LOGS & FILTERS
  // ==============================
  let currentLogFilter = 'all';

  function loadIngestionLogs() {
    fetchAndInjectHtml(`/admin/system/widget/ingestion-logs?type=${currentLogFilter}`, 'ingestion-log-container', 'Loading logs...');
  }

  function bindLogFilters() {
    const btnAll = document.getElementById("filter-all-logs");
    const btnArticles = document.getElementById("filter-article-logs");
    const btnItems = document.getElementById("filter-item-logs");
    if (!btnAll) return;

    const btns = [btnAll, btnArticles, btnItems];

    btnAll.onclick = () => {
      currentLogFilter = 'all';
      updateActiveTab(btns, btnAll);
      loadIngestionLogs();
    };
    btnArticles.onclick = () => {
      currentLogFilter = 'article';
      updateActiveTab(btns, btnArticles);
      loadIngestionLogs();
    };
    btnItems.onclick = () => {
      currentLogFilter = 'item';
      updateActiveTab(btns, btnItems);
      loadIngestionLogs();
    };
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
