const { isAuthenticated, userEmail } = window.APP;
// ── Auth guard (existing — preserved) ─────────────────────────────────────────
function ensureAuthenticated(event, btn, message) {
    if (!isAuthenticated) {
        event.preventDefault();
        showInlineTooltip(btn, message);
        return false;
    }
    return true;
}

// ── Auth form loading state ────────────────────────────────────────────────────
function initAuthFormLoading() {
    const form = document.getElementById("auth-form");
    if (!form) return;
    form.addEventListener("submit", () => {
        const btn = form.querySelector(".auth-btn[type='submit']");
        if (btn) btn.classList.add("is-loading");
    });
}

function handleAuthClick(e) {
    const googleAuth = e.target.closest('.google-auth-btn');
    if (!googleAuth) return false;

    const url = googleAuth.dataset.url;
    if (url) window.location.href = url;
    return true;
}


