// ==========================================
// OVERVIEW PAGE & ANALYTICS FUNCTIONS
// ==========================================

// ==========================================
// INTERACTIONS ANALYTICS
// ==========================================
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
      
      const title = document.createElement("h2");
      title.className = "dashboard-hero-title";
      title.textContent = "Total Interactions";
      hero.appendChild(title);

      const val = document.createElement("div");
      val.className = "dashboard-hero-value";
      val.textContent = total.toLocaleString();
      hero.appendChild(val);

      const meta = document.createElement("p");
      meta.className = "dashboard-hero-meta";
      meta.textContent = "Comprehensive engagement across all content";
      hero.appendChild(meta);

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

      const templateCard = document.getElementById("overview-stat-card-template");

      breakdowns.forEach(bk => {
        const val = data[bk.key] || 0;
        const pct = total > 0 ? Math.round((val / total) * 100) : 0;

        const card = document.createElement("div");
        card.className = "dashboard-stat-card flex flex-col justify-center";
        
        const clone = templateCard.content.cloneNode(true);
        clone.querySelector(".dashboard-stat-icon").textContent = bk.icon;
        clone.querySelector(".dashboard-stat-value").textContent = val.toLocaleString();
        clone.querySelector(".dashboard-stat-label").textContent = bk.label;

        const progress = document.createElement("div");
        progress.className = "dashboard-stat-progress";
        const bar = document.createElement("div");
        bar.className = "dashboard-stat-bar";
        bar.style.width = `${pct}%`;
        progress.appendChild(bar);
        clone.appendChild(progress);

        const cardMeta = document.createElement("p");
        cardMeta.className = "dashboard-stat-meta";
        cardMeta.textContent = `${pct}% of total`;
        clone.appendChild(cardMeta);

        card.appendChild(clone);
        grid.appendChild(card);
      });

      container.appendChild(grid);

      // Add Recent Activity Feed Header
      const activityHeader = document.createElement("div");
      activityHeader.className = "overview-panel-header analytics-activity-header flex items-center justify-between";
      const headerTitle = document.createElement("h3");
      headerTitle.className = "overview-panel-title";
      headerTitle.textContent = "💬 Recent Comments Activity";
      activityHeader.appendChild(headerTitle);
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
            activityContainer.appendChild(getEmptyStateHtml("No recent activity.", ""));
            return;
          }

          const ul = document.createElement("ul");
          ul.className = "activity-feed";

          // Show top 5 comments
          comments.slice(0, 5).forEach(c => {
            const li = document.createElement("li");
            li.className = "activity-item flex items-start";

            const iconDiv = document.createElement("div");
            iconDiv.className = "activity-icon icon-comment flex-center";
            iconDiv.textContent = "💬";
            li.appendChild(iconDiv);

            const actContent = document.createElement("div");
            actContent.className = "activity-content";

            const actText = document.createElement("p");
            actText.className = "activity-text";
            actText.textContent = "User commented on ";
            const spanTarget = document.createElement("span");
            spanTarget.className = "activity-target";
            spanTarget.textContent = `${c.target_type ? c.target_type.toUpperCase() : "Content"} #${c.target_id || ''}`;
            actText.appendChild(spanTarget);
            actContent.appendChild(actText);

            const actBody = document.createElement("p");
            actBody.className = "activity-meta activity-meta-comment";
            actBody.textContent = `"${c.content}"`;
            actContent.appendChild(actBody);

            const timeAgo = c.created_at ? new Date(c.created_at).toLocaleDateString() : "Recently";
            const actTime = document.createElement("p");
            actTime.className = "activity-meta";
            actTime.textContent = `${timeAgo} • Sentiment: ${c.sentiment || 'neutral'}`;
            actContent.appendChild(actTime);

            li.appendChild(actContent);
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


// ==========================================
// INTERACTION BREAKDOWN (overview page)
// ==========================================
function renderInteractionBreakdown(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  fetch('/admin/interactions/stats')
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";
      const templateGrid = document.getElementById("overview-breakdown-template");
      if (!templateGrid) return;
      const grid = templateGrid.content.cloneNode(true).querySelector(".overview-breakdown-grid");

      const items = [
        { label: "Views", key: "views", icon: "👁️" },
        { label: "Comments", key: "comments", icon: "💬" },
        { label: "Likes", key: "likes", icon: "👍" },
        { label: "Dislikes", key: "dislikes", icon: "👎" },
        { label: "Saves", key: "saves", icon: "🔖" },
        { label: "Item Clicks", key: "item_clicks", icon: "🛒" },
      ];
      const total = data.total || 1;
      const templateRow = document.getElementById("overview-breakdown-row-template");

      items.forEach(it => {
        const val = data[it.key] || 0;
        const pct = Math.round((val / total) * 100);

        const clone = templateRow.content.cloneNode(true);
        clone.querySelector(".overview-breakdown-icon").textContent = it.icon;
        clone.querySelector(".overview-breakdown-label").textContent = it.label;
        clone.querySelector(".overview-breakdown-bar").style.width = `${pct}%`;
        clone.querySelector(".overview-breakdown-val").textContent = val.toLocaleString();
        clone.querySelector(".overview-breakdown-pct").textContent = `${pct}%`;
        grid.appendChild(clone);
      });

      container.appendChild(grid);
    })
    .catch(() => {
      container.innerHTML = getErrorStateHtml("Could not load interaction data.");
    });
}

// ==========================================
// SHARED TOP LIST RENDERER
// ==========================================
function renderTopList(containerId, items, valueKey, valueLabel) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!items || !items.length) {
    container.innerHTML = getEmptyStateHtml("No data yet.", "", "loading-height-sm");
    return;
  }

  const linkPrefix = valueLabel === 'views' ? '/admin/contents?search=' : '/admin/items?search=';
  container.innerHTML = "";

  const templateList = document.getElementById("overview-top-list-template");
  if (!templateList) return;
  const list = templateList.content.cloneNode(true).querySelector(".overview-top-list");

  const templateItem = document.getElementById("overview-top-item-template");

  items.forEach((item, i) => {
    const clone = templateItem.content.cloneNode(true);
    clone.querySelector(".overview-top-rank").textContent = i + 1;
    
    const link = clone.querySelector(".overview-top-link-title");
    link.href = `${linkPrefix}${item.id}`;
    link.textContent = item.title || item.name || '—';
    link.title = item.title || item.name || '';

    clone.querySelector(".overview-top-value").textContent = `${Number(item[valueKey] || 0).toLocaleString()} ${valueLabel}`;
    list.appendChild(clone);
  });

  container.appendChild(list);
}

// ==========================================
// TOP ARTICLES (by views)
// ==========================================
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

// ==========================================
// TOP ITEMS (by clicks)
// ==========================================
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

// ==========================================
// STATS GRID (overview cards)
// ==========================================
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

  const template = document.getElementById("overview-stat-card-template");
  if (!template) return;

  statConfig.forEach(stat => {
    let card;
    if (stat.link) {
      card = document.createElement("a");
      card.href = stat.link;
      card.className = "dashboard-stat-card clickable-card flex flex-col justify-center";
    } else {
      card = document.createElement("div");
      card.className = "dashboard-stat-card flex flex-col justify-center";
    }

    let val;
    if (stat.subKey && stats[stat.key] !== undefined) {
      val = stats[stat.key][stat.subKey];
    } else {
      val = stats[stat.key];
    }

    const clone = template.content.cloneNode(true);
    clone.querySelector(".dashboard-stat-icon").textContent = stat.icon;
    clone.querySelector(".dashboard-stat-value").textContent = val !== undefined ? Number(val).toLocaleString() : "—";
    clone.querySelector(".dashboard-stat-label").textContent = stat.label;

    if (stat.label === "Interactions" && stats.interactions) {
      const meta = document.createElement("p");
      meta.className = "dashboard-stat-meta";
      const r = stats.interactions;
      meta.textContent = `${(r.reactions || 0).toLocaleString()} reactions · ${(r.saves || 0).toLocaleString()} saves`;
      clone.appendChild(meta);
    }

    card.appendChild(clone);
    container.appendChild(card);
  });
}

// ==========================================
// DASHBOARD OVERVIEW MAIN FUNCTION
// ==========================================
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
        healthContainer.innerHTML = "";
        
        const healthListDiv = document.createElement("div");
        healthListDiv.className = "health-list";

        const total = data.contents_count || 1;
        const activePct = Math.round(((data.active_contents || 0) / total) * 100);
        const inactivePct = Math.round(((data.inactive_contents || 0) / total) * 100);

        const healthRowTemplate = document.getElementById("overview-health-row-template");
        if (healthRowTemplate) {
          // Active contents row
          const activeRow = healthRowTemplate.content.cloneNode(true);
          const activeBadge = activeRow.querySelector(".status-badge");
          activeBadge.classList.add("active");
          activeBadge.textContent = "Active";
          activeRow.querySelector(".health-label-text").textContent = " Live Index";
          activeRow.querySelector(".health-value-text").textContent = `${data.active_contents.toLocaleString()} (${activePct}%)`;
          const activeBar = activeRow.querySelector(".overview-breakdown-bar");
          activeBar.classList.add("bar-active");
          activeBar.style.width = `${activePct}%`;
          healthListDiv.appendChild(activeRow);

          // Inactive contents row
          const inactiveRow = healthRowTemplate.content.cloneNode(true);
          const inactiveBadge = inactiveRow.querySelector(".status-badge");
          inactiveBadge.classList.add("inactive");
          inactiveBadge.textContent = "Inactive";
          inactiveRow.querySelector(".health-label-text").textContent = " Hidden Archive";
          inactiveRow.querySelector(".health-value-text").textContent = `${data.inactive_contents.toLocaleString()} (${inactivePct}%)`;
          const inactiveBar = inactiveRow.querySelector(".overview-breakdown-bar");
          inactiveBar.classList.add("bar-inactive");
          inactiveBar.style.width = `${inactivePct}%`;
          healthListDiv.appendChild(inactiveRow);
        }

        // Moderation Queue alert
        const queueTemplate = document.getElementById("overview-moderation-queue-template");
        if (queueTemplate) {
          const queueClone = queueTemplate.content.cloneNode(true);
          queueClone.querySelector(".moderation-queue-link").href = "/admin/contents?published=false";
          queueClone.querySelector(".badge-pending").textContent = `${data.review_queue_count} pending`;
          healthListDiv.appendChild(queueClone);
        }

        // Ingestion Growth (if any)
        if (data.growth_trends && data.growth_trends.length > 0) {
          const trendTemplate = document.getElementById("overview-growth-trend-template");
          const trendItemTemplate = document.getElementById("overview-growth-trend-item-template");
          
          if (trendTemplate && trendItemTemplate) {
            const trendClone = trendTemplate.content.cloneNode(true);
            const chartList = trendClone.querySelector(".trend-chart-list");
            
            const maxTrend = Math.max(...data.growth_trends.map(t => t.count), 1);
            data.growth_trends.forEach(t => {
              const pct = Math.round((t.count / maxTrend) * 100);
              const itemClone = trendItemTemplate.content.cloneNode(true);
              itemClone.querySelector(".trend-chart-date").textContent = t.date;
              itemClone.querySelector(".overview-breakdown-bar").style.width = `${pct}%`;
              itemClone.querySelector(".trend-chart-value").textContent = t.count;
              chartList.appendChild(itemClone);
            });
            healthListDiv.appendChild(trendClone);
          }
        }

        healthContainer.appendChild(healthListDiv);
      }

      // 3. Render Real-time Ingestion Activities
      const ingestContainer = document.getElementById("recent-ingest-container");
      if (ingestContainer) {
        ingestContainer.innerHTML = "";
        if (!data.recent_ingested || data.recent_ingested.length === 0) {
          ingestContainer.appendChild(getEmptyStateHtml("No recent ingestions.", "", "loading-height-sm"));
        } else {
          const ul = document.createElement("ul");
          ul.className = "activity-feed";

          const logItemTemplate = document.getElementById("overview-ingest-log-item-template");

          if (logItemTemplate) {
            data.recent_ingested.forEach(r => {
              const clone = logItemTemplate.content.cloneNode(true);
              let badgeClass = "user";
              let badgeIcon = "📰";
              if (r.type === "video") { badgeClass = "active"; badgeIcon = "🎥"; }
              else if (r.type === "post") { badgeClass = "admin"; badgeIcon = "💬"; }

              const iconDiv = clone.querySelector(".ingest-log-icon");
              iconDiv.textContent = badgeIcon;
              iconDiv.className = `activity-icon icon-save ingest-log-icon flex-center`;

              const badge = clone.querySelector(".badge-type-compact");
              badge.className = `status-badge ${badgeClass} badge-type-compact`;
              badge.textContent = r.type;

              const link = clone.querySelector(".activity-target");
              link.href = `/admin/contents?search=${r.id}`;
              link.textContent = `#${r.id}`;

              clone.querySelector(".ingest-log-title").textContent = r.title;
              clone.querySelector(".ingest-log-meta").textContent = r.time;

              ul.appendChild(clone);
            });
          }
          ingestContainer.appendChild(ul);
        }
      }

      // 4. Render Categories Distribution
      const categoriesContainer = document.getElementById("categories-distribution-container");
      if (categoriesContainer) {
        categoriesContainer.innerHTML = "";
        if (!data.by_category || data.by_category.length === 0) {
          categoriesContainer.appendChild(getEmptyStateHtml("No categories mapped.", "", "loading-height-sm"));
        } else {
          const listDiv = document.createElement("div");
          listDiv.className = "dist-list";

          const distTemplate = document.getElementById("overview-dist-row-template");
          const maxVal = Math.max(...data.by_category.map(c => c.count), 1);

          if (distTemplate) {
            data.by_category.forEach(c => {
              const pct = Math.round((c.count / maxVal) * 100);
              const clone = distTemplate.content.cloneNode(true);
              
              const link = clone.querySelector(".dist-row-link");
              link.href = `/admin/contents?category=${c.slug}`;
              
              clone.querySelector(".dist-row-name").textContent = c.name;
              clone.querySelector(".dist-row-count").textContent = `${c.count.toLocaleString()} items`;
              
              const bar = clone.querySelector(".overview-breakdown-bar");
              bar.classList.add("bar-purple");
              bar.style.width = `${pct}%`;
              
              listDiv.appendChild(clone);
            });
          }
          categoriesContainer.appendChild(listDiv);
        }
      }

      // 5. Render Sources Distribution
      const sourcesContainer = document.getElementById("sources-distribution-container");
      if (sourcesContainer) {
        sourcesContainer.innerHTML = "";
        if (!data.by_source || data.by_source.length === 0) {
          sourcesContainer.appendChild(getEmptyStateHtml("No source statistics.", "", "loading-height-sm"));
        } else {
          const listDiv = document.createElement("div");
          listDiv.className = "dist-list";

          const distTemplate = document.getElementById("overview-dist-row-template");
          const maxVal = Math.max(...data.by_source.map(s => s.count), 1);

          if (distTemplate) {
            data.by_source.forEach(s => {
              const pct = Math.round((s.count / maxVal) * 100);
              const clone = distTemplate.content.cloneNode(true);
              
              const link = clone.querySelector(".dist-row-link");
              link.href = `/admin/contents?source=${s.slug}`;
              
              clone.querySelector(".dist-row-name").textContent = s.name;
              clone.querySelector(".dist-row-count").textContent = `${s.count.toLocaleString()} items`;
              
              const bar = clone.querySelector(".overview-breakdown-bar");
              bar.classList.add("bar-teal");
              bar.style.width = `${pct}%`;
              
              listDiv.appendChild(clone);
            });
          }
          sourcesContainer.appendChild(listDiv);
        }
      }

      // 5b. Render Product Sources Distribution
      const productSourcesContainer = document.getElementById("product-sources-distribution-container");
      if (productSourcesContainer) {
        productSourcesContainer.innerHTML = "";
        if (!data.product_by_source || data.product_by_source.length === 0) {
          productSourcesContainer.appendChild(getEmptyStateHtml("No product source statistics.", "", "loading-height-sm"));
        } else {
          const listDiv = document.createElement("div");
          listDiv.className = "dist-list";

          const distTemplate = document.getElementById("overview-dist-row-template");
          const maxVal = Math.max(...data.product_by_source.map(s => s.count), 1);

          if (distTemplate) {
            data.product_by_source.forEach(s => {
              const pct = Math.round((s.count / maxVal) * 100);
              const clone = distTemplate.content.cloneNode(true);
              
              const link = clone.querySelector(".dist-row-link");
              link.href = `/admin/items?source=${s.slug}`;
              
              clone.querySelector(".dist-row-name").textContent = s.name;
              clone.querySelector(".dist-row-count").textContent = `${s.count.toLocaleString()} products`;
              
              const bar = clone.querySelector(".overview-breakdown-bar");
              bar.classList.add("bar-purple");
              bar.style.width = `${pct}%`;
              
              listDiv.appendChild(clone);
            });
          }
          productSourcesContainer.appendChild(listDiv);
        }
      }

      // 5c. Render Top Content Providers Performance
      const topContentProvidersContainer = document.getElementById("top-content-providers-container");
      if (topContentProvidersContainer) {
        topContentProvidersContainer.innerHTML = "";
        if (!data.top_performing_content || data.top_performing_content.length === 0) {
          topContentProvidersContainer.appendChild(getEmptyStateHtml("No provider data.", "", "loading-height-sm"));
        } else {
          const listDiv = document.createElement("div");
          listDiv.className = "dist-list";

          const distTemplate = document.getElementById("overview-dist-row-template");
          const maxVal = Math.max(...data.top_performing_content.map(s => s.views), 1);

          if (distTemplate) {
            data.top_performing_content.forEach(s => {
              const pct = Math.round((s.views / maxVal) * 100);
              const clone = distTemplate.content.cloneNode(true);
              
              const link = clone.querySelector(".dist-row-link");
              link.href = `/admin/contents?source=${s.slug}&sort_by=view_count&sort_dir=desc`;
              
              clone.querySelector(".dist-row-name").textContent = s.name;
              clone.querySelector(".dist-row-count").textContent = `${s.views.toLocaleString()} views`;
              
              const bar = clone.querySelector(".overview-breakdown-bar");
              bar.classList.add("bar-trend");
              bar.style.width = `${pct}%`;
              
              listDiv.appendChild(clone);
            });
          }
          topContentProvidersContainer.appendChild(listDiv);
        }
      }

      // 5d. Render Top Product Providers Performance
      const topProductProvidersContainer = document.getElementById("top-product-providers-container");
      if (topProductProvidersContainer) {
        topProductProvidersContainer.innerHTML = "";
        if (!data.top_performing_product || data.top_performing_product.length === 0) {
          topProductProvidersContainer.appendChild(getEmptyStateHtml("No merchant data.", "", "loading-height-sm"));
        } else {
          const listDiv = document.createElement("div");
          listDiv.className = "dist-list";

          const distTemplate = document.getElementById("overview-dist-row-template");
          const maxVal = Math.max(...data.top_performing_product.map(s => s.clicks), 1);

          if (distTemplate) {
            data.top_performing_product.forEach(s => {
              const pct = Math.round((s.clicks / maxVal) * 100);
              const clone = distTemplate.content.cloneNode(true);
              
              const link = clone.querySelector(".dist-row-link");
              link.href = `/admin/items?source=${s.slug}&sort_by=click_count&sort_dir=desc`;
              
              clone.querySelector(".dist-row-name").textContent = s.name;
              clone.querySelector(".dist-row-count").textContent = `${s.clicks.toLocaleString()} clicks`;
              
              const bar = clone.querySelector(".overview-breakdown-bar");
              bar.classList.add("bar-trend", "bar-orange");
              bar.style.width = `${pct}%`;
              
              listDiv.appendChild(clone);
            });
          }
          topProductProvidersContainer.appendChild(listDiv);
        }
      }

      // 5e. Render Provider Activity Summary
      const providerActivitiesContainer = document.getElementById("provider-activities-container");
      if (providerActivitiesContainer) {
        providerActivitiesContainer.innerHTML = "";
        if (!data.provider_activities || data.provider_activities.length === 0) {
          providerActivitiesContainer.appendChild(getEmptyStateHtml("No active providers.", "", "loading-height-sm"));
        } else {
          const ul = document.createElement("ul");
          ul.className = "activity-feed";

          const providerTemplate = document.getElementById("overview-provider-activity-item-template");

          if (providerTemplate) {
            data.provider_activities.forEach(s => {
              const clone = providerTemplate.content.cloneNode(true);
              
              clone.querySelector(".provider-name").textContent = s.name;
              clone.querySelector(".provider-slug").textContent = `slug: ${s.slug}`;
              clone.querySelector(".provider-content-count").textContent = s.content_count.toLocaleString();
              clone.querySelector(".provider-product-count").textContent = s.product_count.toLocaleString();
              
              const activityTime = s.latest_activity ? formatDate(s.latest_activity) : "No activity";
              clone.querySelector(".provider-activity-time").textContent = activityTime;
              
              ul.appendChild(clone);
            });
          }
          providerActivitiesContainer.appendChild(ul);
        }
      }

    })
    .catch(err => {
      console.error(err);
      container.innerHTML = getErrorStateHtml("Unable to load dashboard metrics. Please try again later.");
    });
}
