const originalFetch = window.fetch;
window.fetch = async function (...args) {
    let [resource, config] = args;
    if (config && config.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method.toUpperCase())) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (csrfToken) {
            config.headers = {
                ...(config.headers || {}),
                'X-CSRFToken': csrfToken
            };
        }
    }
    return originalFetch(resource, config);
};
