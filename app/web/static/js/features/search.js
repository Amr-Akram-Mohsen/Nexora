function initSearch() {
    // Header search elements
    const headerSearchPanel = document.getElementById('header-search-panel');
    const headerInput = headerSearchPanel?.querySelector('.header-search__input');
    const headerClearBtn = headerSearchPanel?.querySelector('.header-search__clear');
    const searchToggleBtn = document.querySelector('.search-toggle');

    // Search results page elements
    const resultsForm = document.querySelector('.search-form');
    const resultsInput = resultsForm?.querySelector('.input-search');
    const resultsClearBtn = resultsForm?.querySelector('.search-page-form__clear');

    function toggleClearButton(input, btn) {
        if (!input || !btn) return;
        btn.classList.toggle('is-visible', input.value.trim().length > 0);
    }

    // Initialize state on load
    if (headerInput && headerClearBtn) {
        toggleClearButton(headerInput, headerClearBtn);
        headerInput.addEventListener('input', () => toggleClearButton(headerInput, headerClearBtn));
        headerClearBtn.addEventListener('click', () => {
            headerInput.value = '';
            toggleClearButton(headerInput, headerClearBtn);
            headerInput.focus();
        });
    }

    if (resultsInput && resultsClearBtn) {
        toggleClearButton(resultsInput, resultsClearBtn);
        resultsInput.addEventListener('input', () => toggleClearButton(resultsInput, resultsClearBtn));
        resultsClearBtn.addEventListener('click', () => {
            resultsInput.value = '';
            toggleClearButton(resultsInput, resultsClearBtn);
            resultsInput.focus();
        });
    }

    // Dismiss search panel on clicking outside
    document.addEventListener('click', (e) => {
        if (!headerSearchPanel || !headerSearchPanel.classList.contains('active')) return;

        const clickedInsidePanel = headerSearchPanel.contains(e.target);
        const clickedToggleBtn = searchToggleBtn?.contains(e.target);

        if (!clickedInsidePanel && !clickedToggleBtn) {
            headerSearchPanel.classList.remove('active');
            searchToggleBtn?.setAttribute('aria-expanded', 'false');
        }
    });

    // Dismiss search panel on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && headerSearchPanel?.classList.contains('active')) {
            headerSearchPanel.classList.remove('active');
            searchToggleBtn?.setAttribute('aria-expanded', 'false');
            searchToggleBtn?.focus();
        }
    });

    initListingSidebar();
}

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

function handleFilterClick(e) {
    const filterChip = e.target.closest(".filter-chip");
    if (!filterChip) return false;
    filterContent(filterChip);
    return true;
}

function handleSearchClick(e) {
    const searchToggleBtn = e.target.closest('.search-toggle');
    if (!searchToggleBtn) return false;

    const siteHeader = searchToggleBtn.closest('.site-header');
    const searchPanel = siteHeader.querySelector('.header-search');
    const isActive = searchPanel.classList.toggle('active');
    searchToggleBtn.setAttribute('aria-expanded', String(isActive));
    if (isActive) {
        const input = searchPanel.querySelector('.header-search__input');
        const clearBtn = searchPanel.querySelector('.header-search__clear');
        if (input) {
            input.focus();
            if (clearBtn) {
                clearBtn.classList.toggle('is-visible', input.value.trim().length > 0);
            }
        }
    }
    return true;
}

function handleSortChange(e) {
    const sortSelect = e.target.closest('.sort-select');
    if (!sortSelect) return false;
    window.location.href = sortSelect.value;
    return true;
}

function handleMoreFiltersClick(e) {
    const btn = e.target.closest('[data-action="toggle-more-filters"]');
    if (!btn) return false;
    
    const section = btn.closest('.filter-section');
    const extras = section.querySelectorAll('.filter-item--extra');
    const isExpanded = btn.getAttribute('aria-expanded') === 'true';

    extras.forEach(el => {
        el.style.display = isExpanded ? 'none' : 'flex';
    });

    btn.setAttribute('aria-expanded', !isExpanded);
    
    // Avoid string construction
    btn.replaceChildren();
    const icon = document.createElement('i');
    icon.className = isExpanded ? 'fas fa-plus' : 'fas fa-minus';
    btn.appendChild(icon);
    btn.appendChild(document.createTextNode(isExpanded ? ` Show more (+${extras.length})` : ' Show less'));
    
    return true;
}

function initListingSidebar() {
    const sidebar = document.getElementById('listingSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const closeBtn = document.getElementById('sidebarClose');
    const openBtn = document.getElementById('filterToggleBtn');

    function openSidebar() {
      if (sidebar) sidebar.classList.add('is-open');
      if (overlay) overlay.classList.add('is-visible');
      document.body.style.overflow = 'hidden';
    }
    function closeSidebar() {
      if (sidebar) sidebar.classList.remove('is-open');
      if (overlay) overlay.classList.remove('is-visible');
      document.body.style.overflow = '';
    }

    if (openBtn) openBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);
}

function initSearchHighlighting() {
    // Initial Search Highlighting
    if (window.SEARCH_QUERY) {
        const cards = document.querySelectorAll('.card__title, .card__excerpt, .item-card__name, .item-card__description');
        const escapedQuery = String(window.SEARCH_QUERY).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        cards.forEach(card => {
            const walk = document.createTreeWalker(card, NodeFilter.SHOW_TEXT, null, false);
            const nodesToReplace = [];
            let n;
            while (n = walk.nextNode()) {
                if (regex.test(n.nodeValue)) nodesToReplace.push(n);
                regex.lastIndex = 0;
            }
            nodesToReplace.forEach(node => {
                const fragment = document.createDocumentFragment();
                let lastIndex = 0;
                let match;
                regex.lastIndex = 0;
                while ((match = regex.exec(node.nodeValue)) !== null) {
                    if (match.index > lastIndex) {
                        fragment.appendChild(document.createTextNode(node.nodeValue.substring(lastIndex, match.index)));
                    }
                    const mark = document.createElement('mark');
                    mark.className = 'search-highlight';
                    mark.textContent = match[0];
                    fragment.appendChild(mark);
                    lastIndex = regex.lastIndex;
                    if (!regex.global) break; 
                }
                if (lastIndex < node.nodeValue.length) {
                    fragment.appendChild(document.createTextNode(node.nodeValue.substring(lastIndex)));
                }
                node.parentNode.replaceChild(fragment, node);
            });
        });
    }
}