/**
 * Nexora Control Panel - Users Management
 */

document.addEventListener("DOMContentLoaded", () => {
  fetchUsers();

  const searchInput = document.getElementById("user-search");
  if (searchInput) {
    let debounce;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        fetchUsers(e.target.value);
      }, 400);
    });
  }

  const refreshBtn = document.getElementById("refresh-users-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => fetchUsers(searchInput?.value));
  }
});

/**
 * Fetch users from the API
 * @param {string} search - Optional search query
 */
function fetchUsers(search = "") {
  const tableBody = document.getElementById("users-table-body");
  const loader = document.getElementById("users-loading");

  if (loader) loader.style.display = "block";
  if (tableBody) tableBody.style.opacity = "0.5";

  const url = search ? `/api/users/?search=${encodeURIComponent(search)}` : "/api/users/";

  fetch(url)
    .then(res => {
      if (!res.ok) throw new Error("Failed to fetch users");
      return res.json();
    })
    .then(data => {
      renderUsersTable(data);
    })
    .catch(err => {
      console.error(err);
      if (tableBody) {
        tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--brand-red)">Error loading users.</td></tr>`;
      }
    })
    .finally(() => {
      if (loader) loader.style.display = "none";
      if (tableBody) tableBody.style.opacity = "1";
    });
}

/**
 * Render user rows into the table
 * @param {Array} users 
 */
function renderUsersTable(users) {
  const tableBody = document.getElementById("users-table-body");
  if (!tableBody) return;

  tableBody.innerHTML = "";

  if (users.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center">No users found.</td></tr>`;
    return;
  }

  users.forEach(user => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${user.id}</td>
      <td>
        <div style="font-weight: 600">${user.name || 'N/A'}</div>
        <div style="font-size: 0.75rem; color: var(--muted-foreground)">${user.email}</div>
      </td>
      <td>
        <span class="status-badge ${user.is_admin ? 'admin' : 'user'}">
          ${user.is_admin ? 'Admin' : 'User'}
        </span>
      </td>
      <td>${new Date(user.created_at).toLocaleDateString()}</td>
      <td>
        <button class="dashboard-delete-btn" onclick="confirmDeleteUser(${user.id}, '${user.name || user.email}')">
          Delete
        </button>
      </td>
    `;

    tableBody.appendChild(row);
  });
}

/**
 * Confirm and delete a user
 * @param {number} id 
 * @param {string} name 
 */
function confirmDeleteUser(id, name) {
  // Use the modal system from core.js if available, otherwise fallback to confirm()
  if (typeof showModal === "function") {
    showModal(
      "Delete User",
      `Are you sure you want to delete user "${name}"? This action cannot be undone.`,
      () => performDeleteUser(id)
    );
  } else if (confirm(`Are you sure you want to delete user "${name}"?`)) {
    performDeleteUser(id);
  }
}

/**
 * Perform the actual DELETE request
 * @param {number} id 
 */
function performDeleteUser(id) {
  fetch(`/api/users/${id}`, { method: "DELETE" })
    .then(res => {
      if (!res.ok) throw new Error("Delete failed");
      return res.json();
    })
    .then(() => {
      fetchUsers(document.getElementById("user-search")?.value);
    })
    .catch(err => {
      console.error(err);
      alert("Failed to delete user.");
    });
}
