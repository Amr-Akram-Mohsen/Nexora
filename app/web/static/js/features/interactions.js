async function submitUserInteraction(
    targetItem,
    interactionType,
    targetBtn = null,
    content = null,
    context = {}
) {

    const formButton = context.form?.querySelector('button[type="submit"]');

    if (targetBtn) setLoading(targetBtn, true);
    if (formButton) setLoading(formButton, true);

    try {
        const targetType = targetItem.dataset.type;
        const targetId = targetItem.dataset.id;
        const reactionType = targetBtn?.dataset.reaction;

        const fd = new FormData();
        fd.append("type", targetType);
        fd.append("id", targetId);
        fd.append("interaction_type", interactionType);

        if (interactionType === "react") {
            fd.append("reaction", reactionType);
            if (targetItem.dataset.commentId) fd.append("comment_id", targetItem.dataset.commentId);
        }

        if (interactionType === "comment") {
            fd.append("comment", content);
            if (context.formType === "reply" && targetItem.dataset.commentId) {
                fd.append("comment_id", targetItem.dataset.commentId);
            }
        }

        const res = await fetch("/handle-interaction", {
            method: "POST",
            body: fd
        });

        const result = await parseInteractionResponse(res);

        if (!res.ok || !result?.success) {
            showInlineTooltip(
                context.form || targetBtn || targetItem,
                result?.error || "Interaction failed. Please try again."
            );
            return result;
        }

        if (interactionType === 'react') {
            updateReactionUI(targetItem, reactionType, result.status);
        } else if (interactionType === 'save') {
            targetBtn.classList.toggle('active', result.status == 'saved');

            // Special behavior for Saved Items page: remove card if unsaved
            if (result.status === 'unsaved' && window.location.pathname.includes('/saved')) {
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
        } else if (interactionType === 'share') {
            showInlineTooltip(targetBtn || targetItem, "Share tracked");
        }
        else if (interactionType === "comment" && result?.success) {
            const list = context.formType === "reply"
                ? context.wrapper.querySelector('.comment__replies-list')
                : context.wrapper.querySelector(".comments__list");

            if (list && result.comment) {
                list.insertAdjacentHTML("afterbegin", result.comment);
            }

            if (context.formType === 'comment')
                incrementCommentCount(context.wrapper, 1);

            context.textarea.value = "";
            showInlineTooltip(
                context.form,
                `${context.formType} added`
            );
        }
        return result;
    } catch (error) {
        console.error("Interaction request failed", error);
        showInlineTooltip(
            context.form || targetBtn || targetItem,
            "Interaction failed. Please try again."
        );
        return { success: false, error: error.message };
    } finally {
        if (targetBtn) setLoading(targetBtn, false);
        if (formButton) setLoading(formButton, false);
    }
}

async function parseInteractionResponse(res) {
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        return res.json();
    }

    const text = await res.text();
    return {
        success: false,
        error: text ? "Server returned an unexpected response." : "Empty server response."
    };
}

function handleInteractionClick(e) {
    const interactionBtn = e.target.closest(".react-btn, .save-btn, .share-btn");
    if (!interactionBtn) return false;

    const interactionType = interactionBtn.classList.contains('react-btn')
        ? 'react'
        : interactionBtn.classList.contains('save-btn')
            ? 'save'
            : 'share';

    if (interactionType === 'share') {
        handleShareInteraction(interactionBtn);
        return true;
    }

    if (!ensureAuthenticated(e, interactionBtn, generalMsg + interactionType)) return false;

    const item = interactionBtn.closest("[data-id]");
    if (!item) return false;

    if (item.hasAttribute('data-comment-id')) {
        // const parentComment = e.target.closest('.comment');
        const commentAuthor = item.querySelector('.comment__author').textContent.trim();

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

async function handleShareInteraction(shareBtn) {
    const item = shareBtn.closest("[data-id]");
    if (!item) return;

    const shareData = {
        title: document.title,
        url: window.location.href
    };

    try {
        if (navigator.share) {
            await navigator.share(shareData);
            showInlineTooltip(shareBtn, "Shared");
        } else if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(shareData.url);
            showInlineTooltip(shareBtn, "Link copied");
        } else {
            showInlineTooltip(shareBtn, shareData.url);
        }

        if (isAuthenticated) {
            submitUserInteraction(item, "share", shareBtn);
        }
    } catch (error) {
        if (error?.name !== "AbortError") {
            console.error("Share failed", error);
            showInlineTooltip(shareBtn, "Could not share this item");
        }
    }
}
