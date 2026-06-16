function showToast(msg, type = "success") {
  const toast = document.getElementById("settings-toast");
  if (!toast) return;

  toast.textContent = msg;
  toast.className = `settings-toast settings-toast-${type} settings-toast-show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove("settings-toast-show");
  }, 3200);
}
