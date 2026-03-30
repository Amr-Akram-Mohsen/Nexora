function trackImpression(el) {
    // Example payload
    const payload = {
        target_type: el.dataset.type,
        target_id: el.dataset.id,
        section: el.closest("[data-section]")?.dataset.section || null,
        ts: Date.now()
    };

    // For now: just debug / future hook
    console.debug("Impression:", payload);
}

function initCardViews() {
    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            trackImpression(entry.target);
            obs.unobserve(entry.target);
        });
    }, { threshold: 0.6 });

    document.querySelectorAll(".view-card").forEach(card => {
        observer.observe(card);
    });
}
// VIEW Article / Product

function sendView(targetType, targetId) {
    const fd = new FormData();
    fd.append("target_type", targetType);
    fd.append("target_id", targetId);

    fetch("/view", { method: "POST", body: fd })
        .catch(() => {});
}
