function handleNavigationClick(e) {
    const mainSectionLink = e.target.closest('.section-link');
    if (!mainSectionLink) return false;
    toggleActive(mainSectionLink)
    return true;
}

function handleUserDropdown(e) {
    const user = e.target.closest(".nav-user");
    if (!user) return false;
    document.querySelectorAll(".nav-user")
        .forEach(el => {
            if (el !== user) el.classList.remove("active");
        });

    if (user) {
        user.classList.toggle("active");
    }
    return true;

}

function handleMobileMenu(e) {
    const mobileMenuToggle = e.target.closest('.mobile-menu-toggle');
    if (!mobileMenuToggle) return false;
    const mobileNav = document.querySelector('.mobile-nav');
    mobileNav.classList.toggle('active');
    mobileMenuToggle.querySelector('i').classList.toggle('fa-bars');
    mobileMenuToggle.querySelector('i').classList.toggle('fa-times');
    return true;
}

// Header scroll effect & Back to Top
function initHeaderScroll() {
    const header = document.querySelector('.site-header');
    const backToTopBtn = document.getElementById('back-to-top');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            if (header) header.classList.add('site-header--scrolled');
        } else {
            if (header) header.classList.remove('site-header--scrolled');
        }

        if (backToTopBtn) {
            if (window.scrollY > 300) {
                backToTopBtn.classList.remove('is-hidden');
            } else {
                backToTopBtn.classList.add('is-hidden');
            }
        }
    });

    if (backToTopBtn) {
        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
}
