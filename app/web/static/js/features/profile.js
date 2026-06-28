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

  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

  document.querySelectorAll('.btn-rename-collection').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const oldName = e.currentTarget.dataset.collection;
      const newName = prompt(`Enter new name for collection "${oldName}":`, oldName);

      if (newName && newName !== oldName) {
        try {
          const res = await fetch("/collection/rename", {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
          });
          const data = await res.json();
          if (res.ok && data.success) {
            window.location.reload();
          } else {
            if (typeof showToast === 'function') {
              showToast(data.error || "Failed to rename collection.", 'error');
            } else {
              alert(data.error || "Failed to rename collection.");
            }
          }
        } catch (err) {
          console.error(err);
          if (typeof showToast === 'function') showToast('An error occurred.', 'error');
        }
      }
    });
  });

  document.querySelectorAll('.btn-delete-collection').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const collectionName = e.currentTarget.dataset.collection;
      if (confirm(`Are you sure you want to delete the collection "${collectionName}"? This will permanently remove the items from your saved list.`)) {
        try {
          const res = await fetch("/collection/delete", {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ collection_name: collectionName, move_to_global: false })
          });
          const data = await res.json();
          if (res.ok && data.success) {
            window.location.reload();
          } else {
            if (typeof showToast === 'function') {
              showToast(data.error || "Failed to delete collection.", 'error');
            } else {
              alert(data.error || "Failed to delete collection.");
            }
          }
        } catch (err) {
          console.error(err);
          if (typeof showToast === 'function') showToast('An error occurred.', 'error');
        }
      }
    });
  });
});
