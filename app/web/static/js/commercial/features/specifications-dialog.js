
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
// document.addEventListener("DOMContentLoaded", () => {
//     const INITIAL_VISIBLE = 6;
//     document
//         .querySelectorAll('[data-expandable-grid="true"]')
//         .forEach((grid) => {
//             const cards = Array.from(grid.children);
//             if (cards.length <= INITIAL_VISIBLE) {
//                 return;
//             }
//             cards.slice(INITIAL_VISIBLE).forEach((card) => {
//                 card.classList.add("grid-item-hidden");
//             });
//             const section = grid.closest(".section");
//             const button = section?.querySelector("[data-section-toggle]");
//             if (!button) {
//                 return;
//             }
//             button.hidden = false;
//             button.addEventListener("click", () => {
//                 const expanded =
//                     button.getAttribute("data-expanded") === "true";
//                 if (!expanded) {
//                     cards.forEach((card) => {
//                         card.classList.remove("grid-item-hidden");
//                     });
//                     button.querySelector("span").textContent = "Show Less";
//                     button.querySelector("i").classList.replace("fa-arrow-down", "fa-arrow-up");
//                     button.setAttribute("data-expanded", "true");
//                 } else {
//                     cards.slice(INITIAL_VISIBLE).forEach((card) => {
//                         card.classList.add("grid-item-hidden");
//                     });
//                     button.querySelector("span").textContent = "Show More";
//                     button.querySelector("i").classList.replace("fa-arrow-up", "fa-arrow-down");
//                     button.setAttribute("data-expanded", "false");
//                     section.scrollIntoView({
//                         behavior: "smooth",
//                         block: "start",
//                     });
//                 }
//             });
//         });
// });
