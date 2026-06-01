async function handleSearch(form) {
    const formData = new FormData(form);
    const query = formData.get('query') || "";

    if (!query.trim()) return;

    const action = form.getAttribute("action") || "/search";
    const url = `${action}?query=${encodeURIComponent(query)}`;

    const res = await fetch(url, {
        method: "GET",
        headers: { "X-Requested-With": "XMLHttpRequest" } // lets Flask know it's AJAX
    });

    const data = await res.json();

    if (data.success) {
        // Replace main content only
        const mainContent = document.querySelector('#main-content');
        if (mainContent) {
            mainContent.innerHTML = data.html;
            window.history.pushState({}, "", url);
            document.querySelector(".header-search")?.classList.remove("active");
            document.querySelector(".search-toggle")?.setAttribute("aria-expanded", "false");
        }
    } else if (data.error) {
        showInlineTooltip(form, data.error);
    }
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

// let newsletterHandled = false;

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
        searchPanel.querySelector('.header-search__input')?.focus();
    }
    return true;

}

function handleSortChange(e) {
    const sortSelect = e.target.closest('.sort-select');
    if (!sortSelect) return false;
    window.location.href = sortSelect.value;
    return true;
}

function initSearchHighlighting() {
    // Initial Search Highlighting
    if (window.SEARCH_QUERY) {
        const cards = document.querySelectorAll('.card__title, .card__excerpt, .item-card__name, .item-card__description');
        const escapedQuery = String(window.SEARCH_QUERY).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        cards.forEach(card => {
            card.innerHTML = card.innerHTML.replace(regex, '<mark class="search-highlight">$1</mark>');
        });
    }
}