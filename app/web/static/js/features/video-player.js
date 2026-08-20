function initVideoPlayerEnhancements() {
    // 1. Parse Timestamps in Description
    const descBox = document.querySelector('.video-description-box__text');
    if (descBox) {
        // Regex for HH:MM:SS or MM:SS (with optional brackets like [01:23] or just 01:23)
        const timeRegex = /(?:\[|\b)((?:[0-5]?\d:)?(?:[0-5]?\d):(?:[0-5]\d))(?:\]|\b)/g;
        
        let hasTimestamps = false;
        let originalHtml = descBox.innerHTML;
        
        const replacedHtml = originalHtml.replace(timeRegex, (match, timeStr) => {
            hasTimestamps = true;
            
            // Calculate total seconds
            const parts = timeStr.split(':').map(n => parseInt(n, 10));
            let totalSeconds = 0;
            if (parts.length === 3) {
                totalSeconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
            } else if (parts.length === 2) {
                totalSeconds = parts[0] * 60 + parts[1];
            }
            
            return `<a href="#" class="video-timestamp-link" data-time="${totalSeconds}">${match}</a>`;
        });
        
        if (hasTimestamps) {
            descBox.innerHTML = replacedHtml;
        }
    }

    // 2. Handle Timestamp Clicks
    document.addEventListener('click', (e) => {
        const timestampLink = e.target.closest('.video-timestamp-link');
        if (!timestampLink) return;

        e.preventDefault();
        const time = parseInt(timestampLink.dataset.time, 10);
        
        const playerContainer = document.querySelector('.video-main-player');
        if (!playerContainer) return;

        let iframe = playerContainer.querySelector('iframe');
        
        if (!iframe) {
            // Iframe doesn't exist yet, simulate play button click first
            const playBtn = playerContainer.querySelector('[data-action="lazy-play"]');
            if (playBtn) playBtn.click();
            
            // Wait a brief moment for the iframe to be injected and ready
            setTimeout(() => {
                iframe = playerContainer.querySelector('iframe');
                if (iframe) seekIframe(iframe, time);
            }, 800);
        } else {
            // Iframe exists, seek immediately
            seekIframe(iframe, time);
            
            // Scroll to video if it's out of view and not sticky
            if (!playerContainer.classList.contains('is-sticky')) {
                playerContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });

    function seekIframe(iframe, time) {
        if (!iframe || !iframe.contentWindow) return;
        iframe.contentWindow.postMessage(JSON.stringify({
            "event": "command",
            "func": "seekTo",
            "args": [time, true]
        }), "*");
        
        // Ensure it's playing
        iframe.contentWindow.postMessage(JSON.stringify({
            "event": "command",
            "func": "playVideo",
            "args": []
        }), "*");
    }

    // 3. Auto-Play Next (Binge Mode) using YouTube Iframe API
    let ytPlayer = null;

    // Load YouTube API
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    window.onYouTubeIframeAPIReady = function() {
        const playerContainer = document.querySelector('.video-main-player');
        if (!playerContainer) return;

        // The iframe is created dynamically when the user clicks play
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.tagName === 'DIV' && node.classList.contains('video-player-wrapper')) {
                        const iframe = node.querySelector('iframe');
                        if (iframe) {
                            ytPlayer = new YT.Player(iframe, {
                                events: {
                                    'onStateChange': onPlayerStateChange,
                                    'onError': onPlayerError
                                }
                            });
                        }
                    }
                });
            });
        });
        
        observer.observe(playerContainer, { childList: true, subtree: true });
        
        // In case it already exists
        const existingIframe = playerContainer.querySelector('iframe');
        if (existingIframe) {
            ytPlayer = new YT.Player(existingIframe, {
                events: {
                    'onStateChange': onPlayerStateChange,
                    'onError': onPlayerError
                }
            });
        }
    };

    function onPlayerStateChange(event) {
        if (event.data === YT.PlayerState.ENDED) {
            showUpNext();
        }
    }

    function onPlayerError(event) {
        // 101 or 150 means the owner disabled playback outside of YouTube
        if (event.data === 101 || event.data === 150) {
            const wrapper = document.querySelector('.video-player-wrapper');
            const iframe = wrapper?.querySelector('iframe');
            if (wrapper && iframe) {
                const videoUrl = iframe.src.replace('embed/', 'watch?v=').split('?')[0];
                const template = document.getElementById('video-error-template');
                if (template) {
                    const clone = template.content.cloneNode(true);
                    const link = clone.querySelector('.video-error-link');
                    if (link) link.href = videoUrl;
                    wrapper.replaceChildren(clone);
                }
            }
        }
    }

    function showUpNext() {
        const wrapper = document.querySelector('.video-player-wrapper');
        if (!wrapper || wrapper.querySelector('.up-next-overlay')) return;

        // Find related content links from the sidebar
        const sidebar = document.querySelector('.detail-page__sidebar');
        if (!sidebar) return;
        
        const relatedLinks = Array.from(sidebar.querySelectorAll('a[href*="/contents/"]'));
        if (relatedLinks.length === 0) return;
        
        // Deduplicate and gather up to 4 videos
        const uniqueVideos = [];
        const seenUrls = new Set();
        
        relatedLinks.forEach(link => {
            if (seenUrls.has(link.href)) return;
            seenUrls.add(link.href);
            
            let title = "Related Video";
            const titleElement = link.querySelector('.card__title, .product-card__title, h4, h3, .content-snippet__title');
            if (titleElement) title = titleElement.textContent.trim();
            
            let thumb = "";
            const img = link.querySelector('img');
            if (img) thumb = img.src;
            
            uniqueVideos.push({ url: link.href, title, thumb });
        });
        
        const topVideos = uniqueVideos.slice(0, 4);
        if (topVideos.length === 0) return;
        
        const nextVideoUrl = topVideos[0].url;

        const overlayTemplate = document.getElementById('video-upnext-template');
        const itemTemplate = document.getElementById('video-upnext-item-template');
        if (!overlayTemplate) return;

        const overlayClone = overlayTemplate.content.cloneNode(true);
        const grid = overlayClone.querySelector('.up-next-grid');

        topVideos.forEach(v => {
            if (itemTemplate && grid) {
                const itemClone = itemTemplate.content.cloneNode(true);
                const itemLink = itemClone.querySelector('.up-next-card');
                if (itemLink) itemLink.href = v.url;
                const img = itemClone.querySelector('.up-next-card__thumb');
                const placeholder = itemClone.querySelector('.up-next-card__placeholder');
                if (v.thumb && img) {
                    img.src = v.thumb;
                    img.alt = v.title;
                    if (placeholder) placeholder.remove();
                } else if (img) {
                    img.remove();
                }
                const titleEl = itemClone.querySelector('.up-next-card__title');
                if (titleEl) titleEl.textContent = v.title;
                grid.appendChild(itemClone);
            }
        });

        wrapper.appendChild(overlayClone);

        const overlay = wrapper.querySelector('.up-next-overlay');
        const cancelBtn = overlay?.querySelector('.cancel-up-next-btn');
        let cancelled = false;
        let timeLeft = 10;

        cancelBtn?.addEventListener('click', () => {
            cancelled = true;
            overlay?.remove();
        });

        const timerInterval = setInterval(() => {
            if (cancelled) {
                clearInterval(timerInterval);
                return;
            }
            timeLeft--;
            const timerEl = overlay?.querySelector('#up-next-timer');
            if (timerEl) timerEl.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                window.location.href = nextVideoUrl;
            }
        }, 1000);
    }
}

document.addEventListener('DOMContentLoaded', initVideoPlayerEnhancements);
