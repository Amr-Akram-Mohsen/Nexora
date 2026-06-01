function initTheme() {
    const saved = localStorage.getItem('theme');
    const isDark = saved === 'dark';
    document.documentElement.classList.toggle('dark-mode', isDark);
    document.documentElement.classList.toggle('light-mode', !isDark);

    syncModeUI();
}

function syncModeUI() {
    const btn = document.querySelector('.mode-toggle');
    const icon = btn?.querySelector('i');

    const isDark = document.body.classList.contains('dark-mode');

    icon?.classList.toggle('fa-moon', !isDark);
    icon?.classList.toggle('fa-sun', isDark);
}

function applyMode() {
    // sync body with html
    if (document.documentElement.classList.contains('dark-mode')) {
        document.body.classList.replace('light-mode', 'dark-mode');
    } else {
        document.body.classList.replace('dark-mode', 'light-mode');
    }

    syncModeUI();
}
function handleModeToggle() {
    const isDark = document.body.classList.contains('dark-mode');
    const nextIsDark = !isDark;

    document.body.classList.toggle('dark-mode', nextIsDark);
    document.body.classList.toggle('light-mode', !nextIsDark);

    localStorage.setItem('theme', nextIsDark ? 'dark' : 'light');

    syncModeUI();
}

function handleThemeClick(e) {
    const modeToggle = e.target.closest('.mode-toggle');
    if (!modeToggle) return false;

    handleModeToggle();
    return true;
}