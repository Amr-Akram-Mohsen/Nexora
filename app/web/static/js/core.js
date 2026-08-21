document.addEventListener("DOMContentLoaded", () => {
    // Attach global delegation handlers first to ensure UI interactivity
    document.addEventListener("click", handleGlobalClicks);
    document.addEventListener("submit", handleGlobalSubmits);
    document.addEventListener("change", handleGlobalChanges);

    initApp();
    initUserInteractions();
    initUserAuth();
});

window.addEventListener("pageshow", initUserInteractions);

function initApp() {
    if (typeof initHeroSlider === "function") initHeroSlider();
    if (typeof initTheme === "function") initTheme();
    if (typeof initHeaderScroll === "function") initHeaderScroll();
    if (typeof initSearch === "function") initSearch();
    if (typeof initSearchHighlighting === "function") initSearchHighlighting();

    if (typeof applyMode === "function") applyMode();
    if (typeof initFlashMessages === "function") initFlashMessages();
    if (typeof initProgressiveReveal === "function") initProgressiveReveal();
}

// Run on page load and when coming back via back/forward buttons
function initUserInteractions() {
    if (window.APP?.isAuthenticated) {
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
