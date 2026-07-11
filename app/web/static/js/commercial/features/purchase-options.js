const PurchaseOptions = {
    init() { },
    update(variant) {
        const container =
            document.querySelector(
                ".product-buy-links__items"
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
class="link product-buy-link flex products-center justify-between"
>
<div class="product-buy-link__info flex flex-col">
<div class="product-buy-link__store flex products-center">
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
<div class="product-buy-link__price">
${link.currency}
${link.price}
</div>
`
                            :
                            ""
                        }
</div>
<span class="product-buy-link__icon">
<i class="fas fa-external-link-alt"></i>
</span>
</a>
`
                    )
            })
    }
}