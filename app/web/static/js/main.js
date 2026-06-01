function handleGlobalClicks(e) {

    if (handleThemeClick(e)) return;

    if (handleGalleryClick(e)) return;

    if (handleHeroSliderClick(e)) return;

    if (handleInteractionClick(e)) return;

    if (handleAffiliateClickEvent(e)) return;

    if (handleCommentsClick(e)) return;

    if (handleFilterClick(e)) return;

    if (handleSearchClick(e)) return;

    if (handleFlashMessagesClick(e)) return;

    if (handleNavigationClick(e)) return;

    if (handleUserDropdown(e)) return;

    if (handleMobileMenu(e)) return;

    if (handleAuthClick(e)) return;

}


function handleGlobalSubmits(e) {
    if (handleCommentSubmit(e)) return;

    if (handleNewsletterSubmit(e)) return;

    if (handleContactSubmit(e)) return;
}

function handleGlobalChanges(e) {
    if (handleCountryChange(e)) return;

    if (handleSortChange(e)) return;
}
