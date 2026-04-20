function renderList(containerId, items, config) {
  const container = document.getElementById(containerId);
  container.className = "dashboard-list";
  container.innerHTML = "";

  items.forEach(item => {
    const div = document.createElement("div");
    div.className = "dashboard-item";

    const title = document.createElement("p");
    title.className = "dashboard-title";
    title.textContent = item[config.titleField] || "_";

    div.appendChild(title);

    // 🔹 EXTRA FIELDS (THIS IS THE NEW PART)
    config.fields.forEach(field => {
      const meta = document.createElement("p");
      meta.className = "dashboard-meta";

      let value = item[field];

      // simple formatting
      if (value === null || value === undefined) {
        value = "—";
      }

      meta.textContent = `${field}: ${value}`;
      div.appendChild(meta);
    });

    if (config.enableDelete) {
      const btn = document.createElement("button");
      btn.className = "dashboard-delete-btn";
      btn.textContent = "Delete";

      btn.addEventListener("click", () => {
        renderDelete(config.domain, item.id);
      });

      div.appendChild(btn);
    }

    container.appendChild(div);
  });
}

function renderDelete(domain, id) {
  fetch(`/api/${domain}/${id}`, { method: "DELETE" })
    .then(() => renderLoad(domain));
}

const domainTitleField = {
  "articles": "title",
  "items": "name",
  "users": "name",
  "interactions": "type",
}

const domainConfig = {
  articles: {
    titleField: "title",
    fields: ["published_at", "view_count"]
  },
  items: {
    titleField: "name",
    fields: ["rating", "created_at"]
  },
  users: {
    titleField: "name",
    fields: ["email", "created_at"]
  },
  interactions: {
    titleField: "content",
    fields: ["created_at"]
  }
};

function renderLoad(domain) {
  const container = document.getElementById(`${domain}-container`);

  container.className = "dashboard-list";
  container.innerHTML = "<p class='loading'>Loading...</p>";

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

      // ❌ ERROR STATE (ADD HERE)
      container.innerHTML = `
        <p class="error">
          Failed to load ${domain}. Please try again.
        </p>
      `;
    });
}

// renderLoad();