(function () {
  'use strict';

  let subscribersController = null;

  document.addEventListener("DOMContentLoaded", () => {
    subscribersController = new AdminListController({
      domain: "subscribers",
      endpoint: "/admin/subscribers/",
      rowsEndpoint: "/admin/subscribers/rows",
      filterIds: [
        "subscriber-status-filter",
        "subscriber-user-filter"
      ],
      defaultPerPage: 25,
      colspan: 6,
      autoInit: true,
      onLoaded: function(data) {
        if (data.headers) {
          const total = data.headers.get("X-Total");
          const confirmed = data.headers.get("X-Confirmed");
          const unconfirmed = data.headers.get("X-Unconfirmed");
          const unsubscribed = data.headers.get("X-Unsubscribed");
          const anonymous = data.headers.get("X-Anonymous");

          if (total !== null) document.getElementById("funnel-total").textContent = parseInt(total).toLocaleString();
          if (confirmed !== null) {
              document.getElementById("funnel-confirmed").textContent = parseInt(confirmed).toLocaleString();
              document.getElementById("summary-confirmed-count").textContent = `Confirmed: ${parseInt(confirmed).toLocaleString()}`;
          }
          if (unconfirmed !== null) document.getElementById("funnel-unconfirmed").textContent = parseInt(unconfirmed).toLocaleString();
          if (unsubscribed !== null) document.getElementById("funnel-unsubscribed").textContent = parseInt(unsubscribed).toLocaleString();

          if (anonymous !== null) {
              document.getElementById("funnel-anonymous").textContent = parseInt(anonymous).toLocaleString();
              document.getElementById("summary-anonymous-count").textContent = `Anonymous: ${parseInt(anonymous).toLocaleString()}`;
          }
        }
      }
    });

    document.body.addEventListener("click", e => {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;
      const { action, id } = btn.dataset;
      const subId = parseInt(id, 10);

      if (action === "delete-subscriber") {
        showModal(
          "Delete Subscriber",
          `Are you sure you want to permanently delete this subscriber?`,
          () => {
            btn.disabled = true;
            btn.textContent = "Deleting…";
            fetch(`/admin/subscribers/${subId}`, { method: "DELETE" })
              .then(res => { if (!res.ok) throw new Error(); return res.json(); })
              .then(() => {
                showToast(`Subscriber has been removed.`);
                if (subscribersController) {
                  subscribersController.load(subscribersController.currentPage);
                }
              })
              .catch(() => {
                showToast("Failed to delete subscriber.", "error");
                btn.disabled = false;
              });
          }
        );
      }
    });
  });
})();
