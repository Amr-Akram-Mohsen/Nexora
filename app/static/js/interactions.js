function updateReactionsCount(wrapper, delta = 1) {
    const countEl = wrapper.querySelector(`.reaction-count`);
    if (!countEl) return;

    const current = parseInt(countEl.textContent.replace(/\D/g, ""), 10) || 0;
    countEl.textContent = `(${current + delta})`;
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

    if (status === 'changed' && activeBtn) {
        activeBtn.classList.remove('active');
    }

    // if (status === 'changed') {
    //     activeBtn.classList.replace('btn--default', 'btn--outline');
    // }

    if (targetItem.hasAttribute('data-comment-id')) {
        updateReactionsCount(targetBtn, status == 'added' || status == 'changed' ? 1 : -1);
        if (activeBtn)
            updateReactionsCount(activeBtn, -1);
    }
}

async function initAllReactions() {
    const buttons = Array.from(document.querySelectorAll(".react-btn"));
    const targets = [];

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        if (item.hasAttribute('data-comment-id')) {
            targets.push({ 'type': 'comment', 'id': item.dataset.commentId });

        }
        targets.push({ ...item.dataset });
    });

    if (targets.size === 0) return;

    // Prepare query parameters
    const params = new URLSearchParams();
    for (const t of targets) {
        params.append("type", t.type);
        params.append("id", t.id);
    }

    const res = await fetch(`/check-react-batch?${params.toString()}`);

    if (!res.ok) return;

    const data = await res.json(); // expect: { "article:1": "like", "article:2": "dislike", ... }

    // Update UI
    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        let key = null;
        if (item.hasAttribute('data-comment-id')) {
            key = `comment:${item.dataset.commentId}`;
        } else {
            key = `${item.dataset.type}:${item.dataset.id}`;
        }
        btn.classList.toggle('active', btn.dataset.reaction === data[key]);
    });
}

async function initAllSaves() {
    const buttons = Array.from(document.querySelectorAll(".save-btn"));
    const targets = [];

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        targets.push({ ...item.dataset });
    });
    if (targets.size === 0) return;

    const params = new URLSearchParams();
    for (const t of targets) {
        params.append("type", t.type);
        params.append("id", t.id);
    }

    const res = await fetch(`/check-save-batch?${params.toString()}`);
    if (!res.ok) return;

    const data = await res.json(); // expect: { "article:1": true, "article:2": false }

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        const key = `${item.dataset.type}:${item.dataset.id}`;

        btn.classList.toggle('active', key in data);

    });
}

async function submitUserInteraction(
    targetItem,
    interactionType,
    targetBtn = null,
    content = null,
    context = {}
) {

    // Turn the button the user clicked into a spinner!
    if (targetBtn) setLoading(targetBtn, true);
    if (context.form) setLoading(context.form.querySelector('button[type="submit"]'), true);

    const targetType = targetItem.dataset.type;
    const targetId = targetItem.dataset.id;
    // const targetId = targetItem.dataset.commentId;

    const reactionType = targetBtn?.dataset.reaction;

    const fd = new FormData();

    fd.append("type", targetType);
    fd.append("id", targetId);
    fd.append("interaction_type", interactionType);


    if (interactionType === "react") {
        fd.append("reaction", reactionType);
        fd.append("comment_id", targetItem.dataset.commentId);
    }

    if (interactionType === "comment") {
        fd.append("comment", content);
        if (context.formType === "reply") fd.append("comment_id", targetItem.dataset.commentId);
    }

    const res = await fetch("/handle-interaction", {
        method: "POST",
        body: fd
    });

    const result = await res.json();

    if (!res.ok) {
        showInlineTooltip(
            context.form,
            res.error
        );
    } else {
        if (interactionType === 'react') {
            updateReactionUI(targetItem, reactionType, result.status);
        } else if (interactionType === 'save') {
            targetBtn.classList.toggle('active', result.status == 'saved')
        }
        else if (interactionType === "comment" && result?.success) {
            const list = context.formType === "reply"
                ? context.wrapper.querySelector('.comment__replies-list')
                : context.wrapper.querySelector(".comments__list");

            list.insertAdjacentHTML("afterbegin", result.comment);

            if (context.formType === 'comment')
                incrementCommentCount(context.wrapper, 1);

            context.textarea.value = "";
            showInlineTooltip(
                context.form,
                `${context.formType} added`
            );
        }
    }
    // Turn it off when finished!
    if (targetBtn) setLoading(targetBtn, false);
    if (context.form) setLoading(context.form.querySelector('button[type="submit"]'), false);

}