/**
 * Progressive Reveal feature for large card collections.
 * Handles client-side hiding and staggered revealing of grid products.
 */

const REVEAL_LIMIT = 12;

/**
 * Initializes all expandable grids on the page.
 * Hides products beyond the initial limit and shows their corresponding "Show More" buttons.
 */
function initProgressiveReveal() {
    const grids = document.querySelectorAll('[data-expandable-grid="true"]');

    grids.forEach(grid => {
        const children = Array.from(grid.children);

        // Only apply progressive reveal if products exceed the initial limit
        if (children.length > REVEAL_LIMIT) {
            // Hide products beyond the limit
            for (let i = REVEAL_LIMIT; i < children.length; i++) {
                children[i].classList.add('grid-product-hidden');
            }

            // Find and show the associated toggle button
            const parent = grid.parentNode;
            if (parent) {
                const button = parent.querySelector('[data-section-toggle]');
                if (button) {
                    button.removeAttribute('hidden');
                }
            }
        }
    });
}

/**
 * Reveals the next batch of hidden products in the grid.
 * @param {HTMLElement} grid - The grid container element
 * @param {HTMLElement} button - The button element that triggered the reveal
 */
function revealNextBatch(grid, button) {
    if (!grid) return;

    const hiddenItems = Array.from(grid.children).filter(product =>
        product.classList.contains('grid-product-hidden')
    );

    if (hiddenItems.length === 0) {
        if (button) button.setAttribute('hidden', '');
        return;
    }

    // Determine the next batch to reveal
    const batchToReveal = hiddenItems.slice(0, REVEAL_LIMIT);

    batchToReveal.forEach((product, index) => {
        // Remove hidden class
        product.classList.remove('grid-product-hidden');

        // Apply staggered animation
        product.style.setProperty('--reveal-idx', index);
        product.classList.add('is-revealing');

        // Clean up animation class and variable after animation ends
        product.addEventListener('animationend', () => {
            product.classList.remove('is-revealing');
            product.style.removeProperty('--reveal-idx');
        }, { once: true });
    });

    // Check if there are still hidden products remaining
    const remainingHidden = Array.from(grid.children).filter(product =>
        product.classList.contains('grid-product-hidden')
    );

    if (remainingHidden.length === 0 && button) {
        // Gracefully hide the button
        button.setAttribute('hidden', '');
    }
}

function handleProgressiveRevealClick(e) {
    const button = e.target.closest('[data-section-toggle]');
    if (!button) return false;

    e.preventDefault();

    // Find the associated grid inside the same container/parent
    const parent = button.parentNode;
    if (parent) {
        const grid = parent.querySelector('[data-expandable-grid="true"]');
        if (grid) {
            revealNextBatch(grid, button);
            return true;
        }
    }

    return false;
}
