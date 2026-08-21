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

        if (interactionType === "save" && context.collection_name) {
            fd.append("collection_name", context.collection_name.trim().toLowerCase());
        }

        if (interactionType === "comment") {
            fd.append("comment", content);
            if (context.formType === "reply" && targetItem.dataset.commentId) {
                fd.append("comment_id", targetItem.dataset.commentId);
            }
        }

        const endpoint = window.APP?.urls?.interaction || "/handle-interaction";
        const res = await fetch(endpoint, {
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
                const card = targetItem.closest('[data-saveable-card], .card');
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

function promptCollectionName(targetBtn) {
    return new Promise((resolve) => {
        const existing = document.getElementById('collection-popover');
        if (existing) existing.remove();

        const template = document.getElementById('collection-popover-template');
        let popover;
        if (template) {
            const clone = template.content.cloneNode(true);
            popover = clone.querySelector('#collection-popover') || clone.firstElementChild;
        } else {
            popover = document.createElement('div');
            popover.id = 'collection-popover';
            popover.className = 'collection-popover';
            popover.innerHTML = `
                <div class="collection-popover__content flex flex-col">
                    <label id="collection-popover-title" class="collection-popover__label" for="collection-input">Save to Collection</label>
                    <input type="text" id="collection-input" class="collection-popover__input" placeholder="general" value="general">
                    <div class="collection-popover__actions flex justify-end">
                        <button type="button" id="collection-cancel" class="btn btn--outline btn--sm">Cancel</button>
                        <button type="button" id="collection-confirm" class="btn btn--default btn--sm">Save</button>
                    </div>
                </div>
            `;
        }

        document.body.appendChild(popover);

        const rect = targetBtn.getBoundingClientRect();
        let top = rect.bottom + window.scrollY + 8;
        let left = rect.left + window.scrollX - (240 / 2) + (rect.width / 2);

        if (left < 10) left = 10;
        if (left + 250 > window.innerWidth) left = window.innerWidth - 250;

        // Prevent going off bottom of screen
        if (top + 150 > window.scrollY + window.innerHeight) {
            top = rect.top + window.scrollY - 150 - 8;
        }

        popover.style.top = `${top}px`;
        popover.style.left = `${left}px`;

        const input = popover.querySelector('#collection-input');
        if (input) {
            input.focus();
            input.select();
        }

        let resolved = false;

        const cleanup = (val) => {
            if (!resolved) {
                resolved = true;
                popover.remove();
                resolve(val);
            }
        };

        popover.querySelector('#collection-cancel')?.addEventListener('click', () => cleanup(null));
        popover.querySelector('#collection-confirm')?.addEventListener('click', () => cleanup(input ? input.value : null));

        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                cleanup(input.value);
            }
            if (e.key === 'Escape') cleanup(null);
        });

        setTimeout(() => {
            const onClickOutside = (e) => {
                if (!popover.contains(e.target) && e.target !== targetBtn) {
                    cleanup(null);
                }
            };
            document.addEventListener('click', onClickOutside);

            const originalCleanup = cleanup;
            cleanup = (val) => {
                document.removeEventListener('click', onClickOutside);
                originalCleanup(val);
            };
        }, 10);
    });
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

    const product = interactionBtn.closest("[data-id]");
    if (!product) return false;

    if (product.hasAttribute('data-comment-id')) {
        const commentAuthor = product.querySelector('.comment__author').textContent.trim();

        if (commentAuthor === userEmail) {
            showInlineTooltip(interactionBtn, "You can't react on your own comment");
            return false;
        }
    }

    if (interactionType === 'save') {
        const isUnsaving = interactionBtn.classList.contains('active');
        if (!isUnsaving) {
            const predefinedCollection = interactionBtn.dataset.collection;
            if (predefinedCollection) {
                submitUserInteraction(product, interactionType, interactionBtn, null, { collection_name: predefinedCollection });
                return true;
            }

            promptCollectionName(interactionBtn).then(collection => {
                if (collection !== null) {
                    submitUserInteraction(product, interactionType, interactionBtn, null, { collection_name: collection });
                }
            });
            return true;
        }
    }

    submitUserInteraction(
        product,
        interactionType,
        interactionBtn || null
    );
    return true;
}

async function handleShareInteraction(shareBtn) {
    const product = shareBtn.closest("[data-id]");
    if (!product) return;

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
            submitUserInteraction(product, "share", shareBtn);
        }
    } catch (error) {
        if (error?.name !== "AbortError") {
            console.error("Share failed", error);
            showInlineTooltip(shareBtn, "Could not share this product");
        }
    }
}
