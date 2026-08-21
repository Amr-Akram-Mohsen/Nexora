// GLOBAL MODAL SYSTEM
let activeModalCallback = null;
let previousActiveElement = null;

function getFocusableElements(container) {
  return Array.from(container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )).filter(el => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden'));
}

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

  overlay.addEventListener('keydown', function(e) {
    if (e.key !== 'Tab') return;

    const focusableElements = getFocusableElements(overlay);
    if (focusableElements.length === 0) {
      e.preventDefault();
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === firstElement) {
        lastElement.focus();
        e.preventDefault();
      }
    } else {
      if (document.activeElement === lastElement) {
        firstElement.focus();
        e.preventDefault();
      }
    }
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
  previousActiveElement = document.activeElement;
  if (overlay) {
    overlay.classList.add("active");
    // Set focus to the first focusable element inside the modal
    setTimeout(() => {
      const focusable = getFocusableElements(overlay);
      if (focusable.length > 0) focusable[0].focus();
    }, 50);
  }
}

function closeModal() {
  const overlay = document.getElementById("dashboard-modal-overlay");
  if (overlay) overlay.classList.remove("active");
  activeModalCallback = null;
  if (previousActiveElement) {
    previousActiveElement.focus();
    previousActiveElement = null;
  }
}

// GLOBAL MODAL EVENT DELEGATION
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
