document.addEventListener('DOMContentLoaded', () => {
    const articleContent = document.querySelector('.article-html');
    if (!articleContent) return;

    // Find all figures in the article body
    const figures = Array.from(articleContent.querySelectorAll('figure'));
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
});
