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
            const iframe = wrapper.querySelector('iframe');
            if (wrapper && iframe) {
                const videoUrl = iframe.src.replace('embed/', 'watch?v=').split('?')[0];
                wrapper.innerHTML = `
                    <div class="flex flex-col items-center justify-center h-full w-full bg-black text-center p-6 absolute inset-0 z-50">
                        <i class="fab fa-youtube text-red-600 mb-4" style="font-size: 3rem;"></i>
                        <h3 class="text-white text-xl font-bold mb-2">Playback Disabled</h3>
                        <p class="text-gray-400 mb-6 max-w-md">The owner of this video has disabled playback on other websites. Don't worry, you can still watch it directly on YouTube!</p>
                        <a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="background: #ef4444; color: white; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: 600;">
                            Watch on YouTube
                        </a>
                    </div>
                `;
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
        
        // The first one is the auto-play target
        const nextVideoUrl = topVideos[0].url;

        let gridHtml = topVideos.map(v => `
            <a href="${v.url}" style="display: flex; flex-direction: column; text-decoration: none; text-align: left; background: rgba(255,255,255,0.05); border-radius: 8px; overflow: hidden; transition: transform 0.2s; border: 1px solid rgba(255,255,255,0.1);" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                ${v.thumb ? `<img src="${v.thumb}" style="width: 100%; aspect-ratio: 16/9; object-fit: cover;">` : '<div style="width:100%; aspect-ratio:16/9; background:#222;"></div>'}
                <div style="padding: 10px;">
                    <p style="color: white; font-size: 0.9rem; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${v.title}</p>
                </div>
            </a>
        `).join('');

        // Overlay UI with 10 second timeout
        wrapper.insertAdjacentHTML('beforeend', `
            <div class="up-next-overlay" style="position: absolute; inset: 0; background: rgba(0,0,0,0.9); display: flex; flex-direction: column; align-products: center; justify-content: center; z-index: 50; padding: 20px; box-sizing: border-box;">
                <div class="flex justify-between w-full" style="max-width: 800px; display: flex; justify-content: space-between; align-products: center; margin-bottom: 20px;">
                    <h3 style="color: white; font-size: 1.2rem; margin: 0;">Up Next in <span id="up-next-timer">10</span>s</h3>
                    <button class="cancel-up-next-btn" style="background: none; border: none; color: #ccc; cursor: pointer; font-size: 1rem;"><i class="fas fa-times"></i> Cancel</button>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; width: 100%; max-width: 800px;">
                    ${gridHtml}
                </div>
            </div>
        `);
        
        let cancelled = false;
        let timeLeft = 10;
        
        wrapper.querySelector('.cancel-up-next-btn').addEventListener('click', () => {
            cancelled = true;
            const overlay = wrapper.querySelector('.up-next-overlay');
            if (overlay) overlay.remove();
        });
        
        const timerInterval = setInterval(() => {
            if (cancelled) {
                clearInterval(timerInterval);
                return;
            }
            timeLeft--;
            const timerEl = wrapper.querySelector('#up-next-timer');
            if (timerEl) timerEl.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                window.location.href = nextVideoUrl;
            }
        }, 1000);
    }
}

document.addEventListener('DOMContentLoaded', initVideoPlayerEnhancements);
