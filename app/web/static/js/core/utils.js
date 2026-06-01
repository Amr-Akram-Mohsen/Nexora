function setLoading(button, isLoading) {
    if (!button) return;
    if (isLoading) {
        button.classList.add('is-loading');
    } else {
        button.classList.remove('is-loading');
    }
}

function toggleActive(el) {
    el.classList.toggle("active", !el.classList.contains('active'));
}

