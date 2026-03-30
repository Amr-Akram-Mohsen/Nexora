document.addEventListener("DOMContentLoaded", () => {
    initApp();
    initUserInteractions();
    document.addEventListener("click", handleGlobalClicks);
    document.addEventListener("submit", handleGlobalSubmits);
});

window.addEventListener("pageshow", initUserInteractions);

document.addEventListener("change", handleCountryToggle);


function initApp() {
    initHeroSlider();
    initTheme();

    // applyMode();
    handleFlashMessages();
}

// Run on page load and when coming back via back/forward buttons
function initUserInteractions() {
    if (isAuthenticated) {
        initAllReactions();
        initAllSaves();
    }
}

const generalMsg = 'please sign in to ';

function filterContent(chip) {
    chip.classList.toggle("active");
    
    const params = new URLSearchParams(window.location.search);
    const key = chip.dataset.filter;
    const value = chip.dataset.slug;
    
    const values = params.getAll(key);
    
    if (values.includes(value)) {
      params.delete(key);
      values.filter(v => v !== value).forEach(v => params.append(key, v));
    } else {
      params.append(key, value);
    }
    
    window.location.search = params.toString();
}

// let newsletterHandled = false;

function handleFlashMessages() {
    // ------------------------------
    // Global messages (top-right)
    // ------------------------------
    const globalMessages = document.querySelectorAll('.flash-messages .alert');
    globalMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(100%)';
            setTimeout(() => msg.remove(), 500);
        }, 2500);
    });
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


async function handleCountryToggle(e) {
    if (!e.target.classList.contains("country-toggle")) return;
    
    const country = e.target.value || "";
    
    await fetch("/set-country", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ country })
    });
    
    // Optional: reload page to apply country filtering
    window.location.reload();
    
}
