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
function initGallery(e) {
  const gallery = e.target.closest(".item-gallery");
  if (!gallery) return;

  const thumbs = [...gallery.querySelectorAll(".item-gallery__thumb img")];
  if (!thumbs.length) return;

  const overlay = document.querySelector("[data-gallery-overlay]");
  if (!overlay) return;

  const displayImg = overlay.querySelector(".displayed-img");

  // collect image sources
  const images = thumbs.map(img => img.src);

  // store them on overlay
  overlay.dataset.images = JSON.stringify(images);
  overlay.dataset.index = "0";

  // show first image
  displayImg.src = images[0];

  // show overlay
  overlay.hidden = false;
}

function handleImageControls(control) {
  const overlay = document.querySelector(".item-gallery");
  if (!overlay) return;

  const displayImg = overlay.querySelector(".item-gallery__img");
  const currentImageIndex = displayImg.dataset.galleryMain;

  const newImageIndex = Number(control.dataset.galleryNewImage);

  const newImage = overlay.querySelector(`[data-gallery-thumb="${newImageIndex}"] img`);

  displayImg.src = newImage.src;
  displayImg.alt = newImage.alt;
  displayImg.dataset.galleryMain = newImageIndex;

  overlay.querySelector(`[data-gallery-index]`).textContent = newImageIndex;
  const galleryLength = overlay.querySelector(`[data-gallery-length]`).textContent;

  const navigationArrows = overlay.querySelectorAll('[data-gallery-new-image]');
  //   navigationArrows[0].dataset.galleryNewImage = 
  if (newImageIndex > currentImageIndex) {
    if (newImageIndex == galleryLength) control.classList.add('disabled');
    else control.dataset.galleryNewImage = newImageIndex + 1;
    navigationArrows[0].dataset.galleryNewImage = currentImageIndex;
    if (currentImageIndex == 1) navigationArrows[0].classList.remove('disabled');
  } else {
    if (newImageIndex == 1) control.classList.add('disabled');
    else control.dataset.galleryNewImage = newImageIndex - 1;
    navigationArrows[1].dataset.galleryNewImage = currentImageIndex;
    if (currentImageIndex == galleryLength) navigationArrows[1].classList.remove('disabled');
  }
}

function toggleActive(el) {
  el.classList.toggle("active", !el.classList.contains('active'));
}