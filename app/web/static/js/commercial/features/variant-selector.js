const VariantSelector = {
    data: [],
    selected: {},
    init() {
        const raw =
            document.getElementById(
                "variant-data"
            )
        if (!raw)
            return
        this.data =
            JSON.parse(
                raw.textContent
            )
        this.attachEvents()
        this.selectDefault()
    },
    attachEvents() {
        document
            .querySelectorAll(
                ".variant-option"
            )
            .forEach(
                button => {
                    button.addEventListener(
                        "click",
                        () => {
                            this.handleSelection(
                                button
                            )
                        }
                    )
                }
            )
    },
    handleSelection(button) {
        const attr =
            button.dataset.attribute
        const value =
            button.dataset.value
        this.selected[attr] =
            value
        const group =
            button.closest(
                ".variant-group"
            )
        group
            .querySelectorAll(
                ".variant-option"
            )
            .forEach(
                b => b.classList.remove(
                    "active"
                )
            )
        button.classList.add(
            "active"
        )
        this.update()
    },
    selectDefault() {
        document
            .querySelectorAll(
                ".variant-group"
            )
            .forEach(
                group => {
                    const first =
                        group.querySelector(
                            ".variant-option"
                        )
                    if (first) {
                        first.click()
                    }
                }
            )
    },
    update() {
        const variant =
            this.findVariant()
        if (
            !variant
        ) {
            return
        }
        // Sync selected values to attribute headers in the DOM
        Object.entries(this.selected).forEach(([attr, value]) => {
            const labelEl = document.querySelector(`[data-selected-for="${attr}"]`);
            if (labelEl) {
                labelEl.textContent = value;
            }
        });
        Gallery.update(
            variant.images
        )
        PurchaseOptions.update(
            variant
        )
        this.updateAvailability()
    },
    findVariant() {
        return this.data.find(
            variant => {
                return Object
                    .entries(
                        this.selected
                    )
                    .every(
                        ([key, value]) => {
                            return (
                                variant
                                    .attributes[key]
                                ===
                                value
                            )
                        }
                    )
            }
        )
    },
    updateAvailability() {
        document
            .querySelectorAll(
                ".variant-option"
            )
            .forEach(
                button => {
                    const attr =
                        button.dataset.attribute
                    const value =
                        button.dataset.value
                    const selection = {
                        ...this.selected,
                        [attr]: value
                    }
                    const valid =
                        this.data.some(
                            variant => {
                                return Object
                                    .entries(
                                        selection
                                    )
                                    .every(
                                        ([k, v]) => {
                                            return (
                                                variant
                                                    .attributes[k]
                                                ===
                                                v
                                            )
                                        }
                                    )
                            }
                        )
                    button.disabled =
                        !valid
                }
            )
    }
}
