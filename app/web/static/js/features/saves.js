async function initAllSaves() {
    const buttons = Array.from(document.querySelectorAll(".save-btn"));
    const targets = [];

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        if (!item) return;
        targets.push({ 'type': item.dataset.type, 'id': item.dataset.id });
    });

    // Deduplicate targets
    const seen = new Set();
    const uniqueTargets = [];
    for (const t of targets) {
        const key = `${t.type}:${t.id}`;
        if (!seen.has(key)) {
            seen.add(key);
            uniqueTargets.push(t);
        }
    }

    if (uniqueTargets.length === 0) return;

    const params = new URLSearchParams();
    for (const t of uniqueTargets) {
        params.append("type", t.type);
        params.append("id", t.id);
    }

    try {
        const res = await fetch(`/check-save-batch?${params.toString()}`);
        if (!res.ok) return;

        const data = await res.json();

        buttons.forEach(btn => {
            const item = btn.closest("[data-id]");
            if (!item) return;
            const key = `${item.dataset.type}:${item.dataset.id}`;

            btn.classList.toggle('active', key in data);
        });
    } catch (error) {
        console.error("Could not initialize saves", error);
    }
}
