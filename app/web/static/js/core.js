document.addEventListener("DOMContentLoaded", () => {
    initApp();
    initUserInteractions();
    initUserAuth();

    document.addEventListener("click", handleGlobalClicks);
    document.addEventListener("submit", handleGlobalSubmits);
    document.addEventListener("change", handleGlobalChanges);
});

window.addEventListener("pageshow", initUserInteractions);

function initApp() {
    initHeroSlider();
    initTheme();
    initHeaderScroll();
    initSearch();
    initSearchHighlighting();

    applyMode();
    initFlashMessages();
    if (typeof initProgressiveReveal === "function") initProgressiveReveal();
}

// Run on page load and when coming back via back/forward buttons
function initUserInteractions() {
    if (isAuthenticated) {
        if (typeof initAllReactions === "function") initAllReactions();
        if (typeof initAllSaves === "function") initAllSaves();
        if (typeof initSavedItemsPage === "function") initSavedItemsPage();
    }
}

function initUserAuth() {
    initPasswordToggles();
    initPasswordStrength();
    initConfirmMatch();
    initAuthFormLoading();
    if (typeof initProfileForms === "function") initProfileForms();
}

const generalMsg = 'please sign in to ';
