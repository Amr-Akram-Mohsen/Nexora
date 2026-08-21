document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("scraping-form");
    const triggerBtn = document.getElementById("trigger-btn");
    const statusContainer = document.getElementById("task-status-container");
    const resultsContainer = document.getElementById("scraping-results-container");
    const statsContainer = document.getElementById("scraping-stats");
    const detailsContainer = document.getElementById("scraping-details");

    const taskName = document.getElementById("task-name");
    const taskStatus = document.getElementById("task-status");
    const taskProgressFill = document.getElementById("task-progress-fill");
    const taskMeta = document.getElementById("task-meta");

    const statTemplate = document.getElementById("stat-card-template");
    const detailTemplate = document.getElementById("detail-row-template");

    let currentTaskId = null;
    let pollInterval = null;

    form.addEventListener("submit", (e) => {
        e.preventDefault();

        const limit = document.getElementById("scraping-limit").value;
        const btnText = triggerBtn.querySelector('.btn-text');

        btnText.textContent = "Starting...";
        triggerBtn.disabled = true;

        fetch("/admin/scraping/api/run", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || ""
            },
            body: JSON.stringify({ limit: limit })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "started" && data.task_id) {
                currentTaskId = data.task_id;
                statusContainer.classList.remove("scraping-hidden");
                resultsContainer.classList.add("scraping-hidden");
                statsContainer.innerHTML = "";
                detailsContainer.innerHTML = "";

                pollInterval = setInterval(pollTaskStatus, 2000);
            }
        })
        .catch(err => {
            console.error(err);
            btnText.textContent = "Start Scraping Batch";
            triggerBtn.disabled = false;
        });
    });

    function pollTaskStatus() {
        if (!currentTaskId) return;

        fetch(`/admin/scraping/api/task/${currentTaskId}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    clearInterval(pollInterval);
                    resetButton();
                    return;
                }

                taskName.textContent = data.name || "Scraping Batch";
                taskStatus.textContent = data.status;
                taskStatus.className = `task-status-badge status-${data.status}`;

                if (data.progress) {
                    taskProgressFill.style.width = `${data.progress}%`;
                }

                if (data.error) {
                    taskMeta.textContent = `Error: ${data.error}`;
                    taskMeta.style.color = "var(--brand-red)";
                } else {
                    taskMeta.textContent = data.description || "";
                    taskMeta.style.color = "";
                }

                if (data.status === "completed" || data.status === "failed") {
                    clearInterval(pollInterval);
                    resetButton();

                    if (data.status === "completed" && data.result) {
                        renderResults(data.result);
                    }
                }
            })
            .catch(err => {
                console.error("Polling error", err);
                clearInterval(pollInterval);
                resetButton();
            });
    }

    function renderResults(result) {
        resultsContainer.classList.remove("scraping-hidden");
        statsContainer.innerHTML = "";
        detailsContainer.innerHTML = "";

        const stats = [
            { label: "Processed", value: result.processed },
            { label: "Published", value: result.published },
            { label: "Network/API Fail", value: result.failed_network },
            { label: "Failed (Too Short)", value: result.failed_quality_length },
            { label: "Failed (No Media)", value: result.failed_quality_media },
            { label: "Failed (Other)", value: result.failed_other }
        ];

        stats.forEach(stat => {
            const clone = statTemplate.content.cloneNode(true);
            clone.querySelector('.stat-label').textContent = stat.label;
            clone.querySelector('.stat-value').textContent = stat.value;
            statsContainer.appendChild(clone);
        });

        if (result.details && result.details.length > 0) {
            result.details.forEach(item => {
                const clone = detailTemplate.content.cloneNode(true);
                const icon = clone.querySelector('.detail-icon');
                const title = clone.querySelector('.detail-title');
                const meta = clone.querySelector('.detail-meta');

                title.textContent = item.title || item.url || "Unknown Item";

                if (item.status === "success") {
                    icon.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
                    icon.classList.add("success");
                    meta.textContent = "Scraped and Published";
                } else {
                    icon.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
                    icon.classList.add("failed");
                    meta.textContent = `Failed: ${item.reason}`;
                }

                detailsContainer.appendChild(clone);
            });
        }
    }

    function resetButton() {
        const btnText = triggerBtn.querySelector('.btn-text');
        btnText.textContent = "Start Scraping Batch";
        triggerBtn.disabled = false;
    }
});
