
async function handleAffiliateClick(li) {
    if (li.classList.contains("is-loading")) return;

    li.classList.add("is-loading");

    const linkId = li.dataset.linkId;

    try {
        const res = await fetch(`/item-click/${linkId}`, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        if (!res.ok) throw new Error("Tracking failed");

        const data = await res.json();

        if (data.redirect_url) {
            window.open(data.redirect_url, "_blank", "noopener,noreferrer");
        }
    } catch (err) {
        console.error("Affiliate redirect failed:", err);
        alert("Unable to open store right now. Please try again.");
    } finally {
        li.classList.remove("is-loading");
    }
}

function handleAffiliateClickEvent(e) {
    const itemBuyBtn = e.target.closest(".item-buy-link");
    if (!itemBuyBtn) return false;
    e.preventDefault();
    handleAffiliateClick(itemBuyBtn);
    return true;
}