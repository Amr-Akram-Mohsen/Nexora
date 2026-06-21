document.addEventListener("DOMContentLoaded", () => {
    fetchSourceStats();
});

function fetchSourceStats() {
    fetch("/admin/providers/sources/health_stats")
        .then(response => response.json())
        .then(data => {
            const elTotal = document.getElementById("stats-total-sources");
            const elActive = document.getElementById("stats-active-sources");
            const elHealthy = document.getElementById("stats-healthy");
            const elWarning = document.getElementById("stats-warning");
            const elFailed = document.getElementById("stats-failed");
            const elSilent = document.getElementById("stats-silent");

            if (elTotal) elTotal.textContent = data.total || 0;
            if (elActive) elActive.textContent = `${data.active || 0} active providers`;
            if (elHealthy) elHealthy.textContent = data.healthy || 0;
            if (elWarning) elWarning.textContent = data.warning || 0;
            if (elFailed) elFailed.textContent = data.failed || 0;
            if (elSilent) elSilent.textContent = data.silent || 0;
        })
        .catch(err => {
            console.error("Failed to fetch source stats:", err);
            // Replace spinners with dashes
            document.querySelectorAll(".dashboard-stat-value").forEach(el => {
                if (el.innerHTML.includes("fa-spin")) {
                    el.textContent = "-";
                }
            });
        });
}
