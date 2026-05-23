// Sliders Actions
function initHeroSlider() {

  const prev = document.querySelector(".hero-slider__arrow--prev");
  const next = document.querySelector(".hero-slider__arrow--next");

  if (prev) {
    prev.classList.add("disabled");
    prev.dataset.slidePrev = -1;
  }

  if (next) {
    next.dataset.slideNext = 1;
  }

  document.querySelector(".hero-slider__dot")?.classList.add("active");
}


function handleHeroSliderControls(control) {
  let slideIndex = -1;

  if (control.classList.contains("hero-slider__arrow--prev"))
    slideIndex = Number(control.dataset.slidePrev);

  else if (control.hasAttribute("data-slide"))
    slideIndex = Number(control.dataset.slide);

  else if (control.classList.contains("hero-slider__arrow--next"))
    slideIndex = Number(control.dataset.slideNext);

  if (slideIndex === -1) return;

  const slides = document.querySelectorAll(".hero-slide");
  const dots = document.querySelectorAll(".hero-slider__dot");
  const track = document.querySelector(".hero-slider__track");

  const lastIndex = slides.length - 1;

  /* move slider */
  track.style.transform = `translateX(-${slideIndex * 100}%)`;

  /* update dots */
  document.querySelector(".hero-slider__dot.active")?.classList.remove("active");
  dots[slideIndex]?.classList.add("active");

  const controls = control.closest(".hero-slider__wrapper");
  const prev = controls?.querySelector(".hero-slider__arrow--prev");
  const next = controls?.querySelector(".hero-slider__arrow--next");

  if (prev) {
    prev.classList.toggle("disabled", slideIndex === 0);
    prev.dataset.slidePrev = slideIndex - 1;
  }

  if (next) {
    next.classList.toggle("disabled", slideIndex === lastIndex);
    next.dataset.slideNext = slideIndex + 1;
  }
}



// // Mode Actions
// function applyMode() {
//     const btn = document.querySelector('.mode-toggle');
//     const icon = btn?.querySelector('i');
//     // sync early-applied class to body
//     if (document.documentElement.classList.contains('dark-mode')) {
//       document.body.classList.add('dark-mode');
//     }
//     // sync icon on load
//     if (document.body.classList.contains('dark-mode')) {
//       icon?.classList.replace('fa-sun', 'fa-moon');
//     }
// }

// function handleModeToggle(e) {
//     const icon = e?.querySelector('i');
//     const isDark = document.body.classList.contains('dark-mode');
//     icon?.classList.toggle('fa-moon', isDark);
//     icon?.classList.toggle('fa-sun', !isDark);
//     localStorage.setItem('theme', isDark ? 'dark' : 'light');
// }

function initTheme() {
  const saved = localStorage.getItem('theme');
  const isDark = saved === 'dark';
  document.documentElement.classList.toggle('dark-mode', isDark);
  document.documentElement.classList.toggle('light-mode', !isDark);

  // if (saved === 'dark') {
  //   document.documentElement.classList.add('dark-mode');
  // } else {
  //   document.documentElement.classList.add('light-mode');
  // }
  // applyMode();
  syncModeUI();
}

function syncModeUI() {
  const btn = document.querySelector('.mode-toggle');
  const icon = btn?.querySelector('i');

  const isDark = document.body.classList.contains('dark-mode');

  icon?.classList.toggle('fa-moon', !isDark);
  icon?.classList.toggle('fa-sun', isDark);
}

function applyMode() {
  // sync body with html
  if (document.documentElement.classList.contains('dark-mode')) {
    document.body.classList.replace('light-mode', 'dark-mode');
  } else {
    document.body.classList.replace('dark-mode', 'light-mode');
  }

  syncModeUI();
}
function handleModeToggle() {
  const isDark = document.body.classList.contains('dark-mode');
  const nextIsDark = !isDark;

  document.body.classList.toggle('dark-mode', nextIsDark);
  document.body.classList.toggle('light-mode', !nextIsDark);

  localStorage.setItem('theme', nextIsDark ? 'dark' : 'light');

  syncModeUI();
}


// Review Dropdown List Actions

function handleReviewsToggle() {
  const dropdownMenu = document.querySelector('.reviews__dropdown-menu');
  const isShown = !dropdownMenu.classList.contains('is-hidden');
  dropdownMenu.classList.toggle('is-hidden', isShown);
}

function closeOverlay() {
  const specs = document.querySelector(".item-details-dialog");
  if (specs) specs.classList.remove("is-open");

  const gallery = document.querySelector("[data-gallery-overlay]");
  if (gallery) gallery.hidden = true;
}

function toggleActive(el) {
  el.classList.toggle("active", !el.classList.contains('active'));
}


function handleImageControls(control) {
  const gallery = control.closest(".item-gallery");
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
  const prevBtn = gallery.querySelector(".item-gallery__nav--prev");
  const nextBtn = gallery.querySelector(".item-gallery__nav--next");

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
  const gallery = e.target.closest(".item-gallery");
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

// function selectVariant(btn) {
//   const group = btn.closest('.variant-group__options');
//   if (!group) return;
//   group.querySelectorAll('.variant-option').forEach(el => el.classList.remove('active'));
//   btn.classList.add('active');

//   const variantImgUrl = btn.dataset.variantImage;
//   const colorAttr = btn.closest('.variant-group')?.querySelector('.variant-group__label')?.textContent?.trim()?.toLowerCase();
//   const isColor = colorAttr === 'color' || colorAttr === 'finish';

//   if (variantImgUrl) {
//     const gallery = document.querySelector(".item-gallery");
//     if (gallery) {
//       const thumbnails = [...gallery.querySelectorAll("[data-gallery-thumb]")];
//       const match = thumbnails.find(thumb => {
//         const img = thumb.querySelector("img");
//         return img && img.src === variantImgUrl;
//       });
//       if (match) {
//         match.click(); // Cleanest: click the matching thumbnail to sync everything
//       } else {
//         // Fallback: directly update display if image not in thumbnails
//         const displayImg = gallery.querySelector("[data-gallery-main]");
//         if (displayImg) {
//           displayImg.src = variantImgUrl;
//           displayImg.dataset.galleryMain = "0";
//           thumbnails.forEach(t => t.classList.remove("is-active"));
//         }
//       }
//     }
//   } else if (isColor) {
//     const colorName = btn.title || btn.textContent.trim();
//     if (colorName) {
//       const gallery = document.querySelector(".item-gallery");
//       if (gallery) {
//         const thumbnails = [...gallery.querySelectorAll("[data-gallery-thumb]")];
//         const match = thumbnails.find(thumb => {
//           const img = thumb.querySelector("img");
//           const srcMatch = img && img.src.toLowerCase().includes(colorName.toLowerCase().replace(/[^a-z0-9]/g, ''));
//           const altMatch = img && img.alt.toLowerCase().includes(colorName.toLowerCase());
//           return srcMatch || altMatch;
//         });
//         if (match) {
//           match.click();
//         }
//       }
//     }
//   }
// }

// function toggleInlineSpecs() {
//   const container = document.getElementById('hidden-details-container');
//   const btn = document.getElementById('toggle-specs-btn');
//   if (!container || !btn) return;

//   const isOpen = container.classList.contains('is-open');
//   if (isOpen) {
//     container.classList.remove('is-open');
//     btn.textContent = 'Show More';
//   } else {
//     container.classList.add('is-open');
//     btn.textContent = 'Show Less';
//   }
// }

document.addEventListener('DOMContentLoaded', () => {

  const btn =
    document.getElementById('toggle-specs-btn');

  if (!btn) return;

  const hiddenItems =
    document.querySelectorAll(
      '.item-detail-item--hidden'
    );

  let expanded = false;

  btn.addEventListener('click', () => {

    expanded = !expanded;

    hiddenItems.forEach(item => {
      item.classList.toggle(
        'is-visible',
        expanded
      );
    });

    btn.textContent =
      expanded
        ? 'Show Less'
        : 'Show More';

  });

});