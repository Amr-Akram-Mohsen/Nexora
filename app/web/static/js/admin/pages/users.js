/**
 * Nexora Control Panel — Users Management
 * Refactored: row HTML is server-rendered (Jinja partials).
 * JS only: fetch → inject HTML → delegate events.
 */

(function () {
  'use strict';

  window.usersController = null;

  // ── Action Handlers ─────
  function handleToggleAdmin(id, name, btn, modal) {
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    window.api.post(`/admin/users/${id}/toggle-admin`)
      .then(data => {
        showToast(data.is_admin ? `${name} is now an Admin` : `${name} is now a User`);
        window.usersController.load(window.usersController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(() => {
        window.usersController.load(window.usersController.currentPage);
        if (modal) modal.classList.remove("active");
      });
  }

  function handleToggleActive(id, isCurrentlyActive, name, btn, modal) {
    const endpoint = isCurrentlyActive ? `/admin/users/${id}` : `/admin/users/${id}/activate`;
    const method = isCurrentlyActive ? window.api.delete : window.api.post;
    
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    method(endpoint)
      .then(() => {
        showToast(`${name} has been ${isCurrentlyActive ? "deactivated" : "activated"}.`);
        window.usersController.load(window.usersController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(() => {
        window.usersController.load(window.usersController.currentPage);
        if (modal) modal.classList.remove("active");
      });
  }

  function handleDeleteUser(id, name, btn, modal) {
    showModal(
      "Delete User",
      `Are you sure you want to permanently delete "${name}"? This action cannot be undone.`,
      () => {
        if (btn) { btn.disabled = true; btn.textContent = "Deleting…"; }
        window.api.delete(`/admin/users/${id}`)
          .then(() => {
            showToast(`${name} has been removed.`);
            window.usersController.load(window.usersController.currentPage);
            if (modal) modal.classList.remove("active");
          })
          .catch(() => {
            if (btn) { btn.disabled = false; btn.textContent = "🗑 Delete User"; }
          });
      }
    );
  }

  // ── DOMContentLoaded ──────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    window.usersController = new AdminListController({
      domain: "users",
      endpoint: "/admin/users/",
      rowsEndpoint: "/admin/users/rows",
      filterIds: [
        "user-role-filter",
        "user-status-filter",
        "user-verified-filter",
        "user-subscription-filter",
        "user-provider-filter"
      ],
      defaultPerPage: 25,
      colspan: 8,
      autoInit: false,
      onLoaded: function(data) {
        if (data.headers) {
          const active = data.headers.get("X-Active-Count");
          const admins = data.headers.get("X-Admin-Count");
          const verified = data.headers.get("X-Verified-Count");
          const subbed = data.headers.get("X-Subscribed-Count");
          
          if (active !== null) {
            const el = document.getElementById("summary-active-count");
            if (el) el.textContent = `Active: ${parseInt(active).toLocaleString()}`;
          }
          if (admins !== null) {
            const el = document.getElementById("summary-admins-count");
            if (el) el.textContent = `Admins: ${parseInt(admins).toLocaleString()}`;
          }
          if (verified !== null) {
            const el = document.getElementById("summary-verified-count");
            if (el) el.textContent = `Verified: ${parseInt(verified).toLocaleString()}`;
          }
          if (subbed !== null) {
            const el = document.getElementById("summary-subscribed-count");
            if (el) el.textContent = `Subscribed: ${parseInt(subbed).toLocaleString()}`;
          }
        }
      }
    });

    let currentSortBy = '';
    let currentSortDir = 'desc';

    const originalGetFilters = window.usersController.getFilters.bind(window.usersController);
    window.usersController.getFilters = function() {
      const filters = originalGetFilters();
      if (currentSortBy) {
        filters.sort_by = currentSortBy;
        filters.sort_dir = currentSortDir;
      }
      return filters;
    };

    window.usersController.init();

    // Event delegation: table header sorting
    document.getElementById("users-table").addEventListener("click", e => {
      const th = e.target.closest("th[data-sort]");
      if (!th) return;
      
      const sortBy = th.dataset.sort;
      if (currentSortBy === sortBy) {
        currentSortDir = currentSortDir === 'desc' ? 'asc' : 'desc';
      } else {
        currentSortBy = sortBy;
        currentSortDir = 'desc';
      }
      
      // Update arrows
      document.querySelectorAll("th[data-sort]").forEach(col => {
          col.textContent = col.textContent.replace(/ [↑↓↕]/, ' ↕');
      });
      th.textContent = th.textContent.replace(/ [↑↓↕]/, currentSortDir === 'desc' ? ' ↓' : ' ↑');
      
      window.usersController.load(1);
    });

    // Event delegation: inspect modal or detail page action buttons
    function userActionHandler(e) {
      const btn  = e.target.closest("[data-action]");
      if (!btn) return;
      const { action, id, name } = btn.dataset;
      const uid = parseInt(id, 10);
      const modal = document.getElementById("inspect-user-modal");

      if (action === "toggle-admin") {
        handleToggleAdmin(uid, name, btn, modal);
      } else if (action === "toggle-active") {
        const isActive = btn.dataset.isActive === "true";
        handleToggleActive(uid, isActive, name, btn, modal);
      } else if (action === "delete-user") {
        handleDeleteUser(uid, name, btn, modal);
      }
    }

    const tableContainer = document.getElementById("users-table");
    if (tableContainer) tableContainer.addEventListener("click", userActionHandler);

    const inspectModal = document.getElementById("inspect-user-modal");
    if (inspectModal) inspectModal.addEventListener("click", userActionHandler);

    // ── Chart Initialization ──────────────────────────────────────
    function initUserCharts() {
      window.api.get('/admin/users/stats')
        .then(data => {
          if (document.getElementById('userGrowthChart')) {
            window.nexoraCharts.render('userGrowthChart', 'line', {
              labels: Object.keys(data.growth),
              datasets: [{
                label: 'New Registrations',
                data: Object.values(data.growth),
                borderColor: window.nexoraCharts.getColors()[0],
                backgroundColor: 'rgba(93, 95, 239, 0.1)',
                tension: 0.3,
                fill: true
              }]
            }, { plugins: { legend: { display: false } } });
          }

          if (document.getElementById('roleDistributionChart')) {
            window.nexoraCharts.render('roleDistributionChart', 'doughnut', {
              labels: Object.keys(data.roles),
              datasets: [{
                data: Object.values(data.roles),
                backgroundColor: window.nexoraCharts.getColors().slice(1, 3)
              }]
            });
          }

          if (document.getElementById('providerSplitChart')) {
            window.nexoraCharts.render('providerSplitChart', 'doughnut', {
              labels: Object.keys(data.providers).map(p => p.charAt(0).toUpperCase() + p.slice(1)),
              datasets: [{
                data: Object.values(data.providers),
                backgroundColor: window.nexoraCharts.getColors().slice(3, 6)
              }]
            });
          }
        });
    }

    initUserCharts();
  });
})();
