
// ── Inline Tooltip (existing — preserved) ────────────────────────────────────
function showInlineTooltip(targetEl, message, duration = 2000) {
    const msg = document.getElementById("inline-tooltip");
    if (!msg || !targetEl) return;
    msg.textContent = message;
    msg.classList.remove("is-hidden");
    msg.style.display = "block";

    const rect = targetEl.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
    const msgHeight = msg.offsetHeight;

    msg.style.top = `${rect.top + scrollTop - msgHeight - 8}px`;
    msg.style.left = `${rect.left + scrollLeft}px`;

    clearTimeout(msg._timeout);
    msg._timeout = setTimeout(() => {
        msg.classList.add("is-hidden");
        msg.style.display = "none";
    }, duration);
}

function initFlashMessages() {
    // ------------------------------
    // Global messages (top-right)
    // ------------------------------
    // Timers have been intentionally removed per user request.
    // Flash messages now persist until dismissed manually.
}

// ------------------------------
// Manual close for global messages
// ------------------------------
function closeFlashMsg(btn) {
    const alert = btn.parentElement;
    alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(100%)';
    setTimeout(() => alert.remove(), 300);
}

function handleFlashMessagesClick(e) {
    const messagesCloseBtn = e.target.closest('.alert-close');
    if (!messagesCloseBtn) return false;
    closeFlashMsg(messagesCloseBtn);
    return true;
}