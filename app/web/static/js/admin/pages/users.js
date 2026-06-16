/**
 * Nexora Control Panel — Users Management
 * Refactored: row HTML is server-rendered (Jinja partials).
 * JS only: fetch → inject HTML → delegate events.
 */

(function () {
  'use strict';

  let listController;

  // ── Inspect Modal (server-rendered body) ──────────────────────
  function openInspectModal(userId) {
    const modal   = document.getElementById("inspect-user-modal");
    const body    = document.getElementById("inspect-user-modal-body");
    const titleEl = document.getElementById("inspect-user-modal-title");
    if (!modal || !body) return;

    body.innerHTML = '<div class="dashboard-loading"><div class="spinner"></div><p>Loading…</p></div>';
    titleEl.textContent = "Inspect User";
    modal.classList.add("active");

    fetch(`/admin/users/${userId}/inspect`)
      .then(res => res.text())
      .then(html => {
        body.innerHTML = html;
        // Action buttons rendered in partial use data-action attributes — delegation handles them
      })
      .catch(() => {
        body.innerHTML = "<p class='text-muted'>Could not load user details.</p>";
      });
  }

  // ── Action Handlers (called via event delegation on body) ─────
  function handleToggleAdmin(id, name, btn, modal) {
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    fetch(`/admin/users/${id}/toggle-admin`, { method: "POST" })
      .then(res => { if (!res.ok) throw new Error(); return res.json(); })
      .then(data => {
        showToast(data.is_admin ? `${name} is now an Admin` : `${name} is now a User`);
        listController.load(listController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(() => {
        showToast("Failed to update role.", "error");
        listController.load(listController.currentPage);
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
        listController.load(listController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(() => {
        showToast("Failed to update status.", "error");
        listController.load(listController.currentPage);
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
            listController.load(listController.currentPage);
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
    listController = new AdminListController({
      domain: "users",
      endpoint: "/admin/users/",
      rowsEndpoint: "/admin/users/rows",   // ← HTML partial mode
      tbodyId: "users-table-body",
      searchId: "user-search",
      filterIds: ["user-role-filter"],
      perPageId: "users-per-page",
      prevBtnId: "users-prev-btn",
      nextBtnId: "users-next-btn",
      indicatorId: "users-page-indicator",
      infoId: "users-pagination-info",
      countId: "users-count",
      defaultPerPage: 25,
      colspan: 5,
      autoInit: false
    });
    listController.init();

    // Event delegation: table body rows (inspect button)
    const tableBody = document.getElementById("users-table-body");
    if (tableBody) {
      tableBody.addEventListener("click", e => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        if (btn.dataset.action === "inspect-user") {
          openInspectModal(parseInt(btn.dataset.id, 10));
        }
      });
    }

    // Event delegation: inspect modal action buttons (rendered server-side in _inspect.html)
    const modal = document.getElementById("inspect-user-modal");
    if (modal) {
      modal.addEventListener("click", e => {
        const btn  = e.target.closest("[data-action]");
        if (!btn) return;
        const { action, id, name } = btn.dataset;
        const uid = parseInt(id, 10);

        if (action === "toggle-admin") {
          handleToggleAdmin(uid, name, btn, modal);
        } else if (action === "toggle-active") {
          const isActive = btn.dataset.isActive === "true";
          handleToggleActive(uid, isActive, name, btn, modal);
        } else if (action === "delete-user") {
          handleDeleteUser(uid, name, btn, modal);
        }
      });
    }
  });
})();
