const PurchaseOptions = {
    init() { },
    update(variant) {
        const container =
            document.querySelector(
                ".item-buy-links__items"
            )
        if (
            !container ||
            !variant
        ) {
            return
        }
        container.innerHTML = ""
        variant.store_links
            .forEach(link => {
                container
                    .insertAdjacentHTML(
                        "beforeend",
                        `
<a
href="${link.url}"
target="_blank"
rel="noopener noreferrer"
class="link item-buy-link flex items-center justify-between"
>
<div class="item-buy-link__info flex flex-col">
<div class="item-buy-link__store flex items-center">
${link.logo
                            ?
                            `<img
src="${link.logo}"
class="store-logo"
loading="lazy"
width="24"
height="24"
>`
                            :
                            ""
                        }
${link.name}
</div>
${link.price
                            ?
                            `
<div class="item-buy-link__price">
${link.currency}
${link.price}
</div>
`
                            :
                            ""
                        }
</div>
<span class="item-buy-link__icon">
<i class="fas fa-external-link-alt"></i>
</span>
</a>
`
                    )
            })
    }
}