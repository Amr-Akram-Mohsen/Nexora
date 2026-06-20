/**
 * Nexora Control Panel — Users Management
 * Refactored: row HTML is server-rendered (Jinja partials).
 * JS only: fetch → inject HTML → delegate events.
 */

(function () {
  'use strict';

  window.usersController = null;

  // ── Action Handlers (called via event delegation on body) ─────
  function handleToggleAdmin(id, name, btn, modal) {
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    fetch(`/admin/users/${id}/toggle-admin`, { method: "POST" })
      .then(res => { if (!res.ok) throw new Error(); return res.json(); })
      .then(data => {
        showToast(data.is_admin ? `${name} is now an Admin` : `${name} is now a User`);
        window.usersController.load(window.usersController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(() => {
        showToast("Failed to update role.", "error");
        window.usersController.load(window.usersController.currentPage);
        if (modal) modal.classList.remove("active");
      });
  }

  function handleToggleActive(id, isCurrentlyActive, name, btn, modal) {
    const endpoint = isCurrentlyActive ? `/admin/users/${id}` : `/admin/users/${id}/activate`;
    const method   = isCurrentlyActive ? "DELETE" : "POST";
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    fetch(endpoint, { method })
      .then(res => { if (!res.ok) throw new Error(); return res.json(); })
      .then(() => {
        showToast(`${name} has been ${isCurrentlyActive ? "deactivated" : "activated"}.`);
        window.usersController.load(window.usersController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(() => {
        showToast("Failed to update status.", "error");
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
        fetch(`/admin/users/${id}`, { method: "DELETE" })
          .then(res => { if (!res.ok) throw new Error(); return res.json(); })
          .then(() => {
            showToast(`${name} has been removed.`);
            window.usersController.load(window.usersController.currentPage);
            if (modal) modal.classList.remove("active");
          })
          .catch(() => {
            showToast("Failed to delete user.", "error");
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
      filterIds: ["user-role-filter"],
      defaultPerPage: 25,
      colspan: 7,
      autoInit: false
    });
    window.usersController.init();

    // Event delegation: inspect modal or detail page action buttons
    document.body.addEventListener("click", e => {
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
    });
  });
})();
