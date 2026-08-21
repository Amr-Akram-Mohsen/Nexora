function togglePasswordVisibility(btn) {
    const wrapper = btn.closest(".password-wrapper");
    const input = wrapper?.querySelector("input");
    if (!input) return;

    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";

    const icon = btn.querySelector("i");
    if (icon) {
        icon.classList.toggle("fa-eye", !isHidden);
        icon.classList.toggle("fa-eye-slash", isHidden);
    }
    btn.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
}

function initPasswordToggles() {
    // Retained as a no-op for backward compatibility since handlePasswordClick handles this via delegation
}

function getPasswordStrength(pwd) {
    if (!pwd || pwd.length < 8) return "weak";

    let score = 0;
    if (/[a-z]/.test(pwd)) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/\d/.test(pwd)) score++;
    if (/[^a-zA-Z0-9]/.test(pwd)) score++;
    if (pwd.length >= 12) score++;
    if (pwd.length >= 16) score++;

    if (score <= 1) return "weak";
    if (score === 2) return "fair";
    if (score === 3) return "good";
    return "strong";
}

const STRENGTH_SEGMENTS = { weak: 1, fair: 2, good: 3, strong: 4 };

function updateStrengthMeter(strength) {
    const bar = document.querySelector(".password-strength-bar");
    const label = document.querySelector(".password-strength-label");
    if (!bar || !label) return;

    const filled = STRENGTH_SEGMENTS[strength] || 0;
    bar.querySelectorAll(".strength-segment").forEach((seg, i) => {
        seg.classList.toggle("active", i < filled);
        // Reset all color classes then set the current one
        seg.classList.remove("weak", "fair", "good", "strong");
        if (i < filled) seg.classList.add(strength);
    });

    label.textContent = strength.charAt(0).toUpperCase() + strength.slice(1);
    label.className = `password-strength-label ${strength}`;
}

function initPasswordStrength() {
    const pwdInput = document.getElementById("password");
    const meter = document.querySelector(".password-strength");
    if (!pwdInput || !meter) return;

    pwdInput.addEventListener("input", () => {
        const val = pwdInput.value;
        const strength = getPasswordStrength(val);
        meter.style.display = val.length > 0 ? "block" : "none";
        updateStrengthMeter(strength);
    });

    meter.style.display = "none";
}

function initConfirmMatch() {
    const pwdInput = document.getElementById("password");
    const confirmInput = document.getElementById("confirm_password");
    const indicator = document.querySelector(".confirm-match");
    if (!pwdInput || !confirmInput || !indicator) return;

    function checkMatch() {
        const confirmVal = confirmInput.value;
        if (!confirmVal) {
            indicator.classList.remove("visible", "match", "no-match");
            return;
        }
        const match = pwdInput.value === confirmVal;
        indicator.classList.add("visible");
        indicator.classList.toggle("match", match);
        indicator.classList.toggle("no-match", !match);
        indicator.textContent = match ? "✓ Passwords match" : "✗ Passwords do not match";
    }

    confirmInput.addEventListener("input", checkMatch);
    pwdInput.addEventListener("input", checkMatch);
}

function togglePasswordForm() {
    const collapsible = document.getElementById('password-collapsible');
    const arrow = document.getElementById('accordion-arrow') || document.querySelector('#password-toggle-btn i');
    const btn = document.getElementById('password-toggle-btn');
    if (!collapsible) return;

    const isCollapsed = collapsible.classList.toggle('collapsed');
    arrow?.classList.toggle('is-open', !isCollapsed);
    btn?.classList.toggle('active', !isCollapsed);
}

function handlePasswordClick(e) {
    const toggleBtn = e.target.closest('[data-action="toggle-password-form"]');
    if (toggleBtn) {
        togglePasswordForm();
        return true;
    }

    const pwdToggle = e.target.closest('.password-toggle, [data-action="toggle-password"]');
    if (pwdToggle) {
        togglePasswordVisibility(pwdToggle);
        return true;
    }

    return false;
}

async function handleProfileFormSubmit(e) {
    const form = e.target.closest('.ajax-form, .profile-form');
    if (!form) return false;

    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    if (btn) btn.classList.add('is-loading');

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const result = await response.json();
        if (result.success) {
            window.location.reload();
        } else {
            alert(result.error || "Update failed");
        }
    } catch (err) {
        console.error(err);
    } finally {
        if (btn) btn.classList.remove('is-loading');
    }
    return true;
}

function initProfileForms() {
    // Retained for backward compatibility since handleProfileFormSubmit handles this via global submit delegation
}
