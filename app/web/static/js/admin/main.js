// affiliates.js  

async function handleAffiliateClick(li) {
    if (li.classList.contains("is-loading")) return;

    li.classList.add("is-loading");

    const linkId = li.dataset.linkId;

    try {
        const res = await fetch(`/item-click/${linkId}`, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        if (!res.ok) throw new Error("Tracking failed");

        const data = await res.json();

        if (data.redirect_url) {
            window.open(data.redirect_url, "_blank", "noopener,noreferrer");
        }
    } catch (err) {
        console.error("Affiliate redirect failed:", err);
        alert("Unable to open store right now. Please try again.");
    } finally {
        li.classList.remove("is-loading");
    }
}
  
 
// auth.js  
const { isAuthenticated, userEmail } = window.APP;


// General Message
function showInlineTooltip(targetEl, message, duration = 2000) {
    const msg = document.getElementById("inline-tooltip");
    if (!msg || !targetEl) return;
    msg.textContent = message;
    msg.classList.remove("is-hidden");
    msg.style.display = "block";

    const rect = targetEl.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

    const msgHeight = msg.offsetHeight;

    msg.style.top = `${rect.top + scrollTop - msgHeight - 8}px`; // tooltip above element
    msg.style.left = `${rect.left + scrollLeft}px`;
    
    // msg.style.top = `${rect.top + scrollTop - rect.height - 8}px`;
    // msg.style.left = `${rect.left + scrollLeft}px`;

    clearTimeout(msg._timeout);
    msg._timeout = setTimeout(() => {
        msg.classList.add("is-hidden");
        msg.style.display = "none";
    }, duration);
}

// General Checking Authentication Function Used For Interactions Allownce
function ensureAuthenticated(event, btn, message){
        if (!isAuthenticated) {
            event.preventDefault();
            showInlineTooltip(btn, message);
            return false;
        }
        return true;
}
  
 
// comments.js  
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

  
 
// compare.js  
// app/static/js/compare.js

class CompareManager {
    constructor() {
        this.storageKey = 'nexora_compare_ids';
        this.maxItems = 4;
        this.compareIds = this.loadIds();
        this.init();
    }

    loadIds() {
        const stored = localStorage.getItem(this.storageKey);
        return stored ? JSON.parse(stored) : [];
    }

    saveIds() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.compareIds));
    }

    toggleItem(id) {
        id = parseInt(id);
        const index = this.compareIds.indexOf(id);
        if (index > -1) {
            this.compareIds.splice(index, 1);
            this.saveIds();
            this.updateUI();
            return 'removed';
        } else {
            if (this.compareIds.length >= this.maxItems) {
                alert(`You can compare up to ${this.maxItems} items at once.`);
                return 'full';
            }
            this.compareIds.push(id);
            this.saveIds();
            this.updateUI();
            return 'added';
        }
    }

    init() {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.compare-toggle-btn');
            if (btn) {
                e.preventDefault();
                e.stopPropagation();
                const id = btn.dataset.id;
                this.toggleItem(id);
            }
        });

        // Initial UI update
        this.updateUI();
    }

    updateUI() {
        // Update all buttons status
        document.querySelectorAll('.compare-toggle-btn').forEach(btn => {
            const id = parseInt(btn.dataset.id);
            btn.classList.toggle('active', this.compareIds.includes(id));
        });

        this.renderCompareBar();
    }

    renderCompareBar() {
        let bar = document.getElementById('compare-floating-bar');
        
        if (this.compareIds.length === 0) {
            if (bar) bar.remove();
            return;
        }

        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'compare-floating-bar';
            bar.className = 'compare-bar flex items-center justify-between';
            document.body.appendChild(bar);
        }

        const compareUrl = `/compare?ids=${this.compareIds.join(',')}`;
        
        bar.innerHTML = `
            <div class="compare-bar__info flex items-center">
                <div class="compare-bar__count">${this.compareIds.length}</div>
                <span class="compare-bar__text">Items selected for comparison</span>
            </div>
            <div class="compare-bar__actions flex items-center">
                <button class="compare-bar__clear btn btn--link">Clear All</button>
                <a href="${compareUrl}" class="btn btn--primary">Compare Now</a>
            </div>
        `;

        bar.querySelector('.compare-bar__clear').onclick = () => {
            this.compareIds = [];
            this.saveIds();
            this.updateUI();
        };
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.compareManager = new CompareManager();
});
  
 
// core.js  
const originalFetch = window.fetch;
window.fetch = async function (...args) {
    let [resource, config] = args;
    if (config && config.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method.toUpperCase())) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (csrfToken) {
            config.headers = {
                ...(config.headers || {}),
                'X-CSRFToken': csrfToken
            };
        }
    }
    return originalFetch(resource, config);
};

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    initUserInteractions();
    document.addEventListener("click", handleGlobalClicks);
    document.addEventListener("submit", handleGlobalSubmits);
});

window.addEventListener("pageshow", initUserInteractions);

document.addEventListener("change", handleCountryToggle);


function initApp() {
    initHeroSlider();
    initTheme();

    // applyMode();
    handleFlashMessages();
}

// Run on page load and when coming back via back/forward buttons
function initUserInteractions() {
    if (isAuthenticated) {
        initAllReactions();
        initAllSaves();
    }
}

const generalMsg = 'please sign in to ';

function filterContent(chip) {
    chip.classList.toggle("active");

    const params = new URLSearchParams(window.location.search);
    const key = chip.dataset.filter;
    const value = chip.dataset.slug;

    const values = params.getAll(key);

    if (values.includes(value)) {
        params.delete(key);
        values.filter(v => v !== value).forEach(v => params.append(key, v));
    } else {
        params.append(key, value);
    }

    window.location.search = params.toString();
}

// let newsletterHandled = false;

function handleFlashMessages() {
    // ------------------------------
    // Global messages (top-right)
    // ------------------------------
    const globalMessages = document.querySelectorAll('.flash-messages .alert');
    globalMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(100%)';
            setTimeout(() => msg.remove(), 500);
        }, 2500);
    });
}

// ------------------------------
// Manual close for global messages
// ------------------------------
function closeFlashMsg(btn) {
    const alert = btn.parentElement;
    alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(100%)';
    setTimeout(() => alert.remove(), 300);
}


async function handleCountryToggle(e) {
    if (!e.target.classList.contains("country-toggle")) return;

    const country = e.target.value || "";

    await fetch("/set-country", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ country })
    });

    // Optional: reload page to apply country filtering
    window.location.reload();

}

function setLoading(button, isLoading) {
    if (!button) return;
    if (isLoading) {
        button.classList.add('is-loading');
    } else {
        button.classList.remove('is-loading');
    }
}
  
 
// forms.js  
async function handleSearch(form) {
    const formData = new FormData(form);
    const query = formData.get('query') || "";

    if (!query.trim()) return;

    const res = await fetch(`/search?query=${encodeURIComponent(query)}`, {
        method: "GET",
        headers: { "X-Requested-With": "XMLHttpRequest" } // lets Flask know it's AJAX
    });

    const data = await res.json();

    if (data.success) {
        // Replace main content only
        const mainContent = document.querySelector('#main-content');
        if (mainContent) {
            mainContent.innerHTML = data.html;

        }
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
    setLoading(btn, true);
    const fd = new FormData(form);

    const response = await fetch(form.action, {
        method: "POST",
        body: fd,
        headers: { "X-Requested-With": "XMLHttpRequest" }
    });

    const data = await response.json();

    setLoading(btn, false);
    showInlineTooltip(
        btn,
        data.success ? data.message : data.error,
        2500
    );

    if (data.success && data.html) {
        document.querySelector("[data-newsletter]").innerHTML = data.html;
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
  
 
// interactions.js  
function updateReactionsCount(wrapper, delta = 1) {
    const countEl = wrapper.querySelector(`.reaction-count`);
    if (!countEl) return;

    const current = parseInt(countEl.textContent.replace(/\D/g, ""), 10) || 0;
    countEl.textContent = `(${current + delta})`;
}


function updateReactionUI(targetItem, reactionType, status) {
    const targetBtn =
        targetItem.querySelector(`
        .react-btn[data-reaction="${reactionType}"]`
        );

    const activeBtn =
        targetItem.querySelector(`
        .react-btn.active`
        );

    // if (status === 'added' || status === 'changed') {
    //     targetBtn.classList.replace('btn--outline', 'btn--default');
    // }

    targetBtn.classList.toggle('active', status === 'added' || status === 'changed');
    // targetBtn.classList.toggle('active', status !== 'removed');    

    if (status === 'changed' && activeBtn) {
        activeBtn.classList.remove('active');
    }

    // if (status === 'changed') {
    //     activeBtn.classList.replace('btn--default', 'btn--outline');
    // }

    if (targetItem.hasAttribute('data-comment-id')) {
        updateReactionsCount(targetBtn, status == 'added' || status == 'changed' ? 1 : -1);
        if (activeBtn)
            updateReactionsCount(activeBtn, -1);
    }
}

async function initAllReactions() {
    const buttons = Array.from(document.querySelectorAll(".react-btn"));
    const targets = [];

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        if (item.hasAttribute('data-comment-id')) {
            targets.push({ 'type': 'comment', 'id': item.dataset.commentId });

        }
        targets.push({ ...item.dataset });
    });

    if (targets.size === 0) return;

    // Prepare query parameters
    const params = new URLSearchParams();
    for (const t of targets) {
        params.append("type", t.type);
        params.append("id", t.id);
    }

    const res = await fetch(`/check-react-batch?${params.toString()}`);

    if (!res.ok) return;

    const data = await res.json(); // expect: { "article:1": "like", "article:2": "dislike", ... }

    // Update UI
    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        let key = null;
        if (item.hasAttribute('data-comment-id')) {
            key = `comment:${item.dataset.commentId}`;
        } else {
            key = `${item.dataset.type}:${item.dataset.id}`;
        }
        btn.classList.toggle('active', btn.dataset.reaction === data[key]);
    });
}

async function initAllSaves() {
    const buttons = Array.from(document.querySelectorAll(".save-btn"));
    const targets = [];

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        targets.push({ ...item.dataset });
    });
    if (targets.size === 0) return;

    const params = new URLSearchParams();
    for (const t of targets) {
        params.append("type", t.type);
        params.append("id", t.id);
    }

    const res = await fetch(`/check-save-batch?${params.toString()}`);
    if (!res.ok) return;

    const data = await res.json(); // expect: { "article:1": true, "article:2": false }

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        const key = `${item.dataset.type}:${item.dataset.id}`;

        btn.classList.toggle('active', key in data);

    });
}

async function submitUserInteraction(
    targetItem,
    interactionType,
    targetBtn = null,
    content = null,
    context = {}
) {

    // Turn the button the user clicked into a spinner!
    if (targetBtn) setLoading(targetBtn, true);
    if (context.form) setLoading(context.form.querySelector('button[type="submit"]'), true);

    const targetType = targetItem.dataset.type;
    const targetId = targetItem.dataset.id;
    // const targetId = targetItem.dataset.commentId;

    const reactionType = targetBtn?.dataset.reaction;

    const fd = new FormData();

    fd.append("type", targetType);
    fd.append("id", targetId);
    fd.append("interaction_type", interactionType);


    if (interactionType === "react") {
        fd.append("reaction", reactionType);
        fd.append("comment_id", targetItem.dataset.commentId);
    }

    if (interactionType === "comment") {
        fd.append("comment", content);
        if (context.formType === "reply") fd.append("comment_id", targetItem.dataset.commentId);
    }

    const res = await fetch("/handle-interaction", {
        method: "POST",
        body: fd
    });

    const result = await res.json();

    if (!res.ok) {
        showInlineTooltip(
            context.form,
            res.error
        );
    } else {
        if (interactionType === 'react') {
            updateReactionUI(targetItem, reactionType, result.status);
        } else if (interactionType === 'save') {
            targetBtn.classList.toggle('active', result.status == 'saved');
            
            // Special behavior for Saved Items page: remove card if unsaved
            if (result.status === 'removed' && window.location.pathname.includes('/saved')) {
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
        }
        else if (interactionType === "comment" && result?.success) {
            const list = context.formType === "reply"
                ? context.wrapper.querySelector('.comment__replies-list')
                : context.wrapper.querySelector(".comments__list");

            list.insertAdjacentHTML("afterbegin", result.comment);

            if (context.formType === 'comment')
                incrementCommentCount(context.wrapper, 1);

            context.textarea.value = "";
            showInlineTooltip(
                context.form,
                `${context.formType} added`
            );
        }
    }
    // Turn it off when finished!
    if (targetBtn) setLoading(targetBtn, false);
    if (context.form) setLoading(context.form.querySelector('button[type="submit"]'), false);

}  
 
// main.js  
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

    const searchForm = e.target.closest(".header-search__form");
    if (searchForm) {
        e.preventDefault();
        handleSearch(searchForm);
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
        const regex = new RegExp(`(${window.SEARCH_QUERY})`, 'gi');
        cards.forEach(card => {
            card.innerHTML = card.innerHTML.replace(regex, '<mark class="search-highlight">$1</mark>');
        });
    }
});
  
 
// tracking.js  
function trackImpression(el) {
    // Example payload
    const payload = {
        target_type: el.dataset.type,
        target_id: el.dataset.id,
        section: el.closest("[data-section]")?.dataset.section || null,
        ts: Date.now()
    };

    // For now: just debug / future hook
    console.debug("Impression:", payload);
}

function initCardViews() {
    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            trackImpression(entry.target);
            obs.unobserve(entry.target);
        });
    }, { threshold: 0.6 });

    document.querySelectorAll(".view-card").forEach(card => {
        observer.observe(card);
    });
}
// VIEW Article / Product

function sendView(targetType, targetId) {
    const fd = new FormData();
    fd.append("target_type", targetType);
    fd.append("target_id", targetId);

    fetch("/view", { method: "POST", body: fd })
        .catch(() => {});
}
  
 
// ui.js  
// Sliders Actions
function initHeroSlider() {

  const prev = document.querySelector(".hero-slider__arrow--prev");
  const next = document.querySelector(".hero-slider__arrow--next");

  if (prev) {
    prev.classList.add("disabled");
    prev.dataset.slidePrev = -1;
  }

  if (next) {
    next.dataset.slideNext = 1;
  }

  document.querySelector(".hero-slider__dot")?.classList.add("active");
}


function handleHeroSliderControls(control) {
  let slideIndex = -1;

  if (control.classList.contains("hero-slider__arrow--prev"))
    slideIndex = Number(control.dataset.slidePrev);

  else if (control.hasAttribute("data-slide"))
    slideIndex = Number(control.dataset.slide);

  else if (control.classList.contains("hero-slider__arrow--next"))
    slideIndex = Number(control.dataset.slideNext);

  if (slideIndex === -1) return;

  const slides = document.querySelectorAll(".hero-slide");
  const dots = document.querySelectorAll(".hero-slider__dot");
  const track = document.querySelector(".hero-slider__track");

  const lastIndex = slides.length - 1;

  /* move slider */
  track.style.transform = `translateX(-${slideIndex * 100}%)`;

  /* update dots */
  document.querySelector(".hero-slider__dot.active")?.classList.remove("active");
  dots[slideIndex]?.classList.add("active");

  const controls = control.closest(".hero-slider__wrapper");
  const prev = controls?.querySelector(".hero-slider__arrow--prev");
  const next = controls?.querySelector(".hero-slider__arrow--next");

  if (prev) {
    prev.classList.toggle("disabled", slideIndex === 0);
    prev.dataset.slidePrev = slideIndex - 1;
  }

  if (next) {
    next.classList.toggle("disabled", slideIndex === lastIndex);
    next.dataset.slideNext = slideIndex + 1;
  }
}



// // Mode Actions
// function applyMode() {
//     const btn = document.querySelector('.mode-toggle');
//     const icon = btn?.querySelector('i');
//     // sync early-applied class to body
//     if (document.documentElement.classList.contains('dark-mode')) {
//       document.body.classList.add('dark-mode');
//     }
//     // sync icon on load
//     if (document.body.classList.contains('dark-mode')) {
//       icon?.classList.replace('fa-sun', 'fa-moon');
//     }
// }

// function handleModeToggle(e) {
//     const icon = e?.querySelector('i');
//     const isDark = document.body.classList.contains('dark-mode');
//     icon?.classList.toggle('fa-moon', isDark);
//     icon?.classList.toggle('fa-sun', !isDark);
//     localStorage.setItem('theme', isDark ? 'dark' : 'light');
// }

function initTheme() {
  const saved = localStorage.getItem('theme');
  const isDark = saved === 'dark';
  document.documentElement.classList.toggle('dark-mode', isDark);
  document.documentElement.classList.toggle('light-mode', !isDark);

  // if (saved === 'dark') {
  //   document.documentElement.classList.add('dark-mode');
  // } else {
  //   document.documentElement.classList.add('light-mode');
  // }
  // applyMode();
  syncModeUI();
}

function syncModeUI() {
  const btn = document.querySelector('.mode-toggle');
  const icon = btn?.querySelector('i');

  const isDark = document.body.classList.contains('dark-mode');

  icon?.classList.toggle('fa-moon', !isDark);
  icon?.classList.toggle('fa-sun', isDark);
}

function applyMode() {
  // sync body with html
  if (document.documentElement.classList.contains('dark-mode')) {
    document.body.classList.replace('light-mode', 'dark-mode');
  } else {
    document.body.classList.replace('dark-mode', 'light-mode');
  }

  syncModeUI();
}
function handleModeToggle() {
  const isDark = document.body.classList.contains('dark-mode');
  const nextIsDark = !isDark;

  document.body.classList.toggle('dark-mode', nextIsDark);
  document.body.classList.toggle('light-mode', !nextIsDark);

  localStorage.setItem('theme', nextIsDark ? 'dark' : 'light');

  syncModeUI();
}


// Review Dropdown List Actions

function handleReviewsToggle() {
  const dropdownMenu = document.querySelector('.reviews__dropdown-menu');
  const isShown = !dropdownMenu.classList.contains('is-hidden');
  dropdownMenu.classList.toggle('is-hidden', isShown);
}

function closeOverlay() {
  const specs = document.querySelector(".item-details-dialog");
  if (specs) specs.classList.remove("is-open");

  const gallery = document.querySelector("[data-gallery-overlay]");
  if (gallery) gallery.hidden = true;
}

function handleImageControls(control) {
  const gallery = control.closest(".item-gallery");
  if (!gallery) return;

  const displayImg = gallery.querySelector(".item-gallery__img");
  const thumbnails = [...gallery.querySelectorAll("[data-gallery-thumb]")];
  const galleryLength = thumbnails.length;
  
  let currentIndex = parseInt(displayImg.dataset.galleryMain || "1");
  let newIndex = parseInt(control.dataset.galleryNewImage || control.dataset.galleryThumb);

  if (!newIndex || newIndex < 1 || newIndex > galleryLength) return;

  // Find the thumbnail for the new index
  const newThumb = gallery.querySelector(`[data-gallery-thumb="${newIndex}"] img`);
  if (!newThumb) return;

  // 1. Update Main Display
  displayImg.src = newThumb.src;
  displayImg.alt = newThumb.alt;
  displayImg.dataset.galleryMain = newIndex;

  // 2. Update Index Counter
  const indexEl = gallery.querySelector(`[data-gallery-index]`);
  if (indexEl) indexEl.textContent = newIndex;

  // 3. Update Sync Arrows
  const prevBtn = gallery.querySelector(".item-gallery__nav--prev");
  const nextBtn = gallery.querySelector(".item-gallery__nav--next");

  if (prevBtn) {
    prevBtn.dataset.galleryNewImage = newIndex - 1;
    prevBtn.classList.toggle("disabled", newIndex === 1);
  }
  if (nextBtn) {
    nextBtn.dataset.galleryNewImage = newIndex + 1;
    nextBtn.classList.toggle("disabled", newIndex === galleryLength);
  }
}
function navigateGallery(direction) {
  const overlay = document.querySelector("[data-gallery-overlay]");
  if (!overlay || overlay.hidden) return;

  const images = JSON.parse(overlay.dataset.images || "[]");
  if (!images.length) return;

  let currentIndex = parseInt(overlay.dataset.index || "0");
  let nextIndex = currentIndex + direction;

  // Cycle around
  if (nextIndex < 0) nextIndex = images.length - 1;
  if (nextIndex >= images.length) nextIndex = 0;

  overlay.dataset.index = nextIndex;
  
  const displayImg = overlay.querySelector(".displayed-img");
  displayImg.src = images[nextIndex];

  const currentEl = overlay.querySelector(".current");
  if (currentEl) currentEl.textContent = nextIndex + 1;

  const totalEl = overlay.querySelector(".total");
  if (totalEl) totalEl.textContent = images.length;
}

function initGallery(e) {
  const gallery = e.target.closest(".item-gallery");
  if (!gallery) return;

  // Use the larger images list from data-gallery-thumbs or similar, but for now thumbnails
  const thumbs = [...gallery.querySelectorAll("[data-gallery-thumb] img")];
  if (!thumbs.length) return;

  const overlay = document.querySelector("[data-gallery-overlay]");
  if (!overlay) return;

  const images = thumbs.map(img => img.src);
  overlay.dataset.images = JSON.stringify(images);
  overlay.dataset.index = "0";

  const displayImg = overlay.querySelector(".displayed-img");
  displayImg.src = images[0];

  const currentEl = overlay.querySelector(".current");
  if (currentEl) currentEl.textContent = "1";
  const totalEl = overlay.querySelector(".total");
  if (totalEl) totalEl.textContent = images.length;

  overlay.hidden = false;
}

function toggleActive(el) {
  el.classList.toggle("active", !el.classList.contains('active'));
}  
 
