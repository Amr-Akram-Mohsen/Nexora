/**
 * Progressive Reveal feature for large card collections.
 * Handles client-side hiding and staggered revealing of grid items.
 */

const REVEAL_LIMIT = 12;

/**
 * Initializes all expandable grids on the page.
 * Hides items beyond the initial limit and shows their corresponding "Show More" buttons.
 */
function initProgressiveReveal() {
    const grids = document.querySelectorAll('[data-expandable-grid="true"]');
    
    grids.forEach(grid => {
        const children = Array.from(grid.children);
        
        // Only apply progressive reveal if items exceed the initial limit
        if (children.length > REVEAL_LIMIT) {
            // Hide items beyond the limit
            for (let i = REVEAL_LIMIT; i < children.length; i++) {
                children[i].classList.add('grid-item-hidden');
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
 * Reveals the next batch of hidden items in the grid.
 * @param {HTMLElement} grid - The grid container element
 * @param {HTMLElement} button - The button element that triggered the reveal
 */
function revealNextBatch(grid, button) {
    if (!grid) return;
    
    const hiddenItems = Array.from(grid.children).filter(item => 
        item.classList.contains('grid-item-hidden')
    );
    
    if (hiddenItems.length === 0) {
        if (button) button.setAttribute('hidden', '');
        return;
    }
    
    // Determine the next batch to reveal
    const batchToReveal = hiddenItems.slice(0, REVEAL_LIMIT);
    
    batchToReveal.forEach((item, index) => {
        // Remove hidden class
        item.classList.remove('grid-item-hidden');
        
        // Apply staggered animation
        item.style.setProperty('--reveal-idx', index);
        item.classList.add('is-revealing');
        
        // Clean up animation class and variable after animation ends
        item.addEventListener('animationend', () => {
            item.classList.remove('is-revealing');
            item.style.removeProperty('--reveal-idx');
        }, { once: true });
    });
    
    // Check if there are still hidden items remaining
    const remainingHidden = Array.from(grid.children).filter(item => 
        item.classList.contains('grid-item-hidden')
    );
    
    if (remainingHidden.length === 0 && button) {
        // Gracefully hide the button
        button.setAttribute('hidden', '');
    }
}

/**
 * Handles global click events for the "Show More" buttons.
 * @param {Event} e - The click event object
 * @returns {boolean} - True if the click was handled, false otherwise
 */
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
