async function handleSearch(form) {
    const formData = new FormData(form);

    const query = String(form.getAttribute('query'));

    if (query.trim() === '') return;

    const countrySelect = document.querySelector('.country-toggle');
    const country = countrySelect ? countrySelect.value : '';
    
    formData.set('country', country);

    const res = await fetch("/search", {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" } // lets Flask know it's AJAX
    });

    const data = await res.json();

    if (data.success) {
      // Replace main content only
      const mainContent = document.querySelector('#main-content');
      if (mainContent) {
          mainContent.innerHTML = data.html;

        }      
      
      // Keep country selection persistent
      if (countrySelect) countrySelect.value = country;
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
    const fd = new FormData(form);
    if (btn && btn.name) {
        fd.append(btn.name, btn.value);
    }

    const response = await fetch(form.action, {
        method: "POST",
        body: fd,
        headers: { "X-Requested-With": "XMLHttpRequest" }
    });

    const data = await response.json();
    
    showInlineTooltip(
        btn,
        data.success ? data.message : data.error,
        2500
    );

    if (data.success) {
        document.querySelector("[data-newsletter]").innerHTML = data.html;
    }
}

async function handleUserMessages(form) {
    const formData = new FormData(form);

    const res = await fetch("/contact", {
        method: "POST",
        body: formData
    });

    const data = await res.json();
    if (data.success) form.reset();
    showInlineTooltip(
      form,
      data.success ? data.message : data.error
    );
}
