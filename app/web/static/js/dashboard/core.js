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
        if (confirm(`Are you sure you want to delete this item?`)) {
          renderDelete(config.domain, item.id);
        }
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
        enableDelete: domain !== "interactions",
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