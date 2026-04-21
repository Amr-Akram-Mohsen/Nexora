// ==============================
// STATE MANAGEMENT
// ==============================
let currentFilters = {};
let currentDomain = null;
let searchDebounce = null;


// ==============================
// DOMAIN CONFIG
// ==============================
const domainConfig = {
  articles: {
    titleField: "title",
    fields: ["id", "published_at", "view_count"],
    enableDelete: true,
    filters: [
      { key: "source", type: "text", placeholder: "Exact Source Name..." }
    ]
  },
  items: {
    titleField: "name",
    fields: ["id", "rating", "created_at"],
    enableDelete: true,
    filters: [
      { key: "brand", type: "text", placeholder: "Brand slug (e.g. apple)" }
    ]
  },
  users: {
    titleField: "name",
    fields: ["id", "email", "created_at"],
    enableDelete: false,
    filters: [
      {
        key: "role",
        type: "select",
        options: [
          { value: "", label: "All Roles" },
          { value: "admin", label: "Admin" },
          { value: "user", label: "User" }
        ]
      }
    ]
  },
  interactions: {}
};


// ==============================
// UTILITIES
// ==============================
function formatFieldName(str) {
  return str
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}


// ==============================
// FILTER UI
// ==============================
function renderFilters(domain, containerId) {
  const container = document.getElementById(containerId);
  const config = domainConfig[domain];
  if (!config) return;

  // remove existing filter bar (scoped)
  const existingBar = container.parentNode.querySelector(".dashboard-filter-bar");
  if (existingBar) existingBar.remove();

  const bar = document.createElement("div");
  bar.className = "dashboard-filter-bar";

  // SEARCH INPUT
  const searchInput = document.createElement("input");
  searchInput.type = "text";
  searchInput.placeholder = "Search...";
  searchInput.className = "dashboard-filter-input";
  searchInput.value = currentFilters.search || "";

  searchInput.addEventListener("input", (e) => {
    currentFilters.search = e.target.value;

    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      if (currentFilters.search && currentFilters.search.length < 2) return;
      fetchList(domain, containerId);
    }, 400);
  });

  bar.appendChild(searchInput);

  // DOMAIN FILTERS
  if (config.filters) {
    config.filters.forEach(f => {
      if (f.type === "select") {
        const select = document.createElement("select");
        select.className = "dashboard-filter-select";

        f.options.forEach(opt => {
          const option = document.createElement("option");
          option.value = opt.value;
          option.textContent = opt.label;
          select.appendChild(option);
        });

        select.value = currentFilters[f.key] || "";

        select.addEventListener("change", (e) => {
          currentFilters[f.key] = e.target.value;
          fetchList(domain, containerId);
        });

        bar.appendChild(select);
      }

      if (f.type === "text") {
        const input = document.createElement("input");
        input.type = "text";
        input.className = "dashboard-filter-input";
        input.placeholder = f.placeholder;
        input.value = currentFilters[f.key] || "";

        input.addEventListener("input", (e) => {
          currentFilters[f.key] = e.target.value;

          clearTimeout(searchDebounce);
          searchDebounce = setTimeout(() => {
            fetchList(domain, containerId);
          }, 400);
        });

        bar.appendChild(input);
      }
    });
  }

  container.parentNode.insertBefore(bar, container);
}


// ==============================
// FETCH LIST
// ==============================
function fetchList(domain, containerId) {
  const container = document.getElementById(containerId);

  container.className = "dashboard-list";
  container.innerHTML = `
    <div class="dashboard-loading">
      <p>Loading ${domain}...</p>
    </div>
  `;

  const params = new URLSearchParams();

  for (const [key, val] of Object.entries(currentFilters)) {
    if (val && val.trim() !== "") {
      params.append(key, val.trim());
    }
  }

  const qs = params.toString() ? `?${params.toString()}` : "";

  fetch(`/api/${domain}/${qs}`)
    .then(res => {
      if (!res.ok) throw new Error("Network error");
      return res.json();
    })
    .then(data => {
      renderList(containerId, data, {
        ...domainConfig[domain],
        domain
      });
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `
        <div class="dashboard-error">
          <p>Failed to load ${domain}. Please try again.</p>
        </div>
      `;
    });
}


// ==============================
// RENDER LIST
// ==============================
function renderList(containerId, items, config) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="dashboard-empty">
        <p>No ${config.domain} found.</p>
      </div>
    `;
    return;
  }

  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "dashboard-item";

    const content = document.createElement("div");
    content.className = "dashboard-item-content";

    const title = document.createElement("p");
    title.className = "dashboard-title";
    title.textContent = item[config.titleField] || "Unnamed";

    content.appendChild(title);

    const metaContainer = document.createElement("div");
    metaContainer.className = "dashboard-meta-container";

    config.fields.forEach(field => {
      const meta = document.createElement("p");
      meta.className = "dashboard-meta";

      let value = item[field];
      if (!value) value = "—";

      meta.innerHTML = `<strong>${formatFieldName(field)}:</strong> ${value}`;
      metaContainer.appendChild(meta);
    });

    content.appendChild(metaContainer);
    row.appendChild(content);

    if (config.enableDelete) {
      const actions = document.createElement("div");
      actions.className = "dashboard-actions";

      const btn = document.createElement("button");
      btn.className = "dashboard-delete-btn";
      btn.textContent = "Delete";

      btn.addEventListener("click", () => {
        showModal(
          "Confirm Deletion",
          "Are you sure you want to delete this item?",
          () => renderDelete(config.domain, item.id)
        );
      });

      actions.appendChild(btn);
      row.appendChild(actions);
    }

    container.appendChild(row);
  });
}


// ==============================
// DELETE
// ==============================
function renderDelete(domain, id) {
  fetch(`/api/${domain}/${id}`, { method: "DELETE" })
    .then(res => {
      if (!res.ok) throw new Error("Delete failed");
      fetchList(domain, `${domain}-container`);
    })
    .catch(err => {
      console.error(err);
    });
}


// ==============================
// INTERACTIONS ANALYTICS
// ==============================
function renderInteractionAnalytics(containerId) {
  const container = document.getElementById(containerId);
  container.className = "dashboard-analytics";
  container.innerHTML = "<div class='dashboard-loading'>Loading analytics...</div>";

  fetch('/api/interactions/stats')
    .then(res => {
      if (!res.ok) throw new Error("Network error");
      return res.json();
    })
    .then(data => {
      container.innerHTML = "";

      const total = data.total || 0;

      // Hero Card
      const hero = document.createElement("div");
      hero.className = "dashboard-analytics-hero";
      hero.innerHTML = `
         <h2 class="dashboard-hero-title">Total Interactions</h2>
         <div class="dashboard-hero-value">${total}</div>
         <p class="dashboard-hero-meta">Comprehensive engagement across all sources</p>
      `;
      container.appendChild(hero);

      // Grid for breakdown
      const grid = document.createElement("div");
      grid.className = "dashboard-stats-grid";

      const breakdowns = [
        { label: "Views", key: "views" },
        { label: "Comments", key: "comments" },
        { label: "Likes", key: "likes" },
        { label: "Dislikes", key: "dislikes" },
        { label: "Saves", key: "saves" },
        { label: "Item Clicks", key: "item_clicks" }
      ];

      breakdowns.forEach(item => {
        const val = data[item.key] || 0;
        const pct = total > 0 ? Math.round((val / total) * 100) : 0;

        const card = document.createElement("div");
        card.className = "dashboard-stat-card";

        card.innerHTML = `
           <h3 class="dashboard-stat-value">${val}</h3>
           <p class="dashboard-stat-label">${item.label}</p>
           <div class="dashboard-stat-progress">
              <div class="dashboard-stat-bar" style="width: ${pct}%"></div>
           </div>
           <p class="dashboard-stat-meta">${pct}% of total</p>
        `;
        grid.appendChild(card);
      });

      container.appendChild(grid);
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `
        <div class="dashboard-error">
          <p>Failed to load interaction analytics. Please try again.</p>
        </div>
      `;
    });
}

// ==============================
// MODAL SYSTEM
// ==============================
let activeModalCallback = null;

function createModalSystem() {
  if (document.getElementById("dashboard-modal-overlay")) return;

  const overlay = document.createElement("div");
  overlay.id = "dashboard-modal-overlay";
  overlay.className = "dashboard-modal-overlay";

  overlay.innerHTML = `
    <div class="dashboard-modal-content">
      <h3 id="modal-title">Confirm</h3>
      <p id="modal-body"></p>
      <div>
        <button id="modal-cancel">Cancel</button>
        <button id="modal-confirm">Confirm</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  document.getElementById("modal-cancel").onclick = closeModal;
  document.getElementById("modal-confirm").onclick = () => {
    if (activeModalCallback) activeModalCallback();
    closeModal();
  };

  overlay.onclick = (e) => {
    if (e.target === overlay) closeModal();
  };
}

function showModal(title, body, callback) {
  createModalSystem();
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").textContent = body;
  activeModalCallback = callback;

  document.getElementById("dashboard-modal-overlay").classList.add("active");
}

function closeModal() {
  document.getElementById("dashboard-modal-overlay").classList.remove("active");
  activeModalCallback = null;
}


// ==============================
// MAIN ENTRY
// ==============================
function renderLoad(domain) {
  const container = document.getElementById(`${domain}-container`);
  if (!container) return;

  // reset state when switching domains
  if (currentDomain !== domain) {
    currentFilters = {};
    currentDomain = domain;
  }

  if (domain === "interactions") {
    renderInteractionAnalytics(`${domain}-container`);
    return;
  }

  renderFilters(domain, `${domain}-container`);
  fetchList(domain, `${domain}-container`);
}

// --- Dashboard Home Stats Renderer ---
function renderStatsGrid(containerId, stats) {
  const container = document.getElementById(containerId);
  container.className = "dashboard-stats-grid";
  container.innerHTML = "";

  const statConfig = [
    { label: "Total Articles", key: "articles_count", link: "/dashboard/articles" },
    { label: "Total Items", key: "items_count", link: "/dashboard/items" },
    { label: "Total Users", key: "users_count", link: "/dashboard/users" },
    { label: "Total Interactions", key: "interactions", subKey: "total", link: "/dashboard/interactions" },
    { label: "Total Views", key: "interactions", subKey: "views" },
    { label: "Total Comments", key: "interactions", subKey: "comments" },
  ];

  statConfig.forEach(stat => {
    let card;
    if (stat.link) {
      card = document.createElement("a");
      card.href = stat.link;
      card.className = "dashboard-stat-card clickable-card";
    } else {
      card = document.createElement("div");
      card.className = "dashboard-stat-card";
    }

    const value = document.createElement("h3");
    value.className = "dashboard-stat-value";

    let val;
    if (stat.subKey && stats[stat.key] !== undefined) {
      val = stats[stat.key][stat.subKey];
    } else {
      val = stats[stat.key];
    }
    value.textContent = val !== undefined ? val : "—";

    const label = document.createElement("p");
    label.className = "dashboard-stat-label";
    label.textContent = stat.label;

    card.appendChild(value);
    card.appendChild(label);

    // Add optional small label for reactions and saves
    if (stat.label === "Total Interactions" && stats.interactions) {
      const meta = document.createElement("p");
      meta.className = "dashboard-stat-meta";
      meta.textContent = `${stats.interactions.reactions} reactions, ${stats.interactions.saves} saves`;
      card.appendChild(meta);
    }

    container.appendChild(card);
  });
}


function renderDashboardHome(containerId) {
  const container = document.getElementById(containerId);
  container.innerHTML = "<div class='dashboard-loading'>Loading statistics...</div>";

  fetch('/api/dashboard/stats')
    .then(res => {
      if (!res.ok) throw new Error("Failed to load stats");
      return res.json();
    })
    .then(data => {
      renderStatsGrid(containerId, data);
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `
        <div class="dashboard-error">
          <p>Unable to load dashboard statistics. Please try again later.</p>
        </div>
      `;
    });
}

