/**
 * Nexora Control Panel — Users Management
 */

(function () {
  'use strict';

  let listController;
  let loadedUsers = [];

  function renderUserRow(user) {
    const template = document.getElementById("users-row-template");
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector("tr");
    tr.id = `user-row-${user.id}`;

    clone.querySelector(".user-cell-name").innerHTML = user.name ? escapeHtml(user.name) : '<em>No name</em>';
    clone.querySelector(".user-cell-email").textContent = user.email;

    // Badges
    const roleCell = clone.querySelector(".user-role-cell");
    roleCell.innerHTML = user.is_admin
      ? `<span class="status-badge admin">Admin</span>`
      : `<span class="status-badge user">User</span>`;

    const statusCell = clone.querySelector(".user-status-cell");
    statusCell.innerHTML = user.is_active
      ? `<span class="status-badge active">Active</span>`
      : `<span class="status-badge inactive">Inactive</span>`;

    const joinedCell = clone.querySelector(".user-joined-cell");
    joinedCell.textContent = user.created_at ? formatDate(user.created_at) : "—";

    // Buttons
    const inspectBtn = clone.querySelector(".user-action-inspect");
    inspectBtn.dataset.id = user.id;

    return tr;
  }

  // Action logic
  function handleToggleAdmin(id, name, btn, modal) {
    if (btn) { btn.disabled = true; btn.textContent = "…"; }

    fetch(`/admin/users/${id}/toggle-admin`, { method: "POST" })
      .then(res => {
        if (!res.ok) throw new Error("Toggle admin failed");
        return res.json();
      })
      .then(data => {
        showToast(data.is_admin ? `${name} is now an Admin` : `${name} is now a User`);
        listController.load(listController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(err => {
        console.error(err);
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
      .then(res => {
        if (!res.ok) throw new Error("Toggle active failed");
        return res.json();
      })
      .then(() => {
        const action = isCurrentlyActive ? "deactivated" : "activated";
        showToast(`${name} has been ${action}.`);
        listController.load(listController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(err => {
        console.error(err);
        showToast("Failed to update status.", "error");
        listController.load(listController.currentPage);
        if (modal) modal.classList.remove("active");
      });
  }

  function confirmDeleteUser(id, name, btn, modal) {
    showModal(
      "Delete User",
      `Are you sure you want to permanently delete "${name}"? This action cannot be undone.`,
      () => performDeleteUser(id, name, btn, modal)
    );
  }

  function performDeleteUser(id, name, btn, modal) {
    if (btn) { btn.disabled = true; btn.textContent = "Deleting…"; }
    fetch(`/admin/users/${id}`, { method: "DELETE" })
      .then(res => {
        if (!res.ok) throw new Error("Delete failed");
        return res.json();
      })
      .then(() => {
        showToast(`${name} has been removed.`);
        listController.load(listController.currentPage);
        if (modal) modal.classList.remove("active");
      })
      .catch(err => {
        console.error(err);
        showToast("Failed to delete user.", "error");
        if (btn) { btn.disabled = false; btn.textContent = "🗑 Delete User"; }
      });
  }

  function showInspectModal(user) {
    const modal = document.getElementById("inspect-user-modal");
    const body = document.getElementById("inspect-user-modal-body");
    const titleEl = document.getElementById("inspect-user-modal-title");

    titleEl.textContent = `Inspect User: ${user.name || user.email}`;

    const template = document.getElementById("user-inspect-template");
    const clone = template.content.cloneNode(true);

    clone.querySelector(".inspect-id").textContent = `#${user.id}`;
    clone.querySelector(".inspect-name").textContent = user.name || "—";
    clone.querySelector(".inspect-email").textContent = user.email;

    const roleBadge = clone.querySelector(".inspect-role");
    roleBadge.textContent = user.is_admin ? "Admin" : "User";
    roleBadge.className = `inspect-role status-badge ${user.is_admin ? 'admin' : 'user'}`;

    const statusBadge = clone.querySelector(".inspect-status");
    statusBadge.textContent = user.is_active ? "Active" : "Inactive";
    statusBadge.className = `inspect-status status-badge ${user.is_active ? 'active' : 'inactive'}`;

    clone.querySelector(".inspect-joined").textContent = user.created_at ? formatDate(user.created_at) : "—";

    const nameAttr = (user.name || user.email).replace(/"/g, '&quot;');

    const adminBtn = clone.querySelector(".inspect-toggle-admin-btn");
    if (adminBtn) {
      adminBtn.dataset.id = user.id;
      adminBtn.dataset.name = nameAttr;
      adminBtn.textContent = user.is_admin ? 'Demote to User' : 'Promote to Admin';
      adminBtn.addEventListener("click", () => {
        handleToggleAdmin(user.id, user.name || user.email, adminBtn, modal);
      });
    }

    const activeBtn = clone.querySelector(".inspect-toggle-active-btn");
    if (activeBtn) {
      activeBtn.dataset.id = user.id;
      activeBtn.dataset.name = nameAttr;
      activeBtn.textContent = user.is_active ? 'Deactivate Account' : 'Activate Account';
      activeBtn.addEventListener("click", () => {
        handleToggleActive(user.id, user.is_active, user.name || user.email, activeBtn, modal);
      });
    }

    const deleteBtn = clone.querySelector(".inspect-delete-btn");
    if (deleteBtn) {
      deleteBtn.dataset.id = user.id;
      deleteBtn.dataset.name = nameAttr;
      deleteBtn.addEventListener("click", () => {
        confirmDeleteUser(user.id, user.name || user.email, deleteBtn, modal);
      });
    }

    body.innerHTML = "";
    body.appendChild(clone);
    modal.classList.add("active");
  }

  // Setup Event Delegation
  document.addEventListener("DOMContentLoaded", () => {
    listController = new AdminListController({
      domain: "users",
      endpoint: "/admin/users/",
      tbodyId: "users-table-body",
      searchId: "user-search",
      filterIds: ["user-role-filter"],
      perPageId: "users-per-page",
      prevBtnId: "users-prev-btn",
      nextBtnId: "users-next-btn",
      indicatorId: "users-page-indicator",
      infoId: "users-pagination-info",
      countId: "users-count",
      rowTemplateId: "users-row-template",
      defaultPerPage: 25,
      colspan: 5,
      renderRow: renderUserRow,
      onLoaded: (data) => {
        loadedUsers = data.items || [];
      },
      autoInit: false
    });
    listController.init();

    const tableBody = document.getElementById("users-table-body");
    if (tableBody) {
      tableBody.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const { action, id } = btn.dataset;
        const userId = parseInt(id, 10);

        if (action === "inspect-user") {
          const user = loadedUsers.find(u => u.id === userId);
          if (user) {
            showInspectModal(user);
          }
        }
      });
    }

    // Close inspect user modal overlay
    const inspectCloseBtn = document.getElementById("inspect-user-close-btn");
    if (inspectCloseBtn) {
      inspectCloseBtn.addEventListener("click", () => {
        document.getElementById("inspect-user-modal").classList.remove("active");
      });
    }

    const inspectModalOverlay = document.getElementById("inspect-user-modal");
    if (inspectModalOverlay) {
      inspectModalOverlay.addEventListener("click", (e) => {
        if (e.target === inspectModalOverlay) {
          inspectModalOverlay.classList.remove("active");
        }
      });
    }
  });
})();
