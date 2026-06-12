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
function getUrlQueryParams() {
  const params = {};
  const searchParams = new URLSearchParams(window.location.search);
  for (const [key, value] of searchParams.entries()) {
    params[key] = value;
  }
  return params;
}

function formatFieldName(str) {
  return str
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatDate(str, includeTime = false) {
  if (!str) return "—";
  try {
    const d = new Date(str);
    const dateStr = d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    if (includeTime) {
      return dateStr + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }
    return dateStr;
  } catch {
    return str;
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "—";
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}


// ==============================
// STATE TEMPLATE HELPERS
// ==============================
function getSpinnerHtml(text = "Loading…", extraClass = "") {
  return `
    <div class="dashboard-loading ${extraClass}">
      <div class="spinner"></div>
      <p>${escapeHtml(text)}</p>
    </div>
  `;
}

function getTableSpinnerHtml(colspan, text = "Loading…", extraClass = "") {
  return `
    <tr>
      <td colspan="${colspan}" class="table-loading-cell">
        ${getSpinnerHtml(text, extraClass)}
      </td>
    </tr>
  `;
}

function getEmptyStateHtml(message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return `
    <div class="dashboard-empty ${extraClass}">
      <span class="dashboard-state-icon">${icon}</span>
      <p>${escapeHtml(message)}</p>
      ${submessage ? `<p class="dashboard-empty-subtext">${escapeHtml(submessage)}</p>` : ""}
    </div>
  `;
}

function getTableEmptyStateHtml(colspan, message = "No items found.", submessage = "Try adjusting your filters or search terms.", extraClass = "", icon = "📭") {
  return `
    <tr>
      <td colspan="${colspan}">
        ${getEmptyStateHtml(message, submessage, extraClass, icon)}
      </td>
    </tr>
  `;
}

function getErrorStateHtml(message = "Failed to load data. Please try again.", extraClass = "") {
  return `
    <div class="dashboard-error ${extraClass}">
      <span class="dashboard-error-icon">⚠️</span>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function getTableErrorStateHtml(colspan, message = "Failed to load data. Please try again.", extraClass = "") {
  return `
    <tr>
      <td colspan="${colspan}">
        ${getErrorStateHtml(message, extraClass)}
      </td>
    </tr>
  `;
}

function showToast(msg, type = "success") {
  const toast = document.getElementById("settings-toast");
  if (!toast) return;

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
  container.innerHTML = getSpinnerHtml(`Loading ${domain}…`);

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
      container.innerHTML = getErrorStateHtml(`Failed to load ${domain}. Please try again.`);
    });
}


// ==============================
// RENDER LIST
// ==============================
function renderList(containerId, items, config) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (!items || items.length === 0) {
    container.innerHTML = getEmptyStateHtml(`No ${config.domain} found.`, `Try adjusting your filters or search terms.`);
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
// INTERACTIONS ANALYTIC
function renderInteractionAnalytics(containerId) {
  const container = document.getElementById(containerId);
  container.className = "dashboard-analytics";
  container.innerHTML = getSpinnerHtml("Loading analytics…");

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
      activityHeader.className = "overview-panel-header analytics-activity-header";
      activityHeader.innerHTML = `
        <h3 class="overview-panel-title">💬 Recent Comments Activity</h3>
      `;
      container.appendChild(activityHeader);

      // Activity Feed Container
      const activityContainer = document.createElement("div");
      activityContainer.className = "overview-panel analytics-activity-container";
      activityContainer.innerHTML = getSpinnerHtml("Loading activity…");
      container.appendChild(activityContainer);

      // Fetch comments for recent activity
      fetch('/admin/interactions/comments')
        .then(res => res.json())
        .then(comments => {
          activityContainer.innerHTML = "";
          if (!comments || comments.length === 0) {
            activityContainer.innerHTML = getEmptyStateHtml("No recent activity.", "");
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
                <p class="activity-meta activity-meta-comment">"${c.content}"</p>
                <p class="activity-meta">${timeAgo} • Sentiment: ${c.sentiment || 'neutral'}</p>
              </div>
            `;
            ul.appendChild(li);
          });

          activityContainer.appendChild(ul);
        })
        .catch(() => {
          activityContainer.innerHTML = getErrorStateHtml("Could not load recent activity.");
        });

    })
    .catch(err => {
      console.error(err);
      container.innerHTML = getErrorStateHtml("Failed to load interaction analytics. Please try again.");
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
      container.innerHTML = getErrorStateHtml("Could not load interaction data.");
    });
}


// ==============================
// ==============================
// SHARED TOP LIST RENDERER
// ==============================
function renderTopList(containerId, items, valueKey, valueLabel) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!items || !items.length) {
    container.innerHTML = getEmptyStateHtml("No data yet.", "", "loading-height-sm");
    return;
  }

  const linkPrefix = valueLabel === 'views' ? '/admin/contents?search=' : '/admin/items?search=';

  container.innerHTML = `
    <ol class="overview-top-list">
      ${items.map((item, i) => `
        <li class="overview-top-item">
          <span class="overview-top-rank">${i + 1}</span>
          <span class="overview-top-name" title="${(item.title || item.name || '').replace(/"/g, '&quot;')}">
            <a href="${linkPrefix}${item.id}" class="overview-top-link-title">
              ${item.title || item.name || '—'}
            </a>
          </span>
          <span class="overview-top-value">${Number(item[valueKey] || 0).toLocaleString()} ${valueLabel}</span>
        </li>
      `).join("")}
    </ol>
  `;
}


// ==============================
// TOP ARTICLES (by views)
// ==============================
function renderTopArticles(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = getSpinnerHtml("Loading…", "loading-height-sm");

  fetch('/admin/dashboard/top-contents')
    .then(res => { if (!res.ok) throw new Error(); return res.json(); })
    .then(data => renderTopList(containerId, data, 'view_count', 'views'))
    .catch(() => {
      container.innerHTML = getErrorStateHtml("Could not load top contents.", "loading-height-sm");
    });
}


// ==============================
// TOP ITEMS (by clicks)
// ==============================
function renderTopItems(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = getSpinnerHtml("Loading…", "loading-height-sm");

  fetch('/admin/dashboard/top-items')
    .then(res => { if (!res.ok) throw new Error(); return res.json(); })
    .then(data => renderTopList(containerId, data, 'click_count', 'clicks'))
    .catch(() => {
      container.innerHTML = getErrorStateHtml("Could not load top items.", "loading-height-sm");
    });
}


// ==============================
// MODAL SYSTEM
// ==============================
let activeModalCallback = null;

function initModalSystem() {
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (!overlay || overlay._initialized) return;

  const cancelBtn = document.getElementById("modal-cancel");
  const confirmBtn = document.getElementById("modal-confirm");

  if (cancelBtn) cancelBtn.onclick = closeModal;
  if (confirmBtn) {
    confirmBtn.onclick = () => {
      if (activeModalCallback) activeModalCallback();
      closeModal();
    };
  }

  overlay.onclick = (e) => {
    if (e.target === overlay) closeModal();
  };

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  overlay._initialized = true;
}

function showModal(title, body, callback) {
  initModalSystem();
  const titleEl = document.getElementById("modal-title");
  const bodyEl = document.getElementById("modal-body");
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (titleEl) titleEl.textContent = title;
  if (bodyEl) bodyEl.textContent = body;
  activeModalCallback = callback;
  if (overlay) overlay.classList.add("active");
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
    { label: "Interactions", key: "interactions", link: "/admin/moderation", icon: "📊", color: "orange", subKey: "total" },
    { label: "Total Views", key: "interactions", link: "/admin/contents?sort_by=view_count&sort_dir=desc", icon: "👁️", color: "cyan", subKey: "views" },
    { label: "Total Comments", key: "interactions", link: "/admin/moderation?tab=comments", icon: "💬", color: "indigo", subKey: "comments" },
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
  container.innerHTML = getSpinnerHtml("Loading platform metrics…");

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
          <div class="health-list">
            <!-- Active Items row -->
            <div>
              <div class="health-row">
                <span class="font-bold"><span class="status-badge active badge-compact">Active</span> Live Index</span>
                <span class="text-muted">${data.active_contents.toLocaleString()} (${activePct}%)</span>
              </div>
              <div class="overview-breakdown-bar-track bar-track-health">
                <div class="overview-breakdown-bar bar-active" style="width: ${activePct}%;"></div>
              </div>
            </div>

            <!-- Inactive Items row -->
            <div>
              <div class="health-row">
                <span class="font-bold"><span class="status-badge inactive badge-compact">Inactive</span> Hidden Archive</span>
                <span class="text-muted">${data.inactive_contents.toLocaleString()} (${inactivePct}%)</span>
              </div>
              <div class="overview-breakdown-bar-track bar-track-health">
                <div class="overview-breakdown-bar bar-inactive" style="width: ${inactivePct}%;"></div>
              </div>
            </div>

            <!-- Pending Review / Drafts alert -->
            <a href="/admin/contents?published=false" class="dashboard-stat-card clickable-card moderation-queue-link">
              <div class="flex-align-center gap-sm">
                <span class="text-lg-icon">⏳</span>
                <div>
                  <div class="font-bold text-sm text-foreground">Moderation Queue</div>
                  <div class="text-xs text-muted">Unpublished aggregator drafts</div>
                </div>
              </div>
              <span class="status-badge badge-pending">${data.review_queue_count} pending</span>
            </a>

            ${growthHtml}
          </div>
        `;
      }

      // 3. Render Real-time Ingestion Activities
      const ingestContainer = document.getElementById("recent-ingest-container");
      if (ingestContainer) {
        if (!data.recent_ingested || data.recent_ingested.length === 0) {
          ingestContainer.innerHTML = getEmptyStateHtml("No recent ingestions.", "", "loading-height-sm");
        } else {
          ingestContainer.innerHTML = `
            <ul class="activity-feed">
              ${data.recent_ingested.map(r => {
            let badgeClass = "user";
            let badgeIcon = "📰";
            if (r.type === "video") { badgeClass = "active"; badgeIcon = "🎥"; }
            else if (r.type === "post") { badgeClass = "admin"; badgeIcon = "💬"; }

            return `
                  <li class="activity-item ingest-log-item">
                    <div class="activity-icon icon-save ingest-log-icon">
                      ${badgeIcon}
                    </div>
                    <div class="activity-content">
                      <p class="activity-text ingest-log-text">
                        Successfully ingested <span class="status-badge ${badgeClass} badge-type-compact">${r.type}</span>
                        <a href="/admin/contents?search=${r.id}" class="activity-target text-deco-none ml-1">#${r.id}</a>
                      </p>
                      <p class="activity-meta ingest-log-title">${r.title}</p>
                      <p class="activity-meta ingest-log-meta">${r.time}</p>
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
          categoriesContainer.innerHTML = getEmptyStateHtml("No categories mapped.", "", "loading-height-sm");
        } else {
          const maxVal = Math.max(...data.by_category.map(c => c.count), 1);
          categoriesContainer.innerHTML = `
            <div class="dist-list">
              ${data.by_category.map(c => {
            const pct = Math.round((c.count / maxVal) * 100);
            return `
                  <a href="/admin/contents?category=${c.slug}" class="dist-row-link">
                    <div class="dist-row">
                      <span class="dist-row-name font-bold text-foreground">${c.name}</span>
                      <span class="text-muted">${c.count.toLocaleString()} items</span>
                    </div>
                    <div class="overview-breakdown-bar-track bar-track-health">
                      <div class="overview-breakdown-bar bar-purple" style="width: ${pct}%;"></div>
                    </div>
                  </a>
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
          sourcesContainer.innerHTML = getEmptyStateHtml("No source statistics.", "", "loading-height-sm");
        } else {
          const maxVal = Math.max(...data.by_source.map(s => s.count), 1);
          sourcesContainer.innerHTML = `
            <div class="dist-list">
              ${data.by_source.map(s => {
            const pct = Math.round((s.count / maxVal) * 100);
            return `
                  <a href="/admin/contents?source=${s.slug}" class="dist-row-link">
                    <div class="dist-row">
                      <span class="dist-row-name font-bold text-foreground">${s.name}</span>
                      <span class="text-muted">${s.count.toLocaleString()} items</span>
                    </div>
                    <div class="overview-breakdown-bar-track bar-track-health">
                      <div class="overview-breakdown-bar bar-teal" style="width: ${pct}%;"></div>
                    </div>
                  </a>
                `;
          }).join("")}
            </div>
          `;
        }
      }

      // 5b. Render Product Sources Distribution
      const productSourcesContainer = document.getElementById("product-sources-distribution-container");
      if (productSourcesContainer) {
        if (!data.product_by_source || data.product_by_source.length === 0) {
          productSourcesContainer.innerHTML = getEmptyStateHtml("No product source statistics.", "", "loading-height-sm");
        } else {
          const maxVal = Math.max(...data.product_by_source.map(s => s.count), 1);
          productSourcesContainer.innerHTML = `
            <div class="dist-list">
              ${data.product_by_source.map(s => {
            const pct = Math.round((s.count / maxVal) * 100);
            return `
                  <a href="/admin/items?source=${s.slug}" class="dist-row-link">
                    <div class="dist-row">
                      <span class="dist-row-name font-bold text-foreground">${s.name}</span>
                      <span class="text-muted">${s.count.toLocaleString()} products</span>
                    </div>
                    <div class="overview-breakdown-bar-track bar-track-health">
                      <div class="overview-breakdown-bar bar-purple" style="width: ${pct}%;"></div>
                    </div>
                  </a>
                `;
          }).join("")}
            </div>
          `;
        }
      }

      // 5c. Render Top Content Providers Performance
      const topContentProvidersContainer = document.getElementById("top-content-providers-container");
      if (topContentProvidersContainer) {
        if (!data.top_performing_content || data.top_performing_content.length === 0) {
          topContentProvidersContainer.innerHTML = getEmptyStateHtml("No provider data.", "", "loading-height-sm");
        } else {
          const maxVal = Math.max(...data.top_performing_content.map(s => s.views), 1);
          topContentProvidersContainer.innerHTML = `
            <div class="dist-list">
              ${data.top_performing_content.map(s => {
            const pct = Math.round((s.views / maxVal) * 100);
            return `
                  <a href="/admin/contents?source=${s.slug}&sort_by=view_count&sort_dir=desc" class="dist-row-link">
                    <div class="dist-row">
                      <span class="dist-row-name font-bold text-foreground">${s.name}</span>
                      <span class="text-muted">${s.views.toLocaleString()} views</span>
                    </div>
                    <div class="overview-breakdown-bar-track bar-track-health">
                      <div class="overview-breakdown-bar bar-trend" style="width: ${pct}%;"></div>
                    </div>
                  </a>
                `;
          }).join("")}
            </div>
          `;
        }
      }

      // 5d. Render Top Product Providers Performance
      const topProductProvidersContainer = document.getElementById("top-product-providers-container");
      if (topProductProvidersContainer) {
        if (!data.top_performing_product || data.top_performing_product.length === 0) {
          topProductProvidersContainer.innerHTML = getEmptyStateHtml("No merchant data.", "", "loading-height-sm");
        } else {
          const maxVal = Math.max(...data.top_performing_product.map(s => s.clicks), 1);
          topProductProvidersContainer.innerHTML = `
            <div class="dist-list">
              ${data.top_performing_product.map(s => {
            const pct = Math.round((s.clicks / maxVal) * 100);
            return `
                  <a href="/admin/items?source=${s.slug}&sort_by=click_count&sort_dir=desc" class="dist-row-link">
                    <div class="dist-row">
                      <span class="dist-row-name font-bold text-foreground">${s.name}</span>
                      <span class="text-muted">${s.clicks.toLocaleString()} clicks</span>
                    </div>
                    <div class="overview-breakdown-bar-track bar-track-health">
                      <div class="overview-breakdown-bar bar-trend bar-orange" style="width: ${pct}%;"></div>
                    </div>
                  </a>
                `;
          }).join("")}
            </div>
          `;
        }
      }

      // 5e. Render Provider Activity Summary
      const providerActivitiesContainer = document.getElementById("provider-activities-container");
      if (providerActivitiesContainer) {
        if (!data.provider_activities || data.provider_activities.length === 0) {
          providerActivitiesContainer.innerHTML = getEmptyStateHtml("No active providers.", "", "loading-height-sm");
        } else {
          providerActivitiesContainer.innerHTML = `
            <ul class="activity-feed">
              ${data.provider_activities.map(s => {
            const totalRecords = s.content_count + s.product_count;
            const activityTime = s.latest_activity ? formatDate(s.latest_activity) : "No activity";

            return `
                  <li class="activity-item ingest-log-item">
                    <div class="activity-icon icon-comment ingest-log-icon">
                      📡
                    </div>
                    <div class="activity-content">
                      <p class="activity-text ingest-log-text">
                        <strong class="text-foreground">${s.name}</strong> 
                        <span class="status-badge active badge-type-compact badge-indigo">slug: ${s.slug}</span>
                      </p>
                      <p class="activity-meta ingest-log-text mt-1 text-muted">
                        Volume: <strong>${s.content_count.toLocaleString()}</strong> content items & <strong>${s.product_count.toLocaleString()}</strong> products
                      </p>
                      <p class="activity-meta ingest-log-meta mt-1">
                        Last Ingest Activity: <strong>${activityTime}</strong>
                      </p>
                    </div>
                  </li>
                `;
          }).join("")}
            </ul>
          `;
        }
      }

    })
    .catch(err => {
      console.error(err);
      container.innerHTML = getErrorStateHtml("Unable to load dashboard metrics. Please try again later.");
    });
}
