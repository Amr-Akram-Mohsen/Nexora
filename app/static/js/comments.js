function incrementCommentCount(wrapper, delta = 1) {
    const countEl = document.querySelector(`.comments-toggle-content`);
    if (!countEl) return;

    const current = parseInt(countEl.textContent.replace(/\D/g, ""), 10) || 0;
    countEl.textContent = `(${current + delta})`;
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
        wrapper = wrapper.querySelector(".comment__replies");
        opening = wrapper.classList.contains("comment__replies--open")
        wrapper.classList.toggle("comment__replies--open");
        list = wrapper.querySelector(".comment__replies-list");
        list.classList.toggle('flex');
        params.append("parent_id", wrapper.dataset.commentId);
    }
    else {
        const parent = wrapper.closest(".detail-page__extra")
        wrapper = parent.querySelector(".comments");
        opening = !wrapper.classList.contains("comments--collapsed")
        wrapper.classList.toggle("comments--collapsed");
        list = wrapper.querySelector(".comments__list");
    }
    const icon = btn.querySelector(".comments-toggle-icon");
    icon.classList.toggle("fa-chevron-down", !opening);
    icon.classList.toggle("fa-chevron-up", opening);
    // Load ONLY the first time it's opened
    // if (!opening) return;
    if (wrapper.dataset.loaded === "true") return;

    const res = await fetch(
        `/get-comments?${params.toString()}`
    );

    if (!res.ok) return null;

    const result = await res.text();


    list.innerHTML = result;

    initAllReactions();

    wrapper.dataset.loaded = "true";
}

