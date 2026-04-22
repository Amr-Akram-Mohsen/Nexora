/**
 * Nexora Control Panel — Users Management
 */

document.addEventListener("DOMContentLoaded", () => {
  fetchUsers();

  // Search
  const searchInput = document.getElementById("user-search");
  if (searchInput) {
    let debounce;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounce);
      debounce = setTimeout(() => fetchUsers(e.target.value, getRoleFilter()), 400);
    });
  }

  // Role filter
  const roleFilter = document.getElementById("user-role-filter");
  if (roleFilter) {
    roleFilter.addEventListener("change", () => fetchUsers(getSearchValue(), getRoleFilter()));
  }

  // Refresh
  const refreshBtn = document.getElementById("refresh-users-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => fetchUsers(getSearchValue(), getRoleFilter()));
  }
});

function getSearchValue() {
  return document.getElementById("user-search")?.value || "";
}

function getRoleFilter() {
  return document.getElementById("user-role-filter")?.value || "";
}


/**
 * Fetch users from the API.
 */
function fetchUsers(search = "", role = "") {
  const tableBody = document.getElementById("users-table-body");
  if (!tableBody) return;

  tableBody.innerHTML = `
    <tr>
      <td colspan="5" class="table-loading-cell">
        <div class="dashboard-loading" style="min-height:120px;">
          <div class="spinner"></div>
          <p>Loading users…</p>
        </div>
      </td>
    </tr>
  `;

  const params = new URLSearchParams();
  if (search.trim()) params.append("search", search.trim());
  if (role) params.append("role", role);
  const qs = params.toString() ? `?${params.toString()}` : "";

  fetch(`/api/users/${qs}`)
    .then(res => {
      if (!res.ok) throw new Error("Failed to fetch users");
      return res.json();
    })
    .then(data => {
      renderUsersTable(data);
      updateSummary(data.length);
    })
    .catch(err => {
      console.error(err);
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align:center;padding:3rem;color:var(--brand-red);">
            ⚠️ Error loading users. Please try again.
          </td>
        </tr>
      `;
    });
}

function updateSummary(count) {
  const bar = document.getElementById("users-summary");
  const cnt = document.getElementById("users-count");
  if (bar) bar.style.display = "block";
  if (cnt) cnt.textContent = count;
}


/**
 * Render user rows into the table.
 */
function renderUsersTable(users) {
  const tableBody = document.getElementById("users-table-body");
  if (!tableBody) return;

  tableBody.innerHTML = "";

  if (users.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;padding:3rem;color:var(--muted-foreground);">
          <div>📭</div>
          <div style="margin-top:0.5rem;">No users found. Try adjusting your filters.</div>
        </td>
      </tr>
    `;
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
            onclick="handleToggleAdmin(${user.id}, '${user.name || user.email}')"
            title="${user.is_admin ? 'Remove Admin' : 'Make Admin'}">
            ${user.is_admin ? '⬇ Demote' : '⬆ Promote'}
          </button>
          <button class="user-action-btn user-action-toggle-active"
            onclick="handleToggleActive(${user.id}, ${user.is_active}, '${user.name || user.email}')"
            title="${user.is_active ? 'Deactivate' : 'Activate'}">
            ${user.is_active ? '🚫 Deactivate' : '✅ Activate'}
          </button>
          <button class="user-action-btn user-action-delete"
            onclick="confirmDeleteUser(${user.id}, '${user.name || user.email}')"
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

  fetch(`/api/users/${id}/toggle-admin`, { method: "POST" })
    .then(res => {
      if (!res.ok) throw new Error("Toggle admin failed");
      return res.json();
    })
    .then(data => {
      showToastFeedback(data.is_admin ? `${name} is now an Admin` : `${name} is now a User`);
      fetchUsers(getSearchValue(), getRoleFilter());
    })
    .catch(err => {
      console.error(err);
      showToastFeedback("Failed to update role.", "error");
      fetchUsers(getSearchValue(), getRoleFilter());
    });
}


/**
 * Toggle active status.
 */
function handleToggleActive(id, isCurrentlyActive, name) {
  const endpoint = isCurrentlyActive ? `/api/users/${id}` : `/api/users/${id}/activate`;
  const method = isCurrentlyActive ? "DELETE" : "POST";

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
      fetchUsers(getSearchValue(), getRoleFilter());
    })
    .catch(err => {
      console.error(err);
      showToastFeedback("Failed to update status.", "error");
      fetchUsers(getSearchValue(), getRoleFilter());
    });
}


/**
 * Confirm and delete a user.
 */
function confirmDeleteUser(id, name) {
  if (typeof showModal === "function") {
    showModal(
      "Delete User",
      `Are you sure you want to permanently delete "${name}"? This action cannot be undone.`,
      () => performDeleteUser(id, name)
    );
  } else if (confirm(`Delete user "${name}"?`)) {
    performDeleteUser(id, name);
  }
}

function performDeleteUser(id, name) {
  fetch(`/api/users/${id}`, { method: "DELETE" })
    .then(res => {
      if (!res.ok) throw new Error("Delete failed");
      return res.json();
    })
    .then(() => {
      showToastFeedback(`${name} has been removed.`);
      fetchUsers(getSearchValue(), getRoleFilter());
    })
    .catch(err => {
      console.error(err);
      showToastFeedback("Failed to delete user.", "error");
    });
}


/**
 * Toast feedback (uses core.js showToast if loaded, else inline).
 */
function showToastFeedback(msg, type = "success") {
  if (typeof showToast === "function") {
    showToast(msg, type);
    return;
  }
  // Inline fallback
  let toast = document.getElementById("cp-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "cp-toast";
    toast.className = "settings-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `settings-toast settings-toast-${type} settings-toast-show`;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => toast.classList.remove("settings-toast-show"), 3200);
}
