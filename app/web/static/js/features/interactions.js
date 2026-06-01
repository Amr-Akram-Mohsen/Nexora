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
            targetBtn.classList.toggle('active', result.status == 'saved');

            // Special behavior for Saved Items page: remove card if unsaved
            if (result.status === 'removed' && window.location.pathname.includes('/saved')) {
                const card = targetItem.closest('.card, .article-card, .item-card');
                if (card) {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.95)';
                    card.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
                    setTimeout(() => {
                        const grid = card.closest('.grid');
                        const section = card.closest('.saved-collection');
                        card.remove();
                        if (grid && !grid.children.length && section) section.remove();
                        if (!document.querySelectorAll('.saved-collection').length) window.location.reload();
                    }, 400);
                }
            }
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

function handleInteractionClick(e) {
    const interactionBtn = e.target.closest(".react-btn, .save-btn");
    if (!interactionBtn) return false;

    interactionType = interactionBtn.classList.contains('react-btn') ? 'react' : 'save';
    if (!ensureAuthenticated(e, interactionBtn, generalMsg + interactionType)) return false;

    const item = interactionBtn.closest("[data-id]");

    if (item.hasAttribute('data-comment-id')) {
        // const parentComment = e.target.closest('.comment');
        const commentAuthor = item.querySelector('.comment__author').textContent;

        if (commentAuthor === userEmail) {
            showInlineTooltip(interactionBtn, "You can't react on your own comment");
            return false;
        }
    }


    submitUserInteraction(
        item,
        interactionType,
        interactionBtn || null
    );
    return true;
}