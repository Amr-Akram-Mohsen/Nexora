// app/web/static/js/admin/control_panel/contents.js

(function () {
  'use strict';

  // Page-level State Management
  // Page-level State Management
  window.contentsController = null;
  let selectedIds = new Set();
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
          const opt1 = document.createElement("option");
          opt1.value = cat.slug;
          opt1.textContent = cat.name;
          categorySelect.appendChild(opt1);

          const opt2 = document.createElement("option");
          opt2.value = cat.id;
          opt2.textContent = cat.name;
          bulkCatSelect.appendChild(opt2);

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

        applyContentsUrlFilters();

        // Once metadata is ready, init contents controller
        window.contentsController.init();
      })
      .catch((err) => {
        console.error("Could not load filters metadata:", err);
        showToast("Error loading catalog metadata filters.", "error");
        window.contentsController.init(); // Fallback
      });
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
      toolbar.classList.remove("is-hidden");
      countSpan.textContent = `${selectedIds.size.toLocaleString()} content items selected`;
      applyBtn.disabled = !actionSelect.value;
    } else {
      toolbar.classList.add("is-hidden");
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
          selectedIds.delete(parseInt(id, 10));
          updateBulkToolbar();
          window.contentsController.load(window.contentsController.currentPage);
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
              document.getElementById("bulk-category-select").classList.add("is-hidden");
              updateBulkToolbar();
              window.contentsController.load(window.contentsController.currentPage);
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
    modal.classList.add("active");
  }

  function hideQuickCategoryModal() {
    document.getElementById("quick-category-modal").classList.remove("active");
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
        ids: [parseInt(contentId, 10)],
        category_id: parseInt(categoryId, 10)
      })
    })
      .then((res) => res.json())
      .then((res) => {
        if (res.success) {
          showToast("Category quick-updated successfully.", "success");
          hideQuickCategoryModal();
          window.contentsController.load(window.contentsController.currentPage);
        } else {
          showToast(res.error || "Recategorization failed.", "error");
        }
      })
      .catch((err) => {
        console.error(err);
        showToast("Error moving content.", "error");
      });
  }

  function applyContentsUrlFilters() {
    if (typeof applyUrlFilters !== "function") return;
    applyUrlFilters({
      search: "content-search",
      type: "filter-type",
      section: "filter-section",
      category: "filter-category",
      source: "filter-source",
      status: "filter-status",
      active: "filter-active",
      published: "filter-published",
      quality: "filter-quality",
      date_type: "filter-date-type",
      start_date: "filter-start-date",
      end_date: "filter-end-date",
      sort_by: "sort-by",
      sort_dir: "sort-dir"
    });
  }




  // ==============================
  // EVENT LISTENERS BINDING
  // ==============================
  function setupEventListeners() {
    const clearBtn = document.getElementById("clear-filters-btn");
    const selectAllCheckbox = document.getElementById("select-all-contents");
    const bulkActionSelect = document.getElementById("bulk-action-select");
    const bulkApplyBtn = document.getElementById("bulk-apply-btn");

    // Modal listeners
    const modalCancel = document.getElementById("quick-cat-cancel");
    const modalConfirm = document.getElementById("quick-cat-confirm");

    // Reset filters action
    clearBtn.addEventListener("click", () => {
      document.getElementById("content-search").value = "";
      document.getElementById("filter-type").value = "";
      document.getElementById("filter-section").value = "";
      document.getElementById("filter-category").value = "";
      document.getElementById("filter-source").value = "";
      document.getElementById("filter-status").value = "";
      document.getElementById("filter-active").value = "";
      document.getElementById("filter-published").value = "";
      document.getElementById("filter-quality").value = "";
      document.getElementById("filter-date-type").value = "published_at";
      document.getElementById("filter-start-date").value = "";
      document.getElementById("filter-end-date").value = "";
      document.getElementById("sort-by").value = "id";
      document.getElementById("sort-dir").value = "desc";
      selectedIds.clear();
      updateBulkToolbar();
      window.contentsController.load(1);
    });

    // Select All binding
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener("change", (e) => {
        const isChecked = e.target.checked;
        const visibleCheckboxes = document.querySelectorAll(".row-select-checkbox");
        visibleCheckboxes.forEach((checkbox) => {
          checkbox.checked = isChecked;
          const cid = parseInt(checkbox.getAttribute("data-id"), 10);
          if (isChecked) {
            selectedIds.add(cid);
          } else {
            selectedIds.delete(cid);
          }
          const r = checkbox.closest("tr");
          if (r) {
            r.classList.toggle("is-selected", isChecked);
          }
        });
        updateBulkToolbar();
      });
    }

    // Bulk actions display and enabling
    bulkActionSelect.addEventListener("change", (e) => {
      const action = e.target.value;
      const bulkCategorySelect = document.getElementById("bulk-category-select");

      if (action === "recategorize") {
        bulkCategorySelect.classList.remove("is-hidden");
      } else {
        bulkCategorySelect.classList.add("is-hidden");
        bulkCategorySelect.value = "";
      }
      bulkApplyBtn.disabled = !action;
    });

    // Apply bulk action
    bulkApplyBtn.addEventListener("click", () => {
      applyBulkAction();
    });

    // Quick Category modal triggers
    modalConfirm.addEventListener("click", saveQuickCategory);

    // Table body event delegation
    const tableBody = document.getElementById("contents-table-body");
    tableBody.addEventListener("click", (e) => {
      const row = e.target.closest("tr");
      if (!row) return;

      const checkbox = row.querySelector(".row-select-checkbox");
      const cid = parseInt(row.dataset.id, 10);

      // Check if clicking actions or inputs
      if (
        e.target.type === "checkbox" ||
        e.target.closest("button") ||
        e.target.closest("a") ||
        e.target.classList.contains("quick-cat-trigger") ||
        e.target.closest(".quick-cat-trigger")
      ) {
        // If clicking checkbox manually
        if (e.target.type === "checkbox") {
          toggleItemSelection(cid, e.target.checked);
          row.classList.toggle("is-selected", e.target.checked);
        }
        return;
      }

      // Toggle selection on row click
      if (checkbox) {
        checkbox.checked = !checkbox.checked;
        toggleItemSelection(cid, checkbox.checked);
        row.classList.toggle("is-selected", checkbox.checked);
      }
    });

    tableBody.addEventListener("dblclick", (e) => {
      const row = e.target.closest("tr");
      if (!row) return;
      if (e.target.closest("button") || e.target.closest("a")) return;
      showQuickCategoryModal(row.dataset.id, row.dataset.categoryId);
    });

    // Inspect modal or detail page: delete action delegation
    document.body.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-action='delete-content']");
      if (!btn) return;
      const id    = parseInt(btn.dataset.id, 10);
      const title = btn.dataset.title || "this content";
      showModal(
        "Safer Catalog Deletion",
        `Are you sure you want to completely delete "${title}"? This is permanent.`,
        () => { 
          performSingleDelete(id); 
          const modal = document.getElementById("inspect-content-modal");
          if (modal) modal.classList.remove("active"); 
        }
      );
    });
  }

  // Define Controller Configuration
  window.contentsController = new AdminListController({
    domain: "contents",
    endpoint: "/admin/contents/",
    rowsEndpoint: "/admin/contents/rows",
    filterIds: [
      "filter-type", "filter-section", "filter-category", "filter-source",
      "filter-status", "filter-active", "filter-published", "filter-quality",
      "filter-date-type", "filter-start-date", "filter-end-date", "sort-by", "sort-dir"
    ],
    colspan: 9,
    onLoaded: () => {
      const selectAll = document.getElementById("select-all-contents");
      if (selectAll) selectAll.checked = false;
    },
    autoInit: false // Initialized manually inside loadMetadata()
  });

})();
