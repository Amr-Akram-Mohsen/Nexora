function handleGlobalClicks(e) {
    const modeToggle = e.target.closest('.mode-toggle');
    if (modeToggle) {
        handleModeToggle();
        return;
    }

    const reviewsToggle = e.target.closest('i.toggle__reviews-menu');
    if (reviewsToggle) {
        handleReviewsToggle();
        return;
    }

    // ---------- Gallery open / close / arrow clicks ----------
    const galleryOverlay = document.querySelector("[data-gallery-overlay]");

    const openGalleryBtn = e.target.closest("[data-gallery-open]");
    if (openGalleryBtn) {
        initGallery(e);
        return;
    }

    const galleryClose = e.target.closest("[data-gallery-close]");
    if (galleryClose) {
        if (galleryOverlay) galleryOverlay.hidden = true;
        return;
    }

    const imageControl = e.target.closest(".item-gallery__nav");
    if (imageControl) {
        handleImageControls(imageControl);
        return;
    }

    const sliderControl = e.target.closest(`
        .hero-slider__arrow--prev:not(.disabled),
        .hero-slider__arrow--next:not(.disabled),
        .hero-slider__dot:not(.active)
    `);

    if (sliderControl) {
        handleHeroSliderControls(sliderControl);
        return;
    }

    const reviewsMenuItem = document.querySelector('.reviews__dropdown-item');
    const dropdownMenu = reviewsMenuItem?.querySelector('.reviews__dropdown-menu');
    if (reviewsMenuItem && !dropdownMenu?.classList.contains('is-hidden') && !reviewsMenuItem.contains(e.target)) {
        dropdownMenu.classList.remove('is-hidden');
        return;
    }
    const reviewClick = e.target.closest('a.reviews-link');
    if (reviewClick) {
        document.querySelector('a.reviews-link.active')?.classList.remove('active');
        reviewClick.classList.add('active');
        return;
    }
    const fullSpecsBtn = e.target.closest(".item-details-dialog__action");
    if (fullSpecsBtn) {
        // showFullSpecs(fullSpecsBtn);
        const overlay = document.querySelector(".item-details-dialog");
        // overlay.classList.add('is-open');
        overlay.classList.toggle('is-open');
        return;
    }

    const fullSpecsOverlay = document.querySelector(".item-details-dialog");
    const closeFullSpecs = e.target.closest(".item-details-dialog__close") || e.target.closest(".item-details-dialog__overlay");
    if (closeFullSpecs || e.target == fullSpecsOverlay) {
        closeOverlay();
        return;
    }

    const interactionBtn = e.target.closest(".react-btn, .save-btn");
    if (interactionBtn) {
        interactionType = interactionBtn.classList.contains('react-btn') ? 'react' : 'save';
        if (!ensureAuthenticated(e, interactionBtn, generalMsg + interactionType)) return;

        const item = interactionBtn.closest("[data-id]");

        if (item.hasAttribute('data-comment-id')) {
            // const parentComment = e.target.closest('.comment');
            const commentAuthor = item.querySelector('.comment__author').textContent;

            if (commentAuthor === userEmail) {
                showInlineTooltip(interactionBtn, "You can't react on your own comment");
                return;
            }
        }


        submitUserInteraction(
            item,
            interactionType,
            interactionBtn || null
        );
        return;
    }

    const itemBuyBtn = e.target.closest(".item-buy-link");
    if (itemBuyBtn) {
        e.preventDefault();
        handleAffiliateClick(itemBuyBtn);
        return;
    }

    // this is in handleGlobalClicks function which is triggered by click eventlistener
    const commentsToggleBtn = e.target.closest(".comments-toggle-btn");
    if (commentsToggleBtn) {
        showComments(commentsToggleBtn);
        return;
    }

    const filterChip = e.target.closest(".filter-chip");
    if (filterChip) {
        filterContent(filterChip);
        return;
    }

    const messagesCloseBtn = e.target.closest('.alert-close');
    if (messagesCloseBtn) {
        closeFlashMsg(messagesCloseBtn);
        return;
    }

    const mainSectionLink = e.target.closest('.section-link');
    if (mainSectionLink) {
        toggleActive(mainSectionLink)
    }

    const searchToggleBtn = e.target.closest('.search-toggle');
    if (searchToggleBtn) {
        const siteHeader = searchToggleBtn.closest('.site-header');
        siteHeader.querySelector('.header-search')
            .classList.toggle('active');
    }

    const user = e.target.closest(".nav-user");
    if (user) {
        document.querySelectorAll(".nav-user")
            .forEach(el => {
                if (el !== user) el.classList.remove("active");
            });

        if (user) {
            user.classList.toggle("active");
        }

    }
}


function handleGlobalSubmits(e) {
    const form = e.target.closest(".comment-form");
    if (form) {
        e.preventDefault();
        const formType = form.classList.contains('comment__form') ? 'comment' : 'reply';

        if (!ensureAuthenticated(e, form.querySelector("button"), generalMsg + formType)) return;
        handleCommentPosting(form, formType);
        return;
    }

    const subscribeForm = e.target.closest("[data-newsletter-form]");
    if (subscribeForm) {
        const btn = e.submitter;
        e.preventDefault();
        handleSubscribing(subscribeForm, btn);
        return;
    }

    const contactForm = e.target.closest(".contact-form");
    if (contactForm) {
        e.preventDefault();
        handleUserMessages(contactForm);
        return;
    }

    const searchForm = e.target.closest(".header-search__form");
    if (searchForm) {
        e.preventDefault();
        handleSearch(searchForm);
        return;
    }
}

// Header scroll effect
function initHeaderScroll() {
    const header = document.querySelector('.site-header');
    if (!header) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('site-header--scrolled');
        } else {
            header.classList.remove('site-header--scrolled');
        }
    });
}

// Initialize everything on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initHeaderScroll();
});
