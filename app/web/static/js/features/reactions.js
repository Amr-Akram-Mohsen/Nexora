function updateReactionsCount(wrapper, delta = 1) {
    const countEl = wrapper.querySelector(`.reaction-count`);
    if (!countEl) return;

    const current = parseInt(countEl.textContent.replace(/\D/g, ""), 10) || 0;
    countEl.textContent = Math.max(0, current + delta);
}


function updateReactionUI(targetItem, reactionType, status) {
    const targetBtn =
        targetItem.querySelector(`
        .react-btn[data-reaction="${reactionType}"]`
        );

    const activeBtn =
        targetItem.querySelector(`
        .react-btn.active`
        );

    // if (status === 'added' || status === 'changed') {
    //     targetBtn.classList.replace('btn--outline', 'btn--default');
    // }

    targetBtn.classList.toggle('active', status === 'added' || status === 'changed');
    // targetBtn.classList.toggle('active', status !== 'removed');    

    if (status === 'changed' && activeBtn && activeBtn !== targetBtn) {
        activeBtn.classList.remove('active');
    }

    // if (status === 'changed') {
    //     activeBtn.classList.replace('btn--default', 'btn--outline');
    // }

    if (targetItem.hasAttribute('data-comment-id')) {
        if (status === 'added') {
            updateReactionsCount(targetBtn, 1);
        } else if (status === 'removed') {
            updateReactionsCount(targetBtn, -1);
        } else if (status === 'changed') {
            updateReactionsCount(targetBtn, 1);
        }

        if (status === 'changed' && activeBtn && activeBtn !== targetBtn) {
            updateReactionsCount(activeBtn, -1);
        }
    }
}

async function initAllReactions() {
    const buttons = Array.from(document.querySelectorAll(".react-btn"));
    const targets = [];

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        if (!item) return;
        if (item.hasAttribute('data-comment-id')) {
            targets.push({ 'type': 'comment', 'id': item.dataset.commentId });
        } else {
            targets.push({ 'type': item.dataset.type, 'id': item.dataset.id });
        }
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

    // Prepare query parameters
    const params = new URLSearchParams();
    for (const t of uniqueTargets) {
        params.append("type", t.type);
        params.append("id", t.id);
    }

    try {
        const res = await fetch(`/check-react-batch?${params.toString()}`);

        if (!res.ok) return;

        const data = await res.json();

        buttons.forEach(btn => {
            const item = btn.closest("[data-id]");
            if (!item) return;
            let key = null;
            if (item.hasAttribute('data-comment-id')) {
                key = `comment:${item.dataset.commentId}`;
            } else {
                key = `${item.dataset.type}:${item.dataset.id}`;
            }
            btn.classList.toggle('active', btn.dataset.reaction === data[key]);
        });
    } catch (error) {
        console.error("Could not initialize reactions", error);
    }
}
