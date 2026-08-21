document.addEventListener('DOMContentLoaded', () => {
    const btn =
        document.getElementById('toggle-specs-btn');
    if (!btn) return;
    const hiddenItems =
        document.querySelectorAll(
            '.product-detail-product--hidden'
        );
    let expanded = false;
    btn.addEventListener('click', () => {
        expanded = !expanded;
        hiddenItems.forEach(product => {
            product.classList.toggle(
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
//     document
//         .querySelectorAll('[data-expandable-grid="true"]')
//         .forEach((grid) => {
//             }
//                 card.classList.add("grid-product-hidden");
//             });
//             }
//                         card.classList.remove("grid-product-hidden");
//                     });
//                 } else {
//                         card.classList.add("grid-product-hidden");
//                     });
//                         behavior: "smooth",
//                         block: "start",
//                     });
//                 }
//             });
//         });
// });
