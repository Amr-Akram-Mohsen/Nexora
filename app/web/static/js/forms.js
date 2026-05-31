async function handleSearch(form) {
    const formData = new FormData(form);
    const query = formData.get('query') || "";

    if (!query.trim()) return;

    const action = form.getAttribute("action") || "/search";
    const url = `${action}?query=${encodeURIComponent(query)}`;

    const res = await fetch(url, {
        method: "GET",
        headers: { "X-Requested-With": "XMLHttpRequest" } // lets Flask know it's AJAX
    });

    const data = await res.json();

    if (data.success) {
        // Replace main content only
        const mainContent = document.querySelector('#main-content');
        if (mainContent) {
            mainContent.innerHTML = data.html;
            window.history.pushState({}, "", url);
            document.querySelector(".header-search")?.classList.remove("active");
            document.querySelector(".search-toggle")?.setAttribute("aria-expanded", "false");
        }
    } else if (data.error) {
        showInlineTooltip(form, data.error);
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

    const item = wrapper.closest("[data-id]");

    submitUserInteraction(item,
        'comment',
        null,
        content,
        { wrapper, textarea, form, formType }
    );
}


async function handleSubscribing(form, btn) {
    if (!btn) btn = form.querySelector("[data-newsletter-submit], button[type='submit']");
    setLoading(btn, true);
    const fd = new FormData(form);

    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: fd,
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        const data = await response.json();
        const message = data.success ? data.message : data.error;

        showInlineTooltip(btn || form, message || "Newsletter request complete.", 2500);

        if (data.success && data.html) {
            const currentNewsletter = form.closest("[data-newsletter]");
            if (currentNewsletter) {
                currentNewsletter.innerHTML = data.html;
            }

            const placement = form.dataset.newsletterPlacement;
            document.querySelectorAll("[data-newsletter]").forEach((newsletter) => {
                if (newsletter === currentNewsletter) return;
                if (placement && newsletter.dataset.newsletterPlacement !== placement) return;
                newsletter.innerHTML = data.html;
            });
        }
    } catch (error) {
        showInlineTooltip(btn || form, "We could not update your newsletter preference. Please try again.", 3000);
    } finally {
        setLoading(btn, false);
    }
}

async function handleUserMessages(form) {
    const formData = new FormData(form);
    const btn = form.querySelector('button[type="submit"]');
    setLoading(btn, true);

    const res = await fetch("/contact", {
        method: "POST",
        body: formData
    });

    setLoading(btn, false);

    const data = await res.json();
    if (data.success) form.reset();
    showInlineTooltip(
        form,
        data.success ? data.message : data.error
    );
}
