document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('delete-account-modal');
  if (modal) {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          if (modal.classList.contains('active')) {
            modal.style.display = 'flex';
          } else {
            modal.style.display = 'none';
          }
        }
      });
    });
    observer.observe(modal, { attributes: true });
  }
});

function handleProfileClick(e) {
  const renameBtn = e.target.closest('.btn-rename-collection, [data-action="rename-collection"]');
  if (renameBtn) {
    const oldName = renameBtn.dataset.collection;
    const newName = prompt(`Enter new name for collection "${oldName}":`, oldName);

    if (newName && newName !== oldName) {
      const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || document.querySelector('meta[name="csrf-token"]')?.content;
      const endpoint = window.APP?.urls?.renameCollection || "/collection/rename";
      fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ old_name: oldName, new_name: newName })
      })
      .then(res => res.json().then(data => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (ok && data.success) {
          window.location.reload();
        } else {
          if (typeof showToast === 'function') {
            showToast(data.error || "Failed to rename collection.", 'error');
          } else {
            alert(data.error || "Failed to rename collection.");
          }
        }
      })
      .catch(err => {
        console.error(err);
        if (typeof showToast === 'function') showToast('An error occurred.', 'error');
      });
    }
    return true;
  }

  const deleteBtn = e.target.closest('.btn-delete-collection, [data-action="delete-collection"]');
  if (deleteBtn) {
    const collectionName = deleteBtn.dataset.collection;
    if (confirm(`Are you sure you want to delete the collection "${collectionName}"? This will permanently remove the products from your saved list.`)) {
      const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || document.querySelector('meta[name="csrf-token"]')?.content;
      const endpoint = window.APP?.urls?.deleteCollection || "/collection/delete";
      fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ collection_name: collectionName, move_to_global: false })
      })
      .then(res => res.json().then(data => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (ok && data.success) {
          window.location.reload();
        } else {
          if (typeof showToast === 'function') {
            showToast(data.error || "Failed to delete collection.", 'error');
          } else {
            alert(data.error || "Failed to delete collection.");
          }
        }
      })
      .catch(err => {
        console.error(err);
        if (typeof showToast === 'function') showToast('An error occurred.', 'error');
      });
    }
    return true;
  }

  return false;
}
