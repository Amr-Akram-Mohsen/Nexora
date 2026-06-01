
async function handleCountryChange(e) {
    if (!e.target.classList.contains("country-toggle")) return false;

    const country = e.target.value || "";

    await fetch("/set-country", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ country })
    });

    // Optional: reload page to apply country filtering
    window.location.reload();
    return true;
}
