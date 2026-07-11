function handleImageControls(control) {
    const gallery = control.closest(".product-gallery");
    if (!gallery) return;
    const displayImg = gallery.querySelector("[data-gallery-main]");
    if (!displayImg) return;
    const thumbnails = [...gallery.querySelectorAll("[data-gallery-thumb]")];
    const galleryLength = thumbnails.length;
    let newIndex = parseInt(control.dataset.galleryNewImage || control.dataset.galleryThumb);
    if (isNaN(newIndex) || newIndex < 1 || newIndex > galleryLength) return;
    // Find the thumbnail for the new index
    const newThumb = gallery.querySelector(`[data-gallery-thumb="${newIndex}"] img`);
    if (!newThumb) return;
    // 1. Update Main Display
    displayImg.src = newThumb.src;
    displayImg.alt = newThumb.alt;
    displayImg.dataset.galleryMain = newIndex;
    // 2. Update Index Counter
    const indexEl = gallery.querySelector(`[data-gallery-index]`);
    if (indexEl) indexEl.textContent = newIndex;
    // 3. Update Sync Arrows
    const prevBtn = gallery.querySelector(".product-gallery__nav--prev");
    const nextBtn = gallery.querySelector(".product-gallery__nav--next");
    if (prevBtn) {
        prevBtn.dataset.galleryNewImage = newIndex - 1;
        prevBtn.classList.toggle("disabled", newIndex === 1);
        prevBtn.disabled = newIndex === 1;
    }
    if (nextBtn) {
        nextBtn.dataset.galleryNewImage = newIndex + 1;
        nextBtn.classList.toggle("disabled", newIndex === galleryLength);
        nextBtn.disabled = newIndex === galleryLength;
    }
    // 4. Update active class on thumbnails
    thumbnails.forEach((thumb, idx) => {
        thumb.classList.toggle("is-active", idx + 1 === newIndex);
    });
}
function navigateGallery(direction) {
    const overlay = document.querySelector("[data-gallery-overlay]");
    if (!overlay || overlay.hidden) return;
    const images = JSON.parse(overlay.dataset.images || "[]");
    if (!images.length) return;
    let currentIndex = parseInt(overlay.dataset.index || "0");
    let nextIndex = currentIndex + direction;
    // Cycle around
    if (nextIndex < 0) nextIndex = images.length - 1;
    if (nextIndex >= images.length) nextIndex = 0;
    overlay.dataset.index = nextIndex;
    const displayImg = overlay.querySelector(".displayed-img");
    displayImg.src = images[nextIndex];
    const currentEl = overlay.querySelector(".current");
    if (currentEl) currentEl.textContent = nextIndex + 1;
    const totalEl = overlay.querySelector(".total");
    if (totalEl) totalEl.textContent = images.length;
}
function initGallery(e) {
    const gallery = e.target.closest(".product-gallery");
    if (!gallery) return;
    const thumbs = [...gallery.querySelectorAll("[data-gallery-thumb] img")];
    if (!thumbs.length) return;
    const overlay = document.querySelector("[data-gallery-overlay]");
    if (!overlay) return;
    const images = thumbs.map(img => img.src);
    overlay.dataset.images = JSON.stringify(images);
    // Sync zoom overlay index with currently displayed image in gallery
    const displayImg = gallery.querySelector("[data-gallery-main]");
    const activeIndex = displayImg ? (parseInt(displayImg.dataset.galleryMain || "1") - 1) : 0;
    overlay.dataset.index = activeIndex;
    const overlayImg = overlay.querySelector(".displayed-img");
    if (overlayImg) overlayImg.src = images[activeIndex];
    const currentEl = overlay.querySelector(".current");
    if (currentEl) currentEl.textContent = activeIndex + 1;
    const totalEl = overlay.querySelector(".total");
    if (totalEl) totalEl.textContent = images.length;
    overlay.hidden = false;
}
function closeOverlay() {
    const gallery = document.querySelector("[data-gallery-overlay]");
    if (gallery) gallery.hidden = true;
}
const Gallery = {
    init() { },
    update(images = []) {
        const gallery =
            document.querySelector(
                ".product-gallery"
            )
        if (
            !gallery ||
            !images ||
            !images.length
        ) {
            return
        }
        const displayImg =
            gallery.querySelector(
                "[data-gallery-main]"
            )
        if (!displayImg) {
            return
        }
        const thumbnails = [...gallery.querySelectorAll("[data-gallery-thumb]")]
        let matchedThumb = null;
        // Search for the first image URL that has a matching static thumbnail
        for (const url of images) {
            const match = thumbnails.find(thumb => {
                const img = thumb.querySelector("img");
                if (!img) return false;
                const thumbUrl = img.src;
                try {
                    const thumbPath = new URL(thumbUrl, window.location.origin).pathname;
                    const varPath = new URL(url, window.location.origin).pathname;
                    return thumbPath === varPath;
                } catch (e) {
                    return thumbUrl.includes(url) || url.includes(thumbUrl);
                }
            });
            if (match) {
                matchedThumb = match;
                break;
            }
        }
        if (matchedThumb) {
            // Programmatically click the matched thumbnail to trigger transitions naturally,
            // which updates index counters, navigation arrows, and highlights cleanly.
            matchedThumb.click();
        } else {
            // Fallback: update main view directly if no thumbnail is found
            displayImg.src = images[0];
            thumbnails.forEach(t => t.classList.remove("is-active"));
            const indexEl = gallery.querySelector("[data-gallery-index]");
            if (indexEl) {
                indexEl.textContent = "—";
            }
        }
    }
}

function handleGalleryClick(e) {
    // ---------- Gallery open / close / arrow clicks ----------
    const galleryOverlay = document.querySelector("[data-gallery-overlay]");
    const openGalleryBtn = e.target.closest("[data-gallery-open]");
    if (openGalleryBtn) {
        initGallery(e);
        return true;
    }
    const galleryClose = e.target.closest("[data-gallery-close]");
    if (galleryClose) {
        if (galleryOverlay) galleryOverlay.hidden = true;
        return true;
    }
    const imageControl = e.target.closest(".product-gallery__nav, .product-gallery__thumb");
    if (imageControl) {
        handleImageControls(imageControl);
        return true;
    }
    // Gallery Overlay Navigation
    const galleryPrev = e.target.closest('[data-gallery-prev]');
    if (galleryPrev) {
        navigateGallery(-1);
        return true;
    }
    const galleryNext = e.target.closest('[data-gallery-next]');
    if (galleryNext) {
        navigateGallery(1);
        return true;
    }

    return false;

}