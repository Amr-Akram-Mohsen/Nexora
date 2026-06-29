function initVideoSticky() {
    const containers = document.querySelectorAll('.video-player-container');
    if (!containers.length) return;

    // Use IntersectionObserver to detect when the video wrapper is out of view
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const container = entry.target;
            const player = container.querySelector('.video-main-player');
            if (!player) return;
            
            // Only make it sticky if the video player has been initialized (iframe exists)
            const hasIframe = player.querySelector('.video-player-wrapper') !== null;
            const isDismissed = player.classList.contains('is-dismissed');
            
            if (!entry.isIntersecting && hasIframe && entry.boundingClientRect.top < 0 && !isDismissed) {
                // Scrolled past the container -> make sticky
                player.classList.add('is-sticky');
            } else if (entry.isIntersecting) {
                // Scrolled back into view -> remove sticky
                player.classList.remove('is-sticky');
            }
        });
    }, {
        root: null,
        threshold: 0, 
        rootMargin: "0px 0px 0px 0px"
    });

    containers.forEach(container => {
        observer.observe(container);
    });

    // Add close button event delegation
    document.addEventListener('click', (e) => {
        const closeBtn = e.target.closest('.video-sticky-close');
        if (!closeBtn) return;
        
        e.preventDefault();
        const player = closeBtn.closest('.video-main-player');
        if (player) {
            player.classList.remove('is-sticky');
            player.classList.add('is-dismissed');
            
            const container = player.closest('.video-player-container');
            if (container) observer.unobserve(container);
            
            const iframe = player.querySelector('iframe');
            if (iframe) {
                const src = iframe.src;
                iframe.src = src;
            }
        }
    });

    // Custom Resize Handle Logic
    document.addEventListener('mousedown', (e) => {
        const handle = e.target.closest('.video-resize-handle');
        if (!handle) return;
        
        e.preventDefault();
        const player = handle.closest('.video-main-player');
        if (!player) return;
        
        let startX = e.clientX;
        let startWidth = player.getBoundingClientRect().width;
        
        // Prevent iframe from eating mouse events during drag
        player.classList.add('is-resizing');
        
        const onMouseMove = (moveEvent) => {
            const dx = startX - moveEvent.clientX;
            let newWidth = startWidth + dx;
            
            if (newWidth < 240) newWidth = 240;
            if (newWidth > 800) newWidth = 800;
            if (newWidth > window.innerWidth - 40) newWidth = window.innerWidth - 40;
            
            player.style.width = `${newWidth}px`;
        };
        
        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.body.style.userSelect = '';
            player.classList.remove('is-resizing');
        };
        
        document.body.style.userSelect = 'none';
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });
}

// Attach to the global init or run immediately if deferred
document.addEventListener('DOMContentLoaded', initVideoSticky);
