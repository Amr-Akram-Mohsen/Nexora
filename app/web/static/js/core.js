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
    initSearchHighlighting();

    applyMode();
    initFlashMessages();
}

// Run on page load and when coming back via back/forward buttons
function initUserInteractions() {
    if (isAuthenticated) {
        initAllReactions();
        initAllSaves();
    }
}

function initUserAuth() {
    initPasswordToggles();
    initPasswordStrength();
    initConfirmMatch();
    initAuthFormLoading();
}

const generalMsg = 'please sign in to ';

