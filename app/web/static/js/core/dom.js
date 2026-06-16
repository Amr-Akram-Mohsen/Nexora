// ==============================
// GLOBAL MODAL SYSTEM
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
// GLOBAL MODAL EVENT DELEGATION
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("click", (e) => {
    // Backdrop click
    if (e.target.classList.contains("dashboard-modal-overlay")) {
      e.target.classList.remove("active");
      return;
    }
    // Dismiss button click
    const dismissBtn = e.target.closest("[data-dismiss='modal'], .dashboard-modal-close-x");
    if (dismissBtn) {
      const modal = dismissBtn.closest(".dashboard-modal-overlay");
      if (modal) {
        modal.classList.remove("active");
      }
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const activeModal = document.querySelector(".dashboard-modal-overlay.active");
      if (activeModal) {
        activeModal.classList.remove("active");
      }
    }
  });
});
