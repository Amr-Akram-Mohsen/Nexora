const { isAuthenticated, userEmail } = window.APP;


// General Message
function showInlineTooltip(targetEl, message, duration = 2000) {
    const msg = document.getElementById("inline-tooltip");
    if (!msg || !targetEl) return;
    msg.textContent = message;
    msg.classList.remove("is-hidden");
    msg.style.display = "block";

    const rect = targetEl.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

    const msgHeight = msg.offsetHeight;

    msg.style.top = `${rect.top + scrollTop - msgHeight - 8}px`; // tooltip above element
    msg.style.left = `${rect.left + scrollLeft}px`;
    
    // msg.style.top = `${rect.top + scrollTop - rect.height - 8}px`;
    // msg.style.left = `${rect.left + scrollLeft}px`;

    clearTimeout(msg._timeout);
    msg._timeout = setTimeout(() => {
        msg.classList.add("is-hidden");
        msg.style.display = "none";
    }, duration);
}

// General Checking Authentication Function Used For Interactions Allownce
function ensureAuthenticated(event, btn, message){
        if (!isAuthenticated) {
            event.preventDefault();
            showInlineTooltip(btn, message);
            return false;
        }
        return true;
}
