function renderList(containerId, items, config) {
  const container = document.getElementById(containerId);
  container.className = "dashboard-list";
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
    const div = document.createElement("div");
    div.className = "dashboard-item";

    const contentDiv = document.createElement("div");
    contentDiv.className = "dashboard-item-content";

    const title = document.createElement("p");
    title.className = "dashboard-title";
    title.textContent = item[config.titleField] || "Unnamed";

    contentDiv.appendChild(title);

    const metaContainer = document.createElement("div");
    metaContainer.className = "dashboard-meta-container";

    // Format field name helper
    const formatFieldName = (str) => {
      return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    };

    config.fields.forEach(field => {
      const meta = document.createElement("p");
      meta.className = "dashboard-meta";

      let value = item[field];

      if (value === null || value === undefined || value === "") {
        value = "—";
      }

      meta.innerHTML = `<strong>${formatFieldName(field)}:</strong> ${value}`;
      metaContainer.appendChild(meta);
    });
    
    contentDiv.appendChild(metaContainer);
    div.appendChild(contentDiv);

    if (config.enableDelete) {
      const actionsDiv = document.createElement("div");
      actionsDiv.className = "dashboard-actions";
      
      const btn = document.createElement("button");
      btn.className = "dashboard-delete-btn";
      btn.textContent = "Delete";

      btn.addEventListener("click", () => {
        showModal(
          "Confirm Deletion",
          `Are you sure you want to delete this item? This action cannot be undone.`,
          () => {
            renderDelete(config.domain, item.id);
          }
        );
      });

      actionsDiv.appendChild(btn);
      div.appendChild(actionsDiv);
    }

    container.appendChild(div);
  });
}

function renderDelete(domain, id) {
  fetch(`/api/${domain}/${id}`, { method: "DELETE" })
    .then(res => {
      if (!res.ok) throw new Error("Failed to delete");
      renderLoad(domain);
    })
    .catch(err => {
      console.error(err);
      alert("Error deleting item.");
    });
}

const domainConfig = {
  articles: {
    titleField: "title",
    fields: ["id", "published_at", "view_count"]
  },
  items: {
    titleField: "name",
    fields: ["id", "rating", "created_at"]
  },
  users: {
    titleField: "name",
    fields: ["id", "email", "created_at"]
  },
  interactions: {
    titleField: "content",
    fields: ["id", "user_id", "created_at"]
  }
};

function renderLoad(domain) {
  const container = document.getElementById(`${domain}-container`);
  if (!container) return;

  if (domain === "interactions") {
    renderInteractionAnalytics(`${domain}-container`);
    return;
  }

  container.className = "dashboard-list";
  container.innerHTML = "<div class='dashboard-loading'>Loading</div>";

  fetch(`/api/${domain}/`)
    .then(res => {
      if (!res.ok) throw new Error("Network error");
      return res.json();
    })
    .then(data => {
      renderList(`${domain}-container`, data, {
        ...domainConfig[domain],
        enableDelete: true,
        domain: domain
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

// --- Component Reusability UI ---
let activeModalCallback = null;

function createModalSystem() {
  if (document.getElementById("dashboard-modal-overlay")) return;

  const overlay = document.createElement("div");
  overlay.id = "dashboard-modal-overlay";
  overlay.className = "dashboard-modal-overlay";

  const content = document.createElement("div");
  content.className = "dashboard-modal-content";

  content.innerHTML = `
    <h3 class="dashboard-modal-title" id="dashboard-modal-title">Confirm</h3>
    <p class="dashboard-modal-body" id="dashboard-modal-body">Are you sure?</p>
    <div class="dashboard-modal-actions">
      <button class="dashboard-btn dashboard-btn-secondary" id="dashboard-modal-cancel">Cancel</button>
      <button class="dashboard-btn dashboard-btn-danger" id="dashboard-modal-confirm">Confirm</button>
    </div>
  `;

  overlay.appendChild(content);
  document.body.appendChild(overlay);

  document.getElementById("dashboard-modal-cancel").addEventListener("click", closeModal);
  document.getElementById("dashboard-modal-confirm").addEventListener("click", () => {
    if (activeModalCallback) activeModalCallback();
    closeModal();
  });

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });
}

function showModal(title, body, onConfirm) {
  createModalSystem();
  document.getElementById("dashboard-modal-title").textContent = title;
  document.getElementById("dashboard-modal-body").textContent = body;
  activeModalCallback = onConfirm;

  const overlay = document.getElementById("dashboard-modal-overlay");
  void overlay.offsetWidth; // Reflow
  overlay.classList.add("active");
}

function closeModal() {
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (overlay) overlay.classList.remove("active");
  activeModalCallback = null;
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