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

    const endpoint = window.APP?.urls?.view || "/view";
    fetch(endpoint, { method: "POST", body: fd })
        .catch(() => {});
}

// ── RECOMMENDATION TRACKING SYSTEM ──

document.addEventListener("DOMContentLoaded", () => {
    // 1. Identify the current page context ID
    const detailPage = document.querySelector('.detail-page');
    const contextId = detailPage ? detailPage.dataset.id : null;

    // 2. Track recommendation block impressions
    const containers = document.querySelectorAll('[data-recommendation-container]');
    
    // Track each recommendation widget rendering
    containers.forEach(container => {
        const entityType = container.dataset.recommendationContainer;
        let entityIds = [];
        try {
            entityIds = JSON.parse(container.dataset.entityIds || '[]');
        } catch (e) {
            console.error("Failed to parse entity IDs for tracking:", e);
        }

        if (entityIds && entityIds.length > 0) {
            const payload = {
                event_type: "impression",
                entity_type: entityType,
                context_id: contextId ? String(contextId) : null,
                entity_ids: entityIds.map(id => typeof id === 'number' ? id : parseInt(id) || id),
                timestamp: new Date().toISOString()
            };

            const endpoint = window.APP?.urls?.trackImpression || "/track/impression";
            fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                console.debug("Tracked recommendation impression:", data);
            })
            .catch(err => {
                console.error("Failed to track recommendation impression:", err);
            });
        }

        // 3. Track recommendation click events
        container.addEventListener("click", (e) => {
            // Check if the clicked target is inside an interactive element that is not the main link (like compare/save/reactions buttons)
            if (e.target.closest('button, .interactions-compact, .interactions, .alert')) {
                return;
            }

            const card = e.target.closest('[data-id]');
            if (card) {
                const entityId = card.dataset.id;
                if (entityId) {
                    const payload = {
                        event_type: "click",
                        entity_type: entityType,
                        entity_id: String(entityId),
                        context_id: contextId ? String(contextId) : null,
                        timestamp: new Date().toISOString()
                    };

                    const endpoint = window.APP?.urls?.trackClick || "/track/click";
                    fetch(endpoint, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(payload)
                    })
                    .then(res => res.json())
                    .then(data => {
                        console.debug("Tracked recommendation click:", data);
                    })
                    .catch(err => {
                        console.error("Failed to track recommendation click:", err);
                    });
                }
            }
        });
    });
});
