function handleLazyVideoClick(e) {
    const btn = e.target.closest('[data-action="lazy-play"]');
    if (!btn) return false;

    e.preventDefault();
    e.stopPropagation();

    const container = btn.closest('.video-preview-container');
    if (!container) return false;

    const videoRef = container.dataset.videoRef;
    const platform = container.dataset.platform || 'youtube';

    let videoId = videoRef;
    if (platform === 'youtube') {
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
        const match = videoRef.match(regExp);
        if (match && match[2].length === 11) {
            videoId = match[2];
        }
    }

    let embedUrl = '';
    if (platform === 'youtube') {
        embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1&enablejsapi=1`;
    }

    if (embedUrl) {
        container.innerHTML = `
            <button type="button" class="btn btn--ghost video-sticky-close" aria-label="Close sticky video">
                <i class="fas fa-times"></i>
            </button>
            <div class="video-resize-handle">
                <i class="fas fa-arrows-alt-v"></i>
            </div>
            <div class="video-player-wrapper">
                <iframe class="video-player-iframe"
                        src="${embedUrl}"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen>
                </iframe>
            </div>
        `;
    }
    return true;
}
