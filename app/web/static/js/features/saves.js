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
    const collectionsContainer = document.querySelector('.saved-collections');

    if (!totalCountEl || !collectionsContainer) return;
    
    const numProducts = collectionsContainer.querySelectorAll('[data-domain-type="commercial"] .card').length;
    const numArticles = collectionsContainer.querySelectorAll('[data-domain-type="content"] .card').length;

    totalCountEl.textContent = numProducts + numArticles;
    if (totalCountLabel) totalCountLabel.textContent = (numProducts + numArticles) === 1 ? 'item' : 'items';
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

    e.preventDefault();
    const href = filterLink.getAttribute('href');
    
    if (href === '#all') {
        showSavedAll();
        window.location.hash = 'all';
        return true;
    } else if (href.startsWith('#collection-')) {
        showCollection(href);
        window.location.hash = href.substring(1);
        return true;
    }
    
    return false;
}

function initSavedItemsPage() {
    const collectionsContainer = document.querySelector('.saved-collections');
    if (!collectionsContainer) return; // Not on the saved items page
    
    // Check hash on load
    const hash = window.location.hash;
    if (hash.startsWith('#collection-')) {
        showCollection(hash);
    } else {
        showSavedAll();
    }

    // MutationObserver to sync counts and sidebar filters dynamically on card removal (unsave)
    const observer = new MutationObserver(function(mutations) {
        const numProducts = collectionsContainer.querySelectorAll('[data-domain-type="commercial"] .card').length;
        const numArticles = collectionsContainer.querySelectorAll('[data-domain-type="content"] .card').length;
        const totalCount = numProducts + numArticles;

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
    
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || document.querySelector('input[name="csrf_token"]')?.value;

    document.querySelectorAll('.card').forEach(card => {
        const panel = card.querySelector('.interaction-panel');
        if (!panel) return;
        
        const targetType = panel.dataset.type;
        const targetId = panel.dataset.id;
        
        const currentCollection = card.closest('.collection-group')?.querySelector('.section-title')?.textContent.trim() || 'General';
        const actions = panel.querySelector('.interaction-panel__actions');
        if (!actions) return;
        
        // Prevent double injection
        if (actions.querySelector('.move-collection-wrapper')) return;
        
        let optionsHtml = `<option value="" disabled selected>Move</option>`;
        collections.forEach(c => {
            optionsHtml += `<option value="${c}">${c}</option>`;
        });
        optionsHtml += `<option value="general">Global</option>`;
        
        const selectHtml = `
            <div class="move-collection-wrapper">
                <select class="move-item-select" aria-label="Move to collection">
                    ${optionsHtml}
                </select>
                <i class="fas fa-chevron-down move-item-select-icon"></i>
            </div>
        `;
        actions.insertAdjacentHTML('afterbegin', selectHtml);
        
        actions.querySelector('.move-item-select').addEventListener('change', async (e) => {
            const newCollection = e.target.value;
            if (!newCollection) return;
            
            try {
                const res = await fetch("/save/move", {
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
                        showToast('Item moved successfully', 'success');
                    }
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    if (typeof showToast === 'function') {
                        showToast(data.error || 'Failed to move item.', 'error');
                    } else {
                        alert(data.error || 'Failed to move item.');
                    }
                    e.target.value = ""; // Reset
                }
            } catch(err) {
                console.error(err);
                if (typeof showToast === 'function') {
                    showToast('An error occurred.', 'error');
                }
            }
        });
    });
}
