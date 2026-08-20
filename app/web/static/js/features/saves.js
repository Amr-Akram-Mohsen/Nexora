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
        const endpoint = window.APP?.urls?.checkSaveBatch || "/check-save-batch";
        const res = await fetch(`${endpoint}?${params.toString()}`);
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

// Global state for saved products page
let currentSavedView = 'all';

function updateSavedHeaderCount() {
    const totalCountEl = document.getElementById('total-count');
    const totalCountLabel = document.getElementById('total-count-label');
    const collectionsContainer = document.querySelector('.saved-collections');

    if (!totalCountEl || !collectionsContainer) return;
    
    const numItems = collectionsContainer.querySelectorAll('[data-domain-type="commercial"] .card, [data-domain-type="commercial"] [data-saveable-card]').length;
    const numArticles = collectionsContainer.querySelectorAll('[data-domain-type="content"] .card, [data-domain-type="content"] [data-saveable-card]').length;
    const total = numItems + numArticles;

    totalCountEl.textContent = total;
    if (totalCountLabel) totalCountLabel.textContent = total === 1 ? 'product' : 'products';
}

function setSavedActiveFilter(activeId) {
    const filters = document.querySelectorAll('.filter-item');
    filters.forEach(el => el.classList.remove('is-active'));
    const activeEl = document.getElementById(activeId) || document.querySelector(`a[href="${activeId}"]`)?.closest('.filter-item');
    if (activeEl) activeEl.classList.add('is-active');
}

function showSavedAll() {
    currentSavedView = 'all';
    const groups = document.querySelectorAll('.collection-group');
    groups.forEach(g => g.style.display = 'flex');
    setSavedActiveFilter('filter-all');
    updateSavedHeaderCount();
}

function showCollection(hash) {
    currentSavedView = hash;
    const groups = document.querySelectorAll('.collection-group');
    groups.forEach(g => {
        if (`#${g.id}` === hash) {
            g.style.display = 'flex';
        } else {
            g.style.display = 'none';
        }
    });
    setSavedActiveFilter(hash);
    updateSavedHeaderCount();
}

function handleSavedItemsFilterClick(e) {
    const filterLink = e.target.closest('.filter-item__link');
    if (!filterLink || !filterLink.closest('.filter-sidebar')) return false;
    
    const filterItem = filterLink.closest('.filter-item');
    if (!filterItem) return false;

    const href = filterLink.getAttribute('href');
    
    if (href === '#all') {
        e.preventDefault();
        showSavedAll();
        window.location.hash = 'all';
        return true;
    } else if (href.startsWith('#collection-')) {
        e.preventDefault();
        showCollection(href);
        window.location.hash = href.substring(1);
        return true;
    }
    
    return false;
}

function initSavedItemsPage() {
    const collectionsContainer = document.querySelector('.saved-collections');
    if (!collectionsContainer) return; // Not on the saved products page
    
    // Check hash on load
    const hash = window.location.hash;
    if (hash.startsWith('#collection-')) {
        showCollection(hash);
    } else {
        showSavedAll();
    }

    // MutationObserver to sync counts and sidebar filters dynamically on card removal (unsave)
    const observer = new MutationObserver(function(mutations) {
        const numItems = collectionsContainer.querySelectorAll('[data-domain-type="commercial"] .card, [data-domain-type="commercial"] [data-saveable-card]').length;
        const numArticles = collectionsContainer.querySelectorAll('[data-domain-type="content"] .card, [data-domain-type="content"] [data-saveable-card]').length;
        const totalCount = numItems + numArticles;

        // Update header count based on current view
        updateSavedHeaderCount();

        // Update sidebar badges
        const badgeAll = document.querySelector('#filter-all .filter-section__badge');
        if (badgeAll) badgeAll.textContent = totalCount;
        
        // Handle fully empty state dynamically if needed
        if (totalCount === 0) {
            window.location.reload(); // Quick way to show the server-rendered empty state
        }
    });

    observer.observe(collectionsContainer, { childList: true, subtree: true });
    
    // Initialize move collection logic
    initMoveToCollection();
}

function initMoveToCollection() {
    const collectionsContainer = document.querySelector('.saved-collections');
    if (!collectionsContainer) return;
    
    const collectionElements = document.querySelectorAll('.filter-item:not(#filter-all) .filter-item__link span:first-child');
    const collections = Array.from(collectionElements).map(el => el.textContent.trim());

    // Show server-rendered move-collection wrappers and populate options once
    document.querySelectorAll('.move-collection-wrapper').forEach(wrapper => {
        wrapper.classList.remove('is-hidden');
        const select = wrapper.querySelector('.move-item-select');
        if (select && select.options.length <= 1) {
            collections.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c;
                select.appendChild(opt);
            });
            const globalOpt = document.createElement('option');
            globalOpt.value = 'general';
            globalOpt.textContent = 'Global';
            select.appendChild(globalOpt);
        }
    });
}

async function handleMoveCollectionChange(e) {
    const select = e.target.closest('.move-item-select');
    if (!select) return false;
    
    const newCollection = select.value;
    if (!newCollection) return false;
    
    const card = select.closest('.card, [data-saveable-card]');
    const panel = select.closest('.interaction-panel');
    if (!panel) return false;
    
    const targetType = panel.dataset.type;
    const targetId = panel.dataset.id;
    const currentCollection = card?.closest('.collection-group')?.querySelector('.section-title')?.textContent.trim() || 'General';
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || document.querySelector('input[name="csrf_token"]')?.value;

    try {
        const endpoint = window.APP?.urls?.moveSave || "/save/move";
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                target_type: targetType,
                target_id: targetId,
                new_collection_name: newCollection,
                old_collection_name: currentCollection
            })
        });
        
        const data = await res.json();
        if (res.ok && data.success) {
            if (typeof showToast === 'function') {
                showToast('Product moved successfully', 'success');
            }
            setTimeout(() => window.location.reload(), 800);
        } else {
            if (typeof showToast === 'function') {
                showToast(data.error || 'Failed to move product.', 'error');
            } else {
                alert(data.error || 'Failed to move product.');
            }
            select.value = ""; // Reset
        }
    } catch(err) {
        console.error(err);
        if (typeof showToast === 'function') {
            showToast('An error occurred.', 'error');
        }
    }
    return true;
}
