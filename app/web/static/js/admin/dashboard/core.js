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
  contents: {
    titleField: "title",
    fields: ["id", "published_at", "view_count"],
    enableDelete: true,
    filters: [
      { key: "source", type: "text", placeholder: "Filter by source…" }
    ]
  },
  items: {
    titleField: "name",
    fields: ["id", "rating", "created_at"],
    enableDelete: true,
    filters: [
      { key: "brand", type: "text", placeholder: "Filter by brand slug…" }
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

function formatDate(str) {
  if (!str) return "—";
  try {
    return new Date(str).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return str;
  }
}

function showToast(msg, type = "success") {
  const toast = document.getElementById("settings-toast") || (() => {
    const t = document.createElement("div");
    t.id = "settings-toast";
    t.className = "settings-toast";
    t.setAttribute("role", "alert");
    document.body.appendChild(t);
    return t;
  })();

  toast.textContent = msg;
  toast.className = `settings-toast settings-toast-${type} settings-toast-show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove("settings-toast-show");
  }, 3200);
}


// ==============================
// FILTER UI
// ==============================
function renderFilters(domain, containerId) {
  const container = document.getElementById(containerId);
  const config = domainConfig[domain];
  if (!config) return;

  const existingBar = container.parentNode.querySelector(".dashboard-filter-bar");
  if (existingBar) existingBar.remove();

  const bar = document.createElement("div");
  bar.className = "dashboard-filter-bar";

  // Search wrapper
  const searchWrap = document.createElement("div");
  searchWrap.className = "dashboard-filter-search-wrap";

  const searchIcon = document.createElement("span");
  searchIcon.className = "dashboard-filter-search-icon";
  searchIcon.textContent = "🔍";
  searchWrap.appendChild(searchIcon);

  const searchInput = document.createElement("input");
  searchInput.type = "text";
  searchInput.placeholder = "Search…";
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

  searchWrap.appendChild(searchInput);
  bar.appendChild(searchWrap);

  // Domain-specific filters
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
          searchDebounce = setTimeout(() => fetchList(domain, containerId), 400);
        });
        bar.appendChild(input);
      }
    });
  }

  // Clear filters button
  const clearBtn = document.createElement("button");
  clearBtn.className = "dashboard-filter-clear";
  clearBtn.textContent = "Clear";
  clearBtn.title = "Reset all filters";
  clearBtn.addEventListener("click", () => {
    currentFilters = {};
    renderFilters(domain, containerId);
    fetchList(domain, containerId);
  });
  bar.appendChild(clearBtn);

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
      <div class="spinner"></div>
      <p>Loading ${domain}…</p>
    </div>
  `;

  const params = new URLSearchParams();
  for (const [key, val] of Object.entries(currentFilters)) {
    if (val && val.trim() !== "") params.append(key, val.trim());
  }
  const qs = params.toString() ? `?${params.toString()}` : "";

  fetch(`/admin/${domain}/${qs}`)
    .then(res => {
      if (!res.ok) throw new Error("Network error");
      return res.json();
    })
    .then(data => {
      renderList(containerId, data, { ...domainConfig[domain], domain });
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `
        <div class="dashboard-error">
          <span style="font-size:2rem;">⚠️</span>
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
        <span style="font-size:2.5rem;margin-bottom:1rem;">📭</span>
        <p>No ${config.domain} found.</p>
        <p style="font-size:0.8rem;margin-top:0.5rem;opacity:0.7;">Try adjusting your filters or search terms.</p>
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
      if (field.includes("_at") && value) value = formatDate(value);
      if (!value && value !== 0) value = "—";

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
      btn.innerHTML = `🗑 Delete`;
      btn.addEventListener("click", () => {
        showModal(
          "Confirm Deletion",
          `Are you sure you want to delete "${item[config.titleField] || 'this item'}"? This action cannot be undone.`,
          () => renderDelete(config.domain, item.id, btn)
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
function renderDelete(domain, id, btn) {
  if (btn) { btn.disabled = true; btn.textContent = "Deleting…"; }

  fetch(`/admin/${domain}/${id}`, { method: "DELETE" })
    .then(res => {
      if (!res.ok) throw new Error("Delete failed");
      fetchList(domain, `${domain}-container`);
    })
    .catch(err => {
      console.error(err);
      if (btn) { btn.disabled = false; btn.innerHTML = "🗑 Delete"; }
    });
}


// ==============================
// INTERACTIONS ANALYTICS
// ==============================
function renderInteractionAnalytics(containerId) {
  const container = document.getElementById(containerId);
  container.className = "dashboard-analytics";
  container.innerHTML = `
    <div class="dashboard-loading">
      <div class="spinner"></div>
      <p>Loading analytics…</p>
    </div>
  `;

  fetch('/admin/interactions/stats')
    .then(res => {
      if (!res.ok) throw new Error("Network error");
      return res.json();
    })
    .then(data => {
      container.innerHTML = "";

      const total = data.total || 0;

      const hero = document.createElement("div");
      hero.className = "dashboard-analytics-hero";
      hero.innerHTML = `
         <h2 class="dashboard-hero-title">Total Interactions</h2>
         <div class="dashboard-hero-value">${total.toLocaleString()}</div>
         <p class="dashboard-hero-meta">Comprehensive engagement across all content</p>
      `;
      container.appendChild(hero);

      const grid = document.createElement("div");
      grid.className = "dashboard-stats-grid";

      const breakdowns = [
        { label: "Views", key: "views", icon: "👁️" },
        { label: "Comments", key: "comments", icon: "💬" },
        { label: "Likes", key: "likes", icon: "👍" },
        { label: "Dislikes", key: "dislikes", icon: "👎" },
        { label: "Saves", key: "saves", icon: "🔖" },
        { label: "Item Clicks", key: "item_clicks", icon: "🛒" },
      ];

      breakdowns.forEach(bk => {
        const val = data[bk.key] || 0;
        const pct = total > 0 ? Math.round((val / total) * 100) : 0;

        const card = document.createElement("div");
        card.className = "dashboard-stat-card";
        card.innerHTML = `
           <div class="dashboard-stat-icon">${bk.icon}</div>
           <h3 class="dashboard-stat-value">${val.toLocaleString()}</h3>
           <p class="dashboard-stat-label">${bk.label}</p>
           <div class="dashboard-stat-progress">
              <div class="dashboard-stat-bar" style="width: ${pct}%"></div>
           </div>
           <p class="dashboard-stat-meta">${pct}% of total</p>
        `;
        grid.appendChild(card);
      });

      container.appendChild(grid);

      // Add Recent Activity Feed Header
      const activityHeader = document.createElement("div");
      activityHeader.className = "overview-panel-header";
      activityHeader.style.marginTop = "2rem";
      activityHeader.style.borderRadius = "var(--radius-lg) var(--radius-lg) 0 0";
      activityHeader.style.border = "1px solid var(--border)";
      activityHeader.style.borderBottom = "none";
      activityHeader.innerHTML = `
        <h3 class="overview-panel-title">💬 Recent Comments Activity</h3>
      `;
      container.appendChild(activityHeader);

      // Activity Feed Container
      const activityContainer = document.createElement("div");
      activityContainer.className = "overview-panel";
      activityContainer.style.borderRadius = "0 0 var(--radius-lg) var(--radius-lg)";
      activityContainer.style.borderTop = "none";
      activityContainer.innerHTML = `<div class="dashboard-loading"><div class="spinner"></div><p>Loading activity…</p></div>`;
      container.appendChild(activityContainer);

      // Fetch comments for recent activity
      fetch('/admin/interactions/comments')
        .then(res => res.json())
        .then(comments => {
          activityContainer.innerHTML = "";
          if (!comments || comments.length === 0) {
            activityContainer.innerHTML = `<div class="dashboard-empty"><p>No recent activity.</p></div>`;
            return;
          }

          const ul = document.createElement("ul");
          ul.className = "activity-feed";

          // Show top 5 comments
          comments.slice(0, 5).forEach(c => {
            const li = document.createElement("li");
            li.className = "activity-item";

            const timeAgo = c.created_at ? new Date(c.created_at).toLocaleDateString() : "Recently";
            const targetName = c.target_type ? c.target_type.toUpperCase() : "Content";

            li.innerHTML = `
              <div class="activity-icon icon-comment">💬</div>
              <div class="activity-content">
                <p class="activity-text">
                  User commented on <span class="activity-target">${targetName} #${c.target_id || ''}</span>
                </p>
                <p class="activity-meta" style="margin-bottom:0.25rem;">"${c.content}"</p>
                <p class="activity-meta">${timeAgo} • Sentiment: ${c.sentiment || 'neutral'}</p>
              </div>
            `;
            ul.appendChild(li);
          });

          activityContainer.appendChild(ul);
        })
        .catch(() => {
          activityContainer.innerHTML = `<p class="hint" style="padding:1rem;">Could not load recent activity.</p>`;
        });

    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `
        <div class="dashboard-error">
          <span style="font-size:2rem;">⚠️</span>
          <p>Failed to load interaction analytics. Please try again.</p>
        </div>
      `;
    });
}


// ==============================
// INTERACTION BREAKDOWN (overview page)
// ==============================
function renderInteractionBreakdown(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  fetch('/admin/interactions/stats')
    .then(res => res.json())
    .then(data => {
      const items = [
        { label: "Views", key: "views", icon: "👁️" },
        { label: "Comments", key: "comments", icon: "💬" },
        { label: "Likes", key: "likes", icon: "👍" },
        { label: "Dislikes", key: "dislikes", icon: "👎" },
        { label: "Saves", key: "saves", icon: "🔖" },
        { label: "Item Clicks", key: "item_clicks", icon: "🛒" },
      ];
      const total = data.total || 1;

      container.innerHTML = `
        <div class="overview-breakdown-grid">
          ${items.map(it => {
        const val = data[it.key] || 0;
        const pct = Math.round((val / total) * 100);
        return `
              <div class="overview-breakdown-row">
                <span class="overview-breakdown-icon">${it.icon}</span>
                <span class="overview-breakdown-label">${it.label}</span>
                <div class="overview-breakdown-bar-track">
                  <div class="overview-breakdown-bar" style="width:${pct}%"></div>
                </div>
                <span class="overview-breakdown-val">${val.toLocaleString()}</span>
                <span class="overview-breakdown-pct">${pct}%</span>
              </div>
            `;
      }).join("")}
        </div>
      `;
    })
    .catch(() => {
      container.innerHTML = `<div class="dashboard-error"><p>Could not load interaction data.</p></div>`;
    });
}


// ==============================
// TOP ARTICLES (by views)
// ==============================
function renderTopArticles(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  fetch('/admin/contents/?limit=5')
    .then(res => res.json())
    .then(data => {
      const sorted = [...data].sort((a, b) => (b.view_count || 0) - (a.view_count || 0)).slice(0, 5);
      if (!sorted.length) {
        container.innerHTML = `<div class="dashboard-empty" style="min-height:100px;"><p>No contents yet.</p></div>`;
        return;
      }
      container.innerHTML = `
        <ol class="overview-top-list">
          ${sorted.map((a, i) => `
            <li class="overview-top-item">
              <span class="overview-top-rank">${i + 1}</span>
              <span class="overview-top-name" title="${a.title}">${a.title}</span>
              <span class="overview-top-value">${(a.view_count || 0).toLocaleString()} views</span>
            </li>
          `).join("")}
        </ol>
      `;
    })
    .catch(() => {
      container.innerHTML = `<div class="dashboard-error"><p>Could not load top contents.</p></div>`;
    });
}


// ==============================
// TOP ITEMS (by clicks)
// ==============================
function renderTopItems(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  fetch('/admin/items/')
    .then(res => res.json())
    .then(data => {
      // Sort by click_count if available, else rating
      const sorted = [...data].sort((a, b) => (b.click_count || b.rating || 0) - (a.click_count || a.rating || 0)).slice(0, 5);
      if (!sorted.length) {
        container.innerHTML = `<div class="dashboard-empty" style="min-height:100px;"><p>No items yet.</p></div>`;
        return;
      }
      container.innerHTML = `
        <ol class="overview-top-list">
          ${sorted.map((item, i) => `
            <li class="overview-top-item">
              <span class="overview-top-rank">${i + 1}</span>
              <span class="overview-top-name" title="${item.name}">${item.name}</span>
              <span class="overview-top-value">⭐ ${item.rating || "—"}</span>
            </li>
          `).join("")}
        </ol>
      `;
    })
    .catch(() => {
      container.innerHTML = `<div class="dashboard-error"><p>Could not load top items.</p></div>`;
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
      <div class="dashboard-modal-icon">⚠️</div>
      <h3 id="modal-title" class="dashboard-modal-title">Confirm</h3>
      <p id="modal-body" class="dashboard-modal-body"></p>
      <div class="dashboard-modal-actions">
        <button id="modal-cancel" class="dashboard-btn dashboard-btn-secondary">Cancel</button>
        <button id="modal-confirm" class="dashboard-btn dashboard-btn-danger">Confirm</button>
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

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
}

function showModal(title, body, callback) {
  createModalSystem();
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").textContent = body;
  activeModalCallback = callback;
  document.getElementById("dashboard-modal-overlay").classList.add("active");
}

function closeModal() {
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (overlay) overlay.classList.remove("active");
  activeModalCallback = null;
}


// ==============================
// MAIN ENTRY
// ==============================
function renderLoad(domain) {
  const container = document.getElementById(`${domain}-container`);
  if (!container) return;

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

function refreshCurrentView() {
  if (currentDomain) {
    renderLoad(currentDomain);
  } else {
    const overviewContainer = document.getElementById("dashboard-overview-container");
    if (overviewContainer) renderDashboardOverview("dashboard-overview-container");
  }
}


// ==============================
// STATS GRID (overview cards)
// ==============================
function renderStatsGrid(containerId, stats) {
  const container = document.getElementById(containerId);
  container.className = "dashboard-stats-grid";
  container.innerHTML = "";

  const statConfig = [
    { label: "Total Contents", key: "contents_count", link: "/admin/contents", icon: "📰", color: "blue" },
    { label: "Total Items", key: "items_count", link: "/admin/items", icon: "🛍️", color: "purple" },
    { label: "Total Users", key: "users_count", link: "/admin/users", icon: "👥", color: "green" },
    { label: "Interactions", key: "interactions", link: "/admin/interactions", icon: "📊", color: "orange", subKey: "total" },
    { label: "Total Views", key: "interactions", icon: "👁️", color: "cyan", subKey: "views" },
    { label: "Total Comments", key: "interactions", icon: "💬", color: "indigo", subKey: "comments" },
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

    let val;
    if (stat.subKey && stats[stat.key] !== undefined) {
      val = stats[stat.key][stat.subKey];
    } else {
      val = stats[stat.key];
    }

    card.innerHTML = `
      <div class="dashboard-stat-icon">${stat.icon}</div>
      <h3 class="dashboard-stat-value">${val !== undefined ? Number(val).toLocaleString() : "—"}</h3>
      <p class="dashboard-stat-label">${stat.label}</p>
    `;

    if (stat.label === "Interactions" && stats.interactions) {
      const meta = document.createElement("p");
      meta.className = "dashboard-stat-meta";
      const r = stats.interactions;
      meta.textContent = `${(r.reactions || 0).toLocaleString()} reactions · ${(r.saves || 0).toLocaleString()} saves`;
      card.appendChild(meta);
    }

    container.appendChild(card);
  });
}


function renderDashboardOverview(containerId) {
  const container = document.getElementById(containerId);
  container.innerHTML = `
    <div class="dashboard-loading">
      <div class="spinner"></div>
      <p>Loading platform metrics…</p>
    </div>
  `;

  fetch('/admin/dashboard/stats')
    .then(res => {
      if (!res.ok) throw new Error("Failed to load stats");
      return res.json();
    })
    .then(data => {
      // 1. Render core stats cards
      renderStatsGrid(containerId, data);

      // 2. Render Catalog Health & Moderation Queue
      const healthContainer = document.getElementById("catalog-health-container");
      if (healthContainer) {
        const total = data.contents_count || 1;
        const activePct = Math.round(((data.active_contents || 0) / total) * 100);
        const inactivePct = Math.round(((data.inactive_contents || 0) / total) * 100);
        
        let growthHtml = "";
        if (data.growth_trends && data.growth_trends.length > 0) {
          const maxTrend = Math.max(...data.growth_trends.map(t => t.count), 1);
          growthHtml = `
            <h4 class="filter-label-xs mt-3 mb-1">7-Day Ingestion Growth</h4>
            <div class="trend-chart-list">
              ${data.growth_trends.map(t => {
                const pct = Math.round((t.count / maxTrend) * 100);
                return `
                  <div class="trend-chart-item">
                    <span class="trend-chart-date">${t.date}</span>
                    <div class="overview-breakdown-bar-track bar-track-trend">
                      <div class="overview-breakdown-bar bar-trend" style="width: ${pct}%;"></div>
                    </div>
                    <span class="trend-chart-value">${t.count}</span>
                  </div>
                `;
              }).join("")}
            </div>
          `;
        }

        healthContainer.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 0.85rem;">
            <!-- Active Items row -->
            <div>
              <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: var(--text-sm);">
                <span style="font-weight: var(--weight-bold);"><span class="status-badge active" style="padding: 0.15rem 0.45rem; font-size: 0.65rem;">Active</span> Live Index</span>
                <span style="color: var(--muted-foreground);">${data.active_contents.toLocaleString()} (${activePct}%)</span>
              </div>
              <div class="overview-breakdown-bar-track" style="height: 6px; background: var(--border);">
                <div class="overview-breakdown-bar" style="width: ${activePct}%; height: 100%; background: #16a34a;"></div>
              </div>
            </div>

            <!-- Inactive Items row -->
            <div>
              <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: var(--text-sm);">
                <span style="font-weight: var(--weight-bold);"><span class="status-badge inactive" style="padding: 0.15rem 0.45rem; font-size: 0.65rem;">Inactive</span> Hidden Archive</span>
                <span style="color: var(--muted-foreground);">${data.inactive_contents.toLocaleString()} (${inactivePct}%)</span>
              </div>
              <div class="overview-breakdown-bar-track" style="height: 6px; background: var(--border);">
                <div class="overview-breakdown-bar" style="width: ${inactivePct}%; height: 100%; background: var(--brand-red);"></div>
              </div>
            </div>

            <!-- Pending Review / Drafts alert -->
            <a href="/admin/contents?published=false" class="dashboard-stat-card clickable-card" style="padding: 0.75rem 1rem; display: flex; align-items: center; justify-content: space-between; border-color: rgba(var(--brand-purple-rgb), 0.25); text-decoration: none; margin-top: 0.25rem;">
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.25rem;">⏳</span>
                <div>
                  <div style="font-weight: var(--weight-bold); font-size: var(--text-sm); color: var(--foreground);">Moderation Queue</div>
                  <div style="font-size: var(--text-xs); color: var(--muted-foreground);">Unpublished aggregator drafts</div>
                </div>
              </div>
              <span class="status-badge admin" style="background: rgba(var(--brand-purple-rgb), 0.1); color: var(--brand-purple); font-size: var(--text-xs); font-weight: var(--weight-xbold);">${data.review_queue_count} pending</span>
            </a>

            ${growthHtml}
          </div>
        `;
      }

      // 3. Render Real-time Ingestion Activities
      const ingestContainer = document.getElementById("recent-ingest-container");
      if (ingestContainer) {
        if (!data.recent_ingested || data.recent_ingested.length === 0) {
          ingestContainer.innerHTML = `<div class="dashboard-empty" style="min-height: 120px;"><p>No recent ingestions.</p></div>`;
        } else {
          ingestContainer.innerHTML = `
            <ul class="activity-feed">
              ${data.recent_ingested.map(r => {
                let badgeClass = "user";
                let badgeIcon = "📰";
                if (r.type === "video") { badgeClass = "active"; badgeIcon = "🎥"; }
                else if (r.type === "post") { badgeClass = "admin"; badgeIcon = "💬"; }
                
                return `
                  <li class="activity-item" style="padding: 0.65rem 1.25rem;">
                    <div class="activity-icon icon-save" style="width: 1.75rem; height: 1.75rem; font-size: 0.85rem; background: var(--secondary);">
                      ${badgeIcon}
                    </div>
                    <div class="activity-content">
                      <p class="activity-text" style="font-size: var(--text-xs); line-height: 1.3;">
                        Successfully ingested <span class="status-badge ${badgeClass}" style="padding: 0.1rem 0.3rem; font-size: 0.55rem;">${r.type}</span>
                        <a href="/admin/contents?search=${r.id}" class="activity-target" style="text-decoration:none; margin-left:0.25rem;">#${r.id}</a>
                      </p>
                      <p class="activity-meta" style="font-weight: var(--weight-bold); font-size: var(--text-xs); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 0.1rem; color: var(--foreground);">${r.title}</p>
                      <p class="activity-meta" style="font-size: 0.65rem; color: var(--muted-foreground); margin-top: 0.1rem;">${r.time}</p>
                    </div>
                  </li>
                `;
              }).join("")}
            </ul>
          `;
        }
      }

      // 4. Render Categories Distribution
      const categoriesContainer = document.getElementById("categories-distribution-container");
      if (categoriesContainer) {
        if (!data.by_category || data.by_category.length === 0) {
          categoriesContainer.innerHTML = `<div class="dashboard-empty" style="min-height: 120px;"><p>No categories mapped.</p></div>`;
        } else {
          const maxVal = Math.max(...data.by_category.map(c => c.count), 1);
          categoriesContainer.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${data.by_category.map(c => {
                const pct = Math.round((c.count / maxVal) * 100);
                return `
                  <div>
                    <div style="display: flex; justify-content: space-between; font-size: var(--text-xs); margin-bottom: 0.25rem;">
                      <span style="font-weight: var(--weight-bold); color: var(--foreground);">${c.name}</span>
                      <span style="color: var(--muted-foreground);">${c.count.toLocaleString()} items</span>
                    </div>
                    <div class="overview-breakdown-bar-track" style="height: 6px; background: var(--border);">
                      <div class="overview-breakdown-bar" style="width: ${pct}%; height: 100%; background: var(--brand-purple);"></div>
                    </div>
                  </div>
                `;
              }).join("")}
            </div>
          `;
        }
      }

      // 5. Render Sources Distribution
      const sourcesContainer = document.getElementById("sources-distribution-container");
      if (sourcesContainer) {
        if (!data.by_source || data.by_source.length === 0) {
          sourcesContainer.innerHTML = `<div class="dashboard-empty" style="min-height: 120px;"><p>No source statistics.</p></div>`;
        } else {
          const maxVal = Math.max(...data.by_source.map(s => s.count), 1);
          sourcesContainer.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${data.by_source.map(s => {
                const pct = Math.round((s.count / maxVal) * 100);
                return `
                  <div>
                    <div style="display: flex; justify-content: space-between; font-size: var(--text-xs); margin-bottom: 0.25rem;">
                      <span style="font-weight: var(--weight-bold); color: var(--foreground);">${s.name}</span>
                      <span style="color: var(--muted-foreground);">${s.count.toLocaleString()} items</span>
                    </div>
                    <div class="overview-breakdown-bar-track" style="height: 6px; background: var(--border);">
                      <div class="overview-breakdown-bar" style="width: ${pct}%; height: 100%; background: var(--brand-teal);"></div>
                    </div>
                  </div>
                `;
              }).join("")}
            </div>
          `;
        }
      }

    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `
        <div class="dashboard-error">
          <span style="font-size:2rem;">⚠️</span>
          <p>Unable to load dashboard metrics. Please try again later.</p>
        </div>
      `;
    });
}
