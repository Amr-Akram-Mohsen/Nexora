async function handleUserMessages(form) {
    const formData = new FormData(form);
    const btn = form.querySelector('button[type="submit"]');
    setLoading(btn, true);

    const endpoint = form.action || window.APP?.urls?.contact || "/contact";
    const res = await fetch(endpoint, {
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

function handleContactSubmit(e) {
    const contactForm = e.target.closest(".contact-form");
    if (!contactForm) return false;
    e.preventDefault();
    handleUserMessages(contactForm);
    return true;
}