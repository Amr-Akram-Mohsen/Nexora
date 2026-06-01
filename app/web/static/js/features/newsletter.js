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

function handleNewsletterSubmit(e) {
    const subscribeForm = e.target.closest("[data-newsletter-form]");
    if (!subscribeForm) return false;
    const btn = e.submitter;
    e.preventDefault();
    handleSubscribing(subscribeForm, btn);
    return true;

}