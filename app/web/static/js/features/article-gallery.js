document.addEventListener('DOMContentLoaded', () => {
    const articleContent = document.querySelector('.article-html');
    if (!articleContent) return;

    // Find all figures in the article body
    let figures = Array.from(articleContent.querySelectorAll('figure'));
    
    // Remove empty figures (e.g., just an empty <picture> tag or img without src)
    figures = figures.filter(figure => {
        const media = figure.querySelector('img, video, iframe');
        
        if (!media) {
            figure.remove();
            return false;
        }

        // If it's an image, make sure it actually has a source
        if (media.tagName.toLowerCase() === 'img') {
            const src = media.getAttribute('src');
            if (!src || src.trim() === '') {
                figure.remove();
                return false;
            }
        }
        
        return true;
    });

    if (figures.length === 0) return;
    
    // Group adjacent figures
    const groups = [];
    let currentGroup = [];

    figures.forEach((figure, index) => {
        currentGroup.push(figure);
        
        // Find the next element sibling, ignoring empty text nodes
        let nextSibling = figure.nextSibling;
        while (nextSibling && nextSibling.nodeType !== 1) {
            nextSibling = nextSibling.nextSibling;
        }

        // If the next sibling is not a figure, the group ends
        if (!nextSibling || nextSibling.tagName.toLowerCase() !== 'figure') {
            if (currentGroup.length > 1) {
                groups.push(currentGroup);
            }
            currentGroup = [];
        }
    });

    // Wrap each valid group in a grid container
    groups.forEach(group => {
        const gridContainer = document.createElement('div');
        gridContainer.className = 'article-figure-grid';
        
        // Insert grid container before the first figure
        group[0].parentNode.insertBefore(gridContainer, group[0]);
        
        // Move all figures in the group into the container
        group.forEach(figure => {
            gridContainer.appendChild(figure);
        });
    });

    // ── Professional Loading State for Media ──
    const mediaElements = articleContent.querySelectorAll('img, video, iframe');
    mediaElements.forEach(media => {
        // If image is already loaded (from cache), immediately mark it
        if (media.tagName.toLowerCase() === 'img' && media.complete) {
            media.classList.add('is-loaded');
            return;
        }
        
        // Otherwise wait for load event
        media.addEventListener('load', () => {
            media.classList.add('is-loaded');
        });
        
        // For video elements
        media.addEventListener('loadeddata', () => {
            media.classList.add('is-loaded');
        });
    });
});
