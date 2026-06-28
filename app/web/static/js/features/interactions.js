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

function promptCollectionName(targetBtn) {
    return new Promise((resolve) => {
        const existing = document.getElementById('collection-popover');
        if (existing) existing.remove();

        const popover = document.createElement('div');
        popover.id = 'collection-popover';
        
        const isDark = document.body.classList.contains('dark') || document.documentElement.classList.contains('dark');
        const bgColor = isDark ? '#1e293b' : '#ffffff';
        const borderColor = isDark ? '#334155' : '#e2e8f0';
        const textColor = isDark ? '#f8fafc' : '#0f172a';
        const inputBg = isDark ? '#0f172a' : '#f8fafc';
        
        popover.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <label style="font-size: 0.85rem; font-weight: 600; color: ${textColor};">Save to Collection</label>
                <input type="text" id="collection-input" placeholder="general" value="general" 
                    style="padding: 8px; border: 1px solid ${borderColor}; border-radius: 6px; font-size: 0.85rem; outline: none; background: ${inputBg}; color: ${textColor}; transition: border-color 0.2s;">
                <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px;">
                    <button type="button" id="collection-cancel" style="padding: 6px 12px; font-size: 0.75rem; font-weight: 500; border: 1px solid ${borderColor}; background: transparent; border-radius: 6px; cursor: pointer; color: ${textColor};">Cancel</button>
                    <button type="button" id="collection-confirm" style="padding: 6px 12px; font-size: 0.75rem; font-weight: 500; border: none; background: var(--accent-primary, #2563eb); color: #fff; border-radius: 6px; cursor: pointer;">Save</button>
                </div>
            </div>
        `;

        Object.assign(popover.style, {
            position: 'absolute',
            zIndex: '9999',
            background: bgColor,
            border: `1px solid ${borderColor}`,
            borderRadius: '12px',
            padding: '16px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
            width: '240px',
            animation: 'fadeIn 0.2s ease-out'
        });

        // Add a small animation style if not exists
        if (!document.getElementById('popover-style')) {
            const style = document.createElement('style');
            style.id = 'popover-style';
            style.textContent = '@keyframes fadeIn { from { opacity: 0; transform: translateY(-4px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } } #collection-input:focus { border-color: var(--accent-primary, #2563eb) !important; }';
            document.head.appendChild(style);
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
        input.focus();
        input.select();

        let resolved = false;
        
        let cleanup = (val) => {
            if (!resolved) {
                resolved = true;
                popover.remove();
                resolve(val);
            }
        };

        popover.querySelector('#collection-cancel').addEventListener('click', () => cleanup(null));
        popover.querySelector('#collection-confirm').addEventListener('click', () => cleanup(input.value));
        
        input.addEventListener('keydown', (e) => {
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
            }
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

    const item = interactionBtn.closest("[data-id]");
    if (!item) return false;

    if (item.hasAttribute('data-comment-id')) {
        const commentAuthor = item.querySelector('.comment__author').textContent.trim();

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
                submitUserInteraction(item, interactionType, interactionBtn, null, { collection_name: predefinedCollection });
                return true;
            }

            promptCollectionName(interactionBtn).then(collection => {
                if (collection !== null) {
                    submitUserInteraction(item, interactionType, interactionBtn, null, { collection_name: collection });
                }
            });
            return true;
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
