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

    const imageControl = e.target.closest(".item-gallery__nav, .item-gallery__thumb");
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
        const searchPanel = siteHeader.querySelector('.header-search');
        const isActive = searchPanel.classList.toggle('active');
        searchToggleBtn.setAttribute('aria-expanded', String(isActive));
        if (isActive) {
            searchPanel.querySelector('.header-search__input')?.focus();
        }
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

    const googleAuth = e.target.closest('.google-auth-btn');
    if (googleAuth) {
        const url = googleAuth.dataset.url;
        if (url) window.location.href = url;
    }

    const mobileMenuToggle = e.target.closest('.mobile-menu-toggle');
    if (mobileMenuToggle) {
        const mobileNav = document.querySelector('.mobile-nav');
        mobileNav.classList.toggle('active');
        mobileMenuToggle.querySelector('i').classList.toggle('fa-bars');
        mobileMenuToggle.querySelector('i').classList.toggle('fa-times');
    }

    // Gallery Overlay Navigation
    const galleryPrev = e.target.closest('[data-gallery-prev]');
    if (galleryPrev) {
        navigateGallery(-1);
    }
    const galleryNext = e.target.closest('[data-gallery-next]');
    if (galleryNext) {
        navigateGallery(1);
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

}

function handleGlobalChanges(e) {
    const sortSelect = e.target.closest('.sort-select');
    if (sortSelect) {
        window.location.href = sortSelect.value;
        return;
    }
}

// Header scroll effect & Back to Top
function initHeaderScroll() {
    const header = document.querySelector('.site-header');
    const backToTopBtn = document.getElementById('back-to-top');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            if (header) header.classList.add('site-header--scrolled');
        } else {
            if (header) header.classList.remove('site-header--scrolled');
        }
        
        if (backToTopBtn) {
            if (window.scrollY > 300) {
                backToTopBtn.classList.remove('is-hidden');
            } else {
                backToTopBtn.classList.add('is-hidden');
            }
        }
    });

    if (backToTopBtn) {
        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
}

// Initialize everything on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initHeaderScroll();

    // Event Delegation listeners
    document.addEventListener('click', handleGlobalClicks);
    document.addEventListener('submit', handleGlobalSubmits);
    document.addEventListener('change', handleGlobalChanges);

    // Initial Search Highlighting
    if (window.SEARCH_QUERY) {
        const cards = document.querySelectorAll('.card__title, .card__excerpt, .item-card__name, .item-card__description');
        const escapedQuery = String(window.SEARCH_QUERY).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        cards.forEach(card => {
            card.innerHTML = card.innerHTML.replace(regex, '<mark class="search-highlight">$1</mark>');
        });
    }
});
