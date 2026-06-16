async function initAllSaves() {
    const buttons = Array.from(document.querySelectorAll(".save-btn"));
    const targets = [];

    buttons.forEach(btn => {
        const item = btn.closest("[data-id]");
        if (!item) return;
        targets.push({ 'type': item.dataset.type, 'id': item.dataset.id });
    });

    // Deduplicate targets
    const seen = new Set();
    const uniqueTargets = [];
    for (const t of targets) {
        const key = `${t.type}:${t.id}`;
        if (!seen.has(key)) {
            seen.add(key);
            uniqueTargets.push(t);
        }
    }

    if (uniqueTargets.length === 0) return;

    const params = new URLSearchParams();
    for (const t of uniqueTargets) {
        params.append("type", t.type);
        params.append("id", t.id);
    }

    try {
        const res = await fetch(`/check-save-batch?${params.toString()}`);
        if (!res.ok) return;

        const data = await res.json();

        buttons.forEach(btn => {
            const item = btn.closest("[data-id]");
            if (!item) return;
            const key = `${item.dataset.type}:${item.dataset.id}`;

            btn.classList.toggle('active', key in data);
        });
    } catch (error) {
        console.error("Could not initialize saves", error);
    }
}

// Global state for saved items page
let currentSavedView = 'all';

function updateSavedHeaderCount() {
    const totalCountEl = document.getElementById('total-count');
    const totalCountLabel = document.getElementById('total-count-label');
    const secProducts = document.getElementById('products-section');
    const secArticles = document.getElementById('articles-section');

    if (!totalCountEl) return;
    
    const numProducts = secProducts ? secProducts.querySelectorAll('.card').length : 0;
    const numArticles = secArticles ? secArticles.querySelectorAll('.card').length : 0;

    if (currentSavedView === 'products') {
        totalCountEl.textContent = numProducts;
        if (totalCountLabel) totalCountLabel.textContent = numProducts === 1 ? 'product' : 'products';
    } else if (currentSavedView === 'articles') {
        totalCountEl.textContent = numArticles;
        if (totalCountLabel) totalCountLabel.textContent = numArticles === 1 ? 'article' : 'articles';
    } else {
        totalCountEl.textContent = numProducts + numArticles;
        if (totalCountLabel) totalCountLabel.textContent = (numProducts + numArticles) === 1 ? 'item' : 'items';
    }
}

function setSavedActiveFilter(activeId) {
    const filters = ['filter-all', 'filter-products', 'filter-articles'];
    filters.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('is-active');
    });
    const activeEl = document.getElementById(activeId);
    if (activeEl) activeEl.classList.add('is-active');
}

function showSavedAll() {
    currentSavedView = 'all';
    const secProducts = document.getElementById('products-section');
    const secArticles = document.getElementById('articles-section');
    if (secProducts) secProducts.style.display = 'flex';
    if (secArticles) secArticles.style.display = 'flex';
    setSavedActiveFilter('filter-all');
    updateSavedHeaderCount();
}

function showSavedProducts() {
    currentSavedView = 'products';
    const secProducts = document.getElementById('products-section');
    const secArticles = document.getElementById('articles-section');
    if (secProducts) secProducts.style.display = 'flex';
    if (secArticles) secArticles.style.display = 'none';
    setSavedActiveFilter('filter-products');
    updateSavedHeaderCount();
}

function showSavedArticles() {
    currentSavedView = 'articles';
    const secProducts = document.getElementById('products-section');
    const secArticles = document.getElementById('articles-section');
    if (secProducts) secProducts.style.display = 'none';
    if (secArticles) secArticles.style.display = 'flex';
    setSavedActiveFilter('filter-articles');
    updateSavedHeaderCount();
}

function handleSavedItemsFilterClick(e) {
    const filterLink = e.target.closest('.filter-item__link');
    if (!filterLink || !filterLink.closest('.filter-sidebar')) return false;
    
    // Only handle saved items filters
    const filterItem = filterLink.closest('.filter-item');
    if (!filterItem || !filterItem.id.startsWith('filter-')) return false;

    e.preventDefault();
    const filterId = filterItem.id;
    
    if (filterId === 'filter-all') {
        showSavedAll();
        window.location.hash = 'all';
        return true;
    } else if (filterId === 'filter-products') {
        showSavedProducts();
        window.location.hash = 'products';
        return true;
    } else if (filterId === 'filter-articles') {
        showSavedArticles();
        window.location.hash = 'articles';
        return true;
    }
    
    return false;
}

function initSavedItemsPage() {
    const collectionsContainer = document.querySelector('.saved-collections');
    if (!collectionsContainer) return; // Not on the saved items page
    
    const filterProducts = document.getElementById('filter-products');
    const filterArticles = document.getElementById('filter-articles');

    // Check hash on load
    const hash = window.location.hash;
    if (hash === '#products' && filterProducts) {
        showSavedProducts();
    } else if (hash === '#articles' && filterArticles) {
        showSavedArticles();
    } else {
        showSavedAll();
    }

    // MutationObserver to sync counts and sidebar filters dynamically on card removal (unsave)
    const observer = new MutationObserver(function(mutations) {
        const secProducts = document.getElementById('products-section');
        const secArticles = document.getElementById('articles-section');
        const numProducts = secProducts ? secProducts.querySelectorAll('.card').length : 0;
        const numArticles = secArticles ? secArticles.querySelectorAll('.card').length : 0;
        const totalCount = numProducts + numArticles;

        // Update section count badges
        if (secProducts) {
            const secBadge = secProducts.querySelector('.section-title .count-badge');
            if (secBadge) secBadge.textContent = '(' + numProducts + ')';
        }
        if (secArticles) {
            const secBadge = secArticles.querySelector('.section-title .count-badge');
            if (secBadge) secBadge.textContent = '(' + numArticles + ')';
        }

        // Update header count based on current view
        updateSavedHeaderCount();

        // Update sidebar badges
        const badgeAll = document.querySelector('#filter-all .filter-section__badge');
        if (badgeAll) badgeAll.textContent = totalCount;

        const badgeProducts = document.querySelector('#filter-products .filter-section__badge');
        if (badgeProducts) badgeProducts.textContent = numProducts;

        const badgeArticles = document.querySelector('#filter-articles .filter-section__badge');
        if (badgeArticles) badgeArticles.textContent = numArticles;

        // Hide sidebar filter items if counts become 0
        const fp = document.getElementById('filter-products');
        const fa = document.getElementById('filter-articles');
        if (numProducts === 0 && fp) {
            fp.remove();
            if (currentSavedView === 'products') showSavedAll();
        }
        if (numArticles === 0 && fa) {
            fa.remove();
            if (currentSavedView === 'articles') showSavedAll();
        }
        
        // Handle fully empty state dynamically if needed
        if (totalCount === 0) {
            window.location.reload(); // Quick way to show the server-rendered empty state
        }
    });

    observer.observe(collectionsContainer, { childList: true, subtree: true });
}
