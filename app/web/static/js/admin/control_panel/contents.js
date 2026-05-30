// app/web/static/js/admin/control_panel/contents.js

(function () {
  // Page-level State Management
  let currentPage = 1;
  let perPage = 20;
  let totalItems = 0;
  let totalPages = 1;
  let selectedIds = new Set();
  let searchDebounce = null;
  let categoriesList = [];

  // ==============================
  // INITIALIZATION
  // ==============================
  document.addEventListener("DOMContentLoaded", () => {
    loadMetadata();
    setupEventListeners();
  });

  // ==============================
  // LOAD DYNAMIC FILTERS DATA
  // ==============================
  function loadMetadata() {
    fetch("/admin/contents/meta")
      .then((res) => {
        if (!res.ok) throw new Error("Metadata fetch failed");
        return res.json();
      })
      .then((meta) => {
        categoriesList = meta.categories || [];
        
        // Populate Section Filter
        const sectionSelect = document.getElementById("filter-section");
        (meta.sections || []).forEach((sec) => {
          const opt = document.createElement("option");
          opt.value = sec.slug;
          opt.textContent = sec.name;
          sectionSelect.appendChild(opt);
        });

        // Populate Category Filter
        const categorySelect = document.getElementById("filter-category");
        const bulkCatSelect = document.getElementById("bulk-category-select");
        const quickCatSelect = document.getElementById("quick-cat-select");

        categoriesList.forEach((cat) => {
          // Main Filter Dropdown
          const opt1 = document.createElement("option");
          opt1.value = cat.slug;
          opt1.textContent = cat.name;
          categorySelect.appendChild(opt1);

          // Bulk Operations Dropdown
          const opt2 = document.createElement("option");
          opt2.value = cat.id;
          opt2.textContent = cat.name;
          bulkCatSelect.appendChild(opt2);

          // Quick Modal Dropdown
          const opt3 = document.createElement("option");
          opt3.value = cat.id;
          opt3.textContent = cat.name;
          quickCatSelect.appendChild(opt3);
        });

        // Populate Source Filter
        const sourceSelect = document.getElementById("filter-source");
        (meta.sources || []).forEach((src) => {
          const opt = document.createElement("option");
          opt.value = src.slug;
          opt.textContent = src.name;
          sourceSelect.appendChild(opt);
        });

        // Once metadata is ready, load first list of contents
        fetchContents();
      })
      .catch((err) => {
        console.error("Could not load filters metadata:", err);
        showToast("Error loading catalog metadata filters.", "error");
        fetchContents(); // Fallback load contents anyways
      });
  }

  // ==============================
  // FETCH CONTENTS CATALOG
  // ==============================
  function fetchContents() {
    const tableBody = document.getElementById("contents-table-body");
    tableBody.innerHTML = `
      <tr>
        <td colspan="7" class="table-loading-cell">
          <div class="dashboard-loading" style="min-height:240px;">
            <div class="spinner"></div>
            <p>Loading contents catalog...</p>
          </div>
        </td>
      </tr>
    `;

    // Construct URL with query parameters
    const params = new URLSearchParams();
    params.append("page", currentPage);
    params.append("per_page", perPage);
    params.append("sort_by", document.getElementById("sort-by").value);
    params.append("sort_dir", document.getElementById("sort-dir").value);

    // Apply active filters
    const search = document.getElementById("content-search").value;
    if (search.trim()) params.append("search", search.trim());

    const type = document.getElementById("filter-type").value;
    if (type) params.append("type", type);

    const section = document.getElementById("filter-section").value;
    if (section) params.append("section", section);

    const category = document.getElementById("filter-category").value;
    if (category) params.append("category", category);

    const source = document.getElementById("filter-source").value;
    if (source) params.append("source", source);

    const status = document.getElementById("filter-status").value;
    if (status) params.append("status", status);

    const active = document.getElementById("filter-active").value;
    if (active) params.append("active", active);

    const published = document.getElementById("filter-published").value;
    if (published) params.append("published", published);

    const quality = document.getElementById("filter-quality").value;
    if (quality) params.append("quality", quality);

    const dateType = document.getElementById("filter-date-type").value;
    params.append("date_type", dateType);

    const startDate = document.getElementById("filter-start-date").value;
    if (startDate) params.append("start_date", startDate);

    const endDate = document.getElementById("filter-end-date").value;
    if (endDate) params.append("end_date", endDate);

    fetch(`/admin/contents/?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error("Catalog fetch failed");
        return res.json();
      })
      .then((data) => {
        totalItems = data.total || 0;
        totalPages = data.pages || 1;
        renderTable(data.items || []);
        renderPagination();
      })
      .catch((err) => {
        console.error(err);
        tableBody.innerHTML = `
          <tr>
            <td colspan="7" class="table-loading-cell">
              <div class="dashboard-error" style="min-height:160px; padding: 2rem; text-align: center;">
                <span style="font-size:2.5rem;">⚠️</span>
                <p style="margin-top: 0.5rem; font-weight: var(--weight-bold);">Failed to load catalog contents.</p>
                <button class="user-action-btn" onclick="window.location.reload()" style="margin-top: 0.75rem;">Retry Loading</button>
              </div>
            </td>
          </tr>
        `;
      });
  }

  // ==============================
  // RENDER TABLE ROWS
  // ==============================
  function renderTable(items) {
    const tableBody = document.getElementById("contents-table-body");
    tableBody.innerHTML = "";

    // Reset select all checkbox
    const selectAllCheckbox = document.getElementById("select-all-contents");
    selectAllCheckbox.checked = false;

    if (items.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" class="table-loading-cell">
            <div class="dashboard-empty" style="min-height:200px;">
              <span style="font-size:2.5rem; margin-bottom:0.75rem;">📭</span>
              <p>No content records found matching filters.</p>
              <p style="font-size:0.8rem; margin-top:0.25rem; opacity:0.7;">Adjust your keywords, categories, or health flags.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.style.cursor = "pointer";

      // Bind row clicks (excluding actions, checkboxes, or double-clicks)
      tr.addEventListener("click", (e) => {
        if (
          e.target.type === "checkbox" ||
          e.target.closest("button") ||
          e.target.closest("a") ||
          e.target.classList.contains("quick-cat-trigger")
        ) {
          return;
        }
        const checkbox = tr.querySelector(".row-select-checkbox");
        if (checkbox) {
          checkbox.checked = !checkbox.checked;
          toggleItemSelection(item.id, checkbox.checked);
        }
      });

      // Double click category trigger
      tr.addEventListener("dblclick", (e) => {
        if (e.target.closest("button") || e.target.closest("a")) return;
        showQuickCategoryModal(item.id, item.category_id);
      });

      // Type Badge styling
      let typeClass = "user";
      if (item.object_type === "article") typeClass = "admin";
      else if (item.object_type === "video") typeClass = "active";
      
      // Flags / Compliance Warnings HTML
      let flagsHtml = "";
      if (item.quality_issues && item.quality_issues.length > 0) {
        item.quality_issues.forEach((flag) => {
          if (flag === "missing_category") {
            flagsHtml += `<span class="status-badge inactive" style="margin: 0.125rem 0;" title="Content belongs to uncategorized and requires clean routing.">⚠️ Category</span> `;
          } else if (flag === "missing_metadata") {
            flagsHtml += `<span class="status-badge inactive" style="margin: 0.125rem 0; background: rgba(245,158,11,0.1); color: var(--brand-orange);" title="Missing essential title or preview details.">📝 Metadata</span> `;
          } else if (flag === "duplicate") {
            flagsHtml += `<span class="status-badge inactive" style="margin: 0.125rem 0; background: rgba(99,102,241,0.1); color: #6366f1;" title="Duplicate titles matching other aggregates.">👯 Duplicate</span> `;
          }
        });
      } else {
        flagsHtml = `<span class="status-badge active" title="No critical catalog/enrichment issues.">✓ Clean</span>`;
      }

      // Checkbox checked state
      const isChecked = selectedIds.has(item.id) ? "checked" : "";

      // Active / Inactive Badge
      const statusBadge = item.is_active
        ? `<span class="status-badge active">Active</span>`
        : `<span class="status-badge inactive">Inactive</span>`;

      // Ingest / Publish Dates
      const ingestTime = item.ingested_at ? new Date(item.ingested_at).toLocaleDateString() : "—";
      const publishTime = item.published_at ? new Date(item.published_at).toLocaleDateString() : "—";

      tr.innerHTML = `
        <td style="text-align: center; vertical-align: middle;">
          <input type="checkbox" class="row-select-checkbox" data-id="${item.id}" ${isChecked} />
        </td>
        <td>
          <span class="status-badge ${typeClass}" style="text-transform: capitalize;">${item.object_type}</span>
          <div style="font-size: 0.7rem; color: var(--muted-foreground); margin-top: 0.25rem;">ID: #${item.id}</div>
        </td>
        <td>
          <div style="font-weight: var(--weight-bold); font-size: var(--text-sm); line-height: 1.4;">
            ${item.url ? `<a href="${item.url}" target="_blank" class="activity-target" style="text-decoration: none;">${item.title} <i class="fas fa-external-link-alt" style="font-size: 0.65rem;"></i></a>` : item.title}
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.35rem; align-items: center;">
            <span style="font-size: 0.75rem; color: var(--muted-foreground);"><i class="fas fa-rss" style="margin-right: 0.25rem;"></i> ${item.source_name}</span>
            <span style="color: var(--border); font-size: 0.75rem;">|</span>
            <span class="quick-cat-trigger" style="font-size: 0.75rem; font-weight: var(--weight-md); color: var(--brand-purple); text-decoration: underline; cursor: pointer;" title="Double-click row to quickly move content.">
              <i class="fas fa-tag"></i> ${item.category_name}
            </span>
            <span style="color: var(--border); font-size: 0.75rem;">|</span>
            <span style="font-size: 0.75rem; color: var(--muted-foreground); font-weight: var(--weight-md);">${item.section_name}</span>
          </div>
        </td>
        <td>
          <div style="font-size: var(--text-sm);"><i class="far fa-eye" style="color: var(--muted-foreground);"></i> ${item.view_count.toLocaleString()}</div>
          <div style="font-size: var(--text-xs); color: var(--muted-foreground); margin-top: 0.25rem;"><i class="far fa-comment"></i> ${item.comment_count}</div>
        </td>
        <td>
          <div style="font-size: 0.75rem;"><strong>Ingested:</strong> ${ingestTime}</div>
          <div style="font-size: 0.75rem; margin-top: 0.2rem;"><strong>Published:</strong> ${publishTime}</div>
          <div style="margin-top: 0.35rem; display: flex; gap: 0.35rem; align-items: center;">
            ${statusBadge}
            ${item.is_published ? `<span class="status-badge active" style="background: rgba(59,130,246,0.1); color: var(--brand-blue);">Published</span>` : `<span class="status-badge inactive" style="background:rgba(100,116,139,0.1); color: #64748b;">Draft (Review)</span>`}
          </div>
        </td>
        <td>
          <div style="display: flex; flex-direction: column; align-items: flex-start; gap: 0.25rem;">
            ${flagsHtml}
          </div>
        </td>
        <td style="text-align: center; vertical-align: middle;">
          <button class="user-action-btn user-action-delete delete-btn" data-id="${item.id}" data-title="${item.title.replace(/"/g, '&quot;')}" title="Delete catalog and generic targets">
            🗑 Delete
          </button>
        </td>
      `;

      // Attach checkbox listeners
      const checkbox = tr.querySelector(".row-select-checkbox");
      checkbox.addEventListener("change", (e) => {
        toggleItemSelection(item.id, e.target.checked);
      });

      // Attach single delete click
      const deleteBtn = tr.querySelector(".delete-btn");
      deleteBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const cid = deleteBtn.getAttribute("data-id");
        const title = deleteBtn.getAttribute("data-title");
        showModal(
          "Safer Catalog Deletion",
          `Are you sure you want to completely delete "${title}"? This will safely wipe the database record, its polymorphic references (Article/Video/Post entries), reactions, logs, and comments. This is permanent.`,
          () => performSingleDelete(cid)
        );
      });

      tableBody.appendChild(tr);
    });
  }

  // ==============================
  // PAGINATION CONTROLS
  // ==============================
  function renderPagination() {
    const info = document.getElementById("pagination-info");
    const prevBtn = document.getElementById("prev-page-btn");
    const nextBtn = document.getElementById("next-page-btn");
    const indicator = document.getElementById("page-num-indicator");

    const start = totalItems === 0 ? 0 : (currentPage - 1) * perPage + 1;
    const end = Math.min(currentPage * perPage, totalItems);

    info.textContent = `Showing ${start.toLocaleString()} to ${end.toLocaleString()} of ${totalItems.toLocaleString()} contents`;
    indicator.textContent = `Page ${currentPage} of ${totalPages}`;

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
  }

  // ==============================
  // STATE SELECTIONS
  // ==============================
  function toggleItemSelection(id, isSelected) {
    if (isSelected) {
      selectedIds.add(id);
    } else {
      selectedIds.delete(id);
    }
    updateBulkToolbar();
  }

  function updateBulkToolbar() {
    const toolbar = document.getElementById("bulk-actions-toolbar");
    const countSpan = document.getElementById("bulk-selection-count");
    const applyBtn = document.getElementById("bulk-apply-btn");
    const actionSelect = document.getElementById("bulk-action-select");

    if (selectedIds.size > 0) {
      toolbar.style.display = "flex";
      countSpan.textContent = `${selectedIds.size.toLocaleString()} content items selected`;
      applyBtn.disabled = !actionSelect.value;
    } else {
      toolbar.style.display = "none";
      applyBtn.disabled = true;
    }
  }

  // ==============================
  // ACTIONS EXECUTION
  // ==============================
  function performSingleDelete(id) {
    fetch(`/admin/contents/${id}`, { method: "DELETE" })
      .then((res) => {
        if (!res.ok) throw new Error("Delete failed");
        return res.json();
      })
      .then((res) => {
        if (res.success) {
          showToast(res.message || "Content safely deleted.", "success");
          selectedIds.delete(parseInt(id));
          updateBulkToolbar();
          fetchContents();
        } else {
          showToast("Failed to delete content.", "error");
        }
      })
      .catch((err) => {
        console.error(err);
        showToast("Error executing content deletion.", "error");
      });
  }

  function applyBulkAction() {
    const action = document.getElementById("bulk-action-select").value;
    const categoryId = document.getElementById("bulk-category-select").value;
    
    if (!action) return;

    // Build payload
    const payload = {
      action: action,
      ids: Array.from(selectedIds)
    };

    if (action === "recategorize") {
      if (!categoryId) {
        showToast("Please select a target category for recategorization.", "warning");
        return;
      }
      payload.category_id = categoryId;
    }

    const actionText = action === "delete" 
      ? "permanently safe delete" 
      : `${action} (or update)`;

    showModal(
      "Confirm Bulk Action",
      `Are you sure you want to execute ${actionText} on the ${selectedIds.size} selected items?`,
      () => {
        fetch("/admin/contents/bulk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        })
          .then((res) => {
            if (!res.ok) throw new Error("Bulk action failed");
            return res.json();
          })
          .then((res) => {
            if (res.success) {
              showToast(res.message || "Bulk operation completed.", "success");
              selectedIds.clear();
              document.getElementById("bulk-action-select").value = "";
              document.getElementById("bulk-category-select").value = "";
              document.getElementById("bulk-category-select").style.display = "none";
              updateBulkToolbar();
              fetchContents();
            } else {
              showToast(res.error || "Bulk action failed.", "error");
            }
          })
          .catch((err) => {
            console.error(err);
            showToast("Error processing bulk operation.", "error");
          });
      }
    );
  }

  // ==============================
  // QUICK RECATEGORIZE MODAL
  // ==============================
  function showQuickCategoryModal(contentId, currentCategoryId) {
    const modal = document.getElementById("quick-category-modal");
    const idInput = document.getElementById("quick-cat-content-id");
    const select = document.getElementById("quick-cat-select");

    idInput.value = contentId;
    select.value = currentCategoryId || "";
    modal.style.display = "flex";
  }

  function hideQuickCategoryModal() {
    document.getElementById("quick-category-modal").style.display = "none";
  }

  function saveQuickCategory() {
    const contentId = document.getElementById("quick-cat-content-id").value;
    const categoryId = document.getElementById("quick-cat-select").value;

    if (!categoryId) {
      showToast("Please choose a category.", "warning");
      return;
    }

    fetch("/admin/contents/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "recategorize",
        ids: [parseInt(contentId)],
        category_id: parseInt(categoryId)
      })
    })
      .then((res) => res.json())
      .then((res) => {
        if (res.success) {
          showToast("Category quick-updated successfully.", "success");
          hideQuickCategoryModal();
          fetchContents();
        } else {
          showToast(res.error || "Recategorization failed.", "error");
        }
      })
      .catch((err) => {
        console.error(err);
        showToast("Error moving content.", "error");
      });
  }

  // ==============================
  // EVENT LISTENERS BINDING
  // ==============================
  function setupEventListeners() {
    const refreshBtn = document.getElementById("refresh-contents-btn");
    const searchInput = document.getElementById("content-search");
    const typeSelect = document.getElementById("filter-type");
    const sectionSelect = document.getElementById("filter-section");
    const categorySelect = document.getElementById("filter-category");
    const sourceSelect = document.getElementById("filter-source");
    const statusSelect = document.getElementById("filter-status");
    const activeSelect = document.getElementById("filter-active");
    const publishedSelect = document.getElementById("filter-published");
    const qualitySelect = document.getElementById("filter-quality");
    const dateTypeSelect = document.getElementById("filter-date-type");
    const startDateInput = document.getElementById("filter-start-date");
    const endDateInput = document.getElementById("filter-end-date");
    
    const sortBy = document.getElementById("sort-by");
    const sortDir = document.getElementById("sort-dir");
    const clearBtn = document.getElementById("clear-filters-btn");
    
    const selectAllCheckbox = document.getElementById("select-all-contents");
    
    const bulkActionSelect = document.getElementById("bulk-action-select");
    const bulkApplyBtn = document.getElementById("bulk-apply-btn");
    
    const prevBtn = document.getElementById("prev-page-btn");
    const nextBtn = document.getElementById("next-page-btn");
    const perPageSelect = document.getElementById("pagination-per-page");

    // Modal listeners
    const modalCancel = document.getElementById("quick-cat-cancel");
    const modalConfirm = document.getElementById("quick-cat-confirm");

    // Refresh action
    refreshBtn.addEventListener("click", () => {
      fetchContents();
    });

    // Debounced search input
    searchInput.addEventListener("input", () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        currentPage = 1;
        fetchContents();
      }, 400);
    });

    // Select input changes trigger fetch
    [
      typeSelect,
      sectionSelect,
      categorySelect,
      sourceSelect,
      statusSelect,
      activeSelect,
      publishedSelect,
      qualitySelect,
      dateTypeSelect,
      sortBy,
      sortDir
    ].forEach((element) => {
      element.addEventListener("change", () => {
        currentPage = 1;
        fetchContents();
      });
    });

    // Dates fetch trigger
    [startDateInput, endDateInput].forEach((element) => {
      element.addEventListener("change", () => {
        currentPage = 1;
        fetchContents();
      });
    });

    // Reset filters action
    clearBtn.addEventListener("click", () => {
      searchInput.value = "";
      typeSelect.value = "";
      sectionSelect.value = "";
      categorySelect.value = "";
      sourceSelect.value = "";
      statusSelect.value = "";
      activeSelect.value = "";
      publishedSelect.value = "";
      qualitySelect.value = "";
      dateTypeSelect.value = "published_at";
      startDateInput.value = "";
      endDateInput.value = "";
      sortBy.value = "published_at";
      sortDir.value = "desc";
      currentPage = 1;
      selectedIds.clear();
      updateBulkToolbar();
      fetchContents();
    });

    // Select All binding
    selectAllCheckbox.addEventListener("change", (e) => {
      const isChecked = e.target.checked;
      const visibleCheckboxes = document.querySelectorAll(".row-select-checkbox");
      visibleCheckboxes.forEach((checkbox) => {
        checkbox.checked = isChecked;
        const cid = parseInt(checkbox.getAttribute("data-id"));
        if (isChecked) {
          selectedIds.add(cid);
        } else {
          selectedIds.delete(cid);
        }
      });
      updateBulkToolbar();
    });

    // Bulk actions display and enabling
    bulkActionSelect.addEventListener("change", (e) => {
      const action = e.target.value;
      const bulkCategorySelect = document.getElementById("bulk-category-select");

      if (action === "recategorize") {
        bulkCategorySelect.style.display = "inline-block";
      } else {
        bulkCategorySelect.style.display = "none";
        bulkCategorySelect.value = "";
      }
      bulkApplyBtn.disabled = !action;
    });

    // Apply bulk action
    bulkApplyBtn.addEventListener("click", () => {
      applyBulkAction();
    });

    // Pagination listeners
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        fetchContents();
      }
    });

    nextBtn.addEventListener("click", () => {
      if (currentPage < totalPages) {
        currentPage++;
        fetchContents();
      }
    });

    perPageSelect.addEventListener("change", (e) => {
      perPage = parseInt(e.target.value);
      currentPage = 1;
      fetchContents();
    });

    // Quick Category modal triggers
    modalCancel.addEventListener("click", hideQuickCategoryModal);
    modalConfirm.addEventListener("click", saveQuickCategory);
    
    // Close quick modal on clicking background
    const quickModalOverlay = document.getElementById("quick-category-modal");
    quickModalOverlay.addEventListener("click", (e) => {
      if (e.target === quickModalOverlay) hideQuickCategoryModal();
    });
  }
})();
