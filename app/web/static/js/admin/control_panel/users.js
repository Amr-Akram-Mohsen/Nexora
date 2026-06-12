/**
 * Nexora Control Panel — Users Management
 *
 * Updated to handle the paginated API response envelope
 * {items, page, pages, total, per_page} (R-09).
 */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────
  let currentPage = 1;
  let totalPages  = 1;
  let perPage     = 25;

  document.addEventListener("DOMContentLoaded", () => {
    fetchUsers(1);

    // Search
    const searchInput = document.getElementById("user-search");
    if (searchInput) {
      let debounce;
      searchInput.addEventListener("input", (e) => {
        clearTimeout(debounce);
        debounce = setTimeout(() => fetchUsers(1), 400);
      });
    }

    // Role filter
    const roleFilter = document.getElementById("user-role-filter");
    if (roleFilter) {
      roleFilter.addEventListener("change", () => fetchUsers(1));
    }

    // Refresh
    const refreshBtn = document.getElementById("refresh-users-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => fetchUsers(currentPage));
    }

    // Pagination controls
    const prevBtn = document.getElementById("users-prev-btn");
    const nextBtn = document.getElementById("users-next-btn");
    if (prevBtn) prevBtn.addEventListener("click", () => { if (currentPage > 1) fetchUsers(currentPage - 1); });
    if (nextBtn) nextBtn.addEventListener("click", () => { if (currentPage < totalPages) fetchUsers(currentPage + 1); });

    // Table click event delegation
    const tableBody = document.getElementById("users-table-body");
    if (tableBody) {
      tableBody.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const { action, id, name } = btn.dataset;
        const userId = parseInt(id, 10);

        if (action === "toggle-admin") {
          handleToggleAdmin(userId, name);
        } else if (action === "toggle-active") {
          const isCurrentlyActive = btn.dataset.active === "true";
          handleToggleActive(userId, isCurrentlyActive, name);
        } else if (action === "delete-user") {
          confirmDeleteUser(userId, name);
        }
      });
    }
  });

  function getSearchValue() {
    return document.getElementById("user-search")?.value || "";
  }

  function getRoleFilter() {
    return document.getElementById("user-role-filter")?.value || "";
  }


  /**
   * Fetch users from the API (paginated).
   */
  function fetchUsers(page) {
    currentPage = page || 1;
    const tableBody = document.getElementById("users-table-body");
    if (!tableBody) return;

    tableBody.innerHTML = getTableSpinnerHtml(5, "Loading users…", "loading-height-sm");

    const params = new URLSearchParams({ page: currentPage, per_page: perPage });
    const search = getSearchValue();
    const role   = getRoleFilter();
    if (search.trim()) params.append("search", search.trim());
    if (role)          params.append("role", role);

    fetch(`/admin/users/?${params}`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch users");
        return res.json();
      })
      .then(data => {
        // data = {items, page, pages, total, per_page}
        const users = data.items || [];
        totalPages  = data.pages || 1;
        const total = data.total || 0;
        const from  = ((currentPage - 1) * perPage) + 1;
        const to    = Math.min(currentPage * perPage, total);

        renderUsersTable(users);
        updatePagination(total, from, to);
      })
      .catch(err => {
        console.error(err);
        tableBody.innerHTML = getTableErrorStateHtml(5, "Error loading users. Please try again.", "loading-height-sm");
      });
  }

  function updatePagination(total, from, to) {
    const countEl = document.getElementById("users-count");
    const infoEl  = document.getElementById("users-pagination-info");
    const pageEl  = document.getElementById("users-page-indicator");
    const prevBtn = document.getElementById("users-prev-btn");
    const nextBtn = document.getElementById("users-next-btn");

    if (countEl) countEl.textContent = total.toLocaleString();
    if (infoEl)  infoEl.textContent  = `Showing ${total ? from : 0} to ${to} of ${total.toLocaleString()} users`;
    if (pageEl)  pageEl.textContent  = `Page ${currentPage} of ${totalPages}`;
    if (prevBtn) prevBtn.disabled    = currentPage <= 1;
    if (nextBtn) nextBtn.disabled    = currentPage >= totalPages;
  }


  /**
   * Render user rows into the table.
   */
  function renderUsersTable(users) {
    const tableBody = document.getElementById("users-table-body");
    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (users.length === 0) {
      tableBody.innerHTML = getTableEmptyStateHtml(5, "No users found.", "Try adjusting your filters.", "loading-height-sm");
      return;
    }

    users.forEach(user => {
      const row = document.createElement("tr");
      row.id = `user-row-${user.id}`;

      const isActiveLabel = user.is_active
        ? `<span class="status-badge active">Active</span>`
        : `<span class="status-badge inactive">Inactive</span>`;

      const roleLabel = user.is_admin
        ? `<span class="status-badge admin">Admin</span>`
        : `<span class="status-badge user">User</span>`;

      const joinDate = user.created_at
        ? new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
        : "—";

      row.innerHTML = `
        <td>
          <div class="user-cell-name">${user.name || '<em>No name</em>'}</div>
          <div class="user-cell-email">${user.email}</div>
        </td>
        <td>${roleLabel}</td>
        <td>${isActiveLabel}</td>
        <td>${joinDate}</td>
        <td>
          <div class="user-actions-group">
            <button class="user-action-btn user-action-toggle-admin"
              data-action="toggle-admin"
              data-id="${user.id}"
              data-name="${(user.name || user.email).replace(/"/g, '&quot;')}"
              title="${user.is_admin ? 'Remove Admin' : 'Make Admin'}">
              ${user.is_admin ? '⬇ Demote' : '⬆ Promote'}
            </button>
            <button class="user-action-btn user-action-toggle-active"
              data-action="toggle-active"
              data-id="${user.id}"
              data-active="${user.is_active}"
              data-name="${(user.name || user.email).replace(/"/g, '&quot;')}"
              title="${user.is_active ? 'Deactivate' : 'Activate'}">
              ${user.is_active ? '🚫 Deactivate' : '✅ Activate'}
            </button>
            <button class="user-action-btn user-action-delete"
              data-action="delete-user"
              data-id="${user.id}"
              data-name="${(user.name || user.email).replace(/"/g, '&quot;')}"
              title="Delete user">
              🗑 Delete
            </button>
          </div>
        </td>
      `;

      tableBody.appendChild(row);
    });
  }


  /**
   * Toggle admin role.
   */
  function handleToggleAdmin(id, name) {
    const label = document.querySelector(`#user-row-${id} .user-action-toggle-admin`);
    if (label) { label.disabled = true; label.textContent = "…"; }

    fetch(`/admin/users/${id}/toggle-admin`, { method: "POST" })
      .then(res => {
        if (!res.ok) throw new Error("Toggle admin failed");
        return res.json();
      })
      .then(data => {
        showToastFeedback(data.is_admin ? `${name} is now an Admin` : `${name} is now a User`);
        fetchUsers(currentPage);
      })
      .catch(err => {
        console.error(err);
        showToastFeedback("Failed to update role.", "error");
        fetchUsers(currentPage);
      });
  }


  /**
   * Toggle active status.
   */
  function handleToggleActive(id, isCurrentlyActive, name) {
    const endpoint = isCurrentlyActive ? `/admin/users/${id}` : `/admin/users/${id}/activate`;
    const method   = isCurrentlyActive ? "DELETE" : "POST";

    const btn = document.querySelector(`#user-row-${id} .user-action-toggle-active`);
    if (btn) { btn.disabled = true; btn.textContent = "…"; }

    fetch(endpoint, { method })
      .then(res => {
        if (!res.ok) throw new Error("Toggle active failed");
        return res.json();
      })
      .then(() => {
        const action = isCurrentlyActive ? "deactivated" : "activated";
        showToastFeedback(`${name} has been ${action}.`);
        fetchUsers(currentPage);
      })
      .catch(err => {
        console.error(err);
        showToastFeedback("Failed to update status.", "error");
        fetchUsers(currentPage);
      });
  }


  /**
   * Confirm and delete a user.
   */
  function confirmDeleteUser(id, name) {
    showModal(
      "Delete User",
      `Are you sure you want to permanently delete "${name}"? This action cannot be undone.`,
      () => performDeleteUser(id, name)
    );
  }

  function performDeleteUser(id, name) {
    fetch(`/admin/users/${id}`, { method: "DELETE" })
      .then(res => {
        if (!res.ok) throw new Error("Delete failed");
        return res.json();
      })
      .then(() => {
        showToastFeedback(`${name} has been removed.`);
        fetchUsers(currentPage);
      })
      .catch(err => {
        console.error(err);
        showToastFeedback("Failed to delete user.", "error");
      });
  }


  function showToastFeedback(msg, type = "success") {
    showToast(msg, type);
  }

})();
