/**
 * Catalog & Listing Sort Controller
 * Automatically attaches change handlers to desktop and mobile sort select elements.
 */
document.addEventListener('DOMContentLoaded', function () {
  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) {
    sortSelect.addEventListener('change', function () {
      if (this.value) {
        window.location.href = this.value;
      }
    });
  }

  const sortSelectMobile = document.getElementById('sort-select-mobile');
  if (sortSelectMobile) {
    sortSelectMobile.addEventListener('change', function () {
      if (this.value) {
        window.location.href = this.value;
      }
    });
  }
});
