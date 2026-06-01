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

function handleHeroSliderClick(e) {
    const sliderControl = e.target.closest(`
        .hero-slider__arrow--prev:not(.disabled),
        .hero-slider__arrow--next:not(.disabled),
        .hero-slider__dot:not(.active)
    `);

    if (!sliderControl) return false;

    handleHeroSliderControls(sliderControl);
    return true;

}