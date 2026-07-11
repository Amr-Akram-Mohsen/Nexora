function incrementCommentCount(wrapper, delta = 1) {
    const target = wrapper?.closest?.("[data-id]") || wrapper;
    const countEl = target?.querySelector?.(`.interaction-panel .comments-toggle-content`);
    if (!countEl) return;

    const current = parseInt(countEl.textContent.replace(/\D/g, ""), 10) || 0;
    const next = Math.max(0, current + delta);
    countEl.textContent = `${next} ${next === 1 ? "comment" : "comments"}`;
}

async function showComments(btn) {
    let wrapper = btn.closest("[data-id]");

    const isReply = wrapper.hasAttribute('data-comment-id');

    let list = null;

    const params = new URLSearchParams();

    params.append("type", wrapper.dataset.type);
    params.append("id", wrapper.dataset.id);

    // const textMsg = isReply ? 'replies' : 'comments';

    let opening = false;


    if (isReply) {
        const comment = wrapper;
        wrapper = comment.querySelector(".comment__replies");
        wrapper.classList.toggle("comment__replies--open");
        opening = wrapper.classList.contains("comment__replies--open");
        list = wrapper.querySelector(".comment__replies-list");
        list?.classList.toggle('flex', opening);
        params.append("parent_id", comment.dataset.commentId);
    }
    else {
        // const parent = wrapper.closest(".detail-page__extra")
        // wrapper = parent.querySelector(".comments");
        wrapper = wrapper.querySelector(".comments");
        wrapper.classList.toggle("comments--collapsed");
        opening = !wrapper.classList.contains("comments--collapsed");
        list = wrapper.querySelector(".comments__list");
    }
    const icon = btn.querySelector(".comments-toggle-icon");
    if (icon) {
        icon.classList.toggle("fa-chevron-down", !opening);
        icon.classList.toggle("fa-chevron-up", opening);
    }
    // Load ONLY the first time it's opened
    // if (!opening) return;
    if (wrapper.dataset.loaded === "true") return;

    try {
        const res = await fetch(`/get-comments?${params.toString()}`);

        if (!res.ok) {
            showInlineTooltip(btn, "Could not load comments");
            return null;
        }

        const result = await res.text();
        list.innerHTML = result;

        if (typeof initAllReactions === "function") initAllReactions();

        wrapper.dataset.loaded = "true";
    } catch (error) {
        console.error("Could not load comments", error);
        showInlineTooltip(btn, "Could not load comments");
    }
}

async function handleCommentPosting(form, formType) {

    if (formType === 'reply') {
        const parentComment = form.closest('.comment');
        const commentAuthor = parentComment.querySelector('.comment__author').textContent;

        if (commentAuthor === userEmail) {
            showInlineTooltip(form, "You can't reply on your own comment");
            return;
        }
    }
    const wrapper = form.classList.contains("comment__reply-form")
        ? form.closest(".comment__replies")
        : form.closest(".comments");

    const textarea = form.querySelector("textarea");
    const content = textarea.value.trim();
    if (!content) {
        showInlineTooltip(form, "You can't post an empty comment");
        return;
    }

    const product = wrapper.closest("[data-id]");

    submitUserInteraction(product,
        'comment',
        null,
        content,
        { wrapper, textarea, form, formType }
    );
}

function handleCommentsClick(e) {
    const commentsToggleBtn = e.target.closest(".comments-toggle-btn");
    if (commentsToggleBtn) {
        showComments(commentsToggleBtn);
        return true;
    }
    return false;
}

function handleCommentSubmit(e) {
    const form = e.target.closest(".comment-form");
    if (!form) return false;
    e.preventDefault();
    const formType = form.classList.contains('comment__form') ? 'comment' : 'reply';

    if (!ensureAuthenticated(e, form.querySelector("button"), generalMsg + formType)) return false;
    handleCommentPosting(form, formType);
    return true;
}
