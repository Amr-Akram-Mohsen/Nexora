function initTheme() {
    const saved = localStorage.getItem('theme');
    const isDark = saved === 'dark';
    document.documentElement.classList.toggle('dark-mode', isDark);
    document.documentElement.classList.toggle('light-mode', !isDark);
    if (document.body) {
        document.body.classList.toggle('dark-mode', isDark);
        document.body.classList.toggle('light-mode', !isDark);
    }
    syncModeUI();
}

function syncModeUI() {
    const isDark = document.documentElement.classList.contains('dark-mode') || document.body?.classList.contains('dark-mode');
    document.querySelectorAll('.mode-toggle').forEach(btn => {
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = isDark ? 'far fa-sun' : 'far fa-moon';
        }
        btn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        btn.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
    });
}

function applyMode() {
    const isDark = document.documentElement.classList.contains('dark-mode');
    if (document.body) {
        document.body.classList.toggle('dark-mode', isDark);
        document.body.classList.toggle('light-mode', !isDark);
    }
    syncModeUI();
}

function handleModeToggle() {
    const isDark = document.documentElement.classList.contains('dark-mode') || document.body?.classList.contains('dark-mode');
    const nextIsDark = !isDark;

    document.documentElement.classList.toggle('dark-mode', nextIsDark);
    document.documentElement.classList.toggle('light-mode', !nextIsDark);
    if (document.body) {
        document.body.classList.toggle('dark-mode', nextIsDark);
        document.body.classList.toggle('light-mode', !nextIsDark);
    }

    localStorage.setItem('theme', nextIsDark ? 'dark' : 'light');
    syncModeUI();
}

function handleThemeClick(e) {
    const modeToggle = e.target.closest('.mode-toggle');
    if (!modeToggle) return false;

    handleModeToggle();
    return true;
}
