document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("ingestion-form");
    const triggerBtn = document.getElementById("trigger-btn");
    const statusContainer = document.getElementById("task-status-container");
    const statusText = document.getElementById("task-status-text");
    const resultContainer = document.getElementById("task-result-container");
    const helpersContainer = document.getElementById("cache-helpers-container");

    let activePollingInterval = null;

    // Fetch Cache Helpers
    function fetchHelpers() {
        fetch("/admin/ingestions/api/helpers")
            .then(res => res.json())
            .then(data => {
                helpersContainer.innerHTML = "";
                const template = document.getElementById("cache-helpers-template");
                const clone = template.content.cloneNode(true);
                clone.querySelector(".cache-helpers-view").textContent = JSON.stringify(data, null, 2);
                helpersContainer.appendChild(clone);
            })
            .catch(err => {
                helpersContainer.innerHTML = "";
                const msgTemplate = document.getElementById("result-message-template");
                const clone = msgTemplate.content.cloneNode(true);
                const p = clone.querySelector(".result-message");
                p.classList.add("text-danger");
                p.textContent = `Failed to load helpers: ${err}`;
                helpersContainer.appendChild(clone);
            });
    }

    fetchHelpers();

    // Handle form submission
    form.addEventListener("submit", (e) => {
        e.preventDefault();

        if (activePollingInterval) {
            clearInterval(activePollingInterval);
        }

        const sourceName = document.getElementById("source_name").value;
        const dryRun = document.getElementById("dry_run").checked;
        const targetSection = document.getElementById("target_section").value || null;
        const targetCategory = document.getElementById("target_category").value || null;
        const limit = document.getElementById("limit").value || null;
        const cooldownHours = document.getElementById("cooldown_hours").value;

        const payload = {
            dry_run: dryRun,
            target_section: targetSection,
            target_category: targetCategory,
            limit: limit,
            profile_overrides: {}
        };

        if (cooldownHours !== "") {
            payload.profile_overrides.cooldown_hours = parseFloat(cooldownHours);
        }

        triggerBtn.disabled = true;
        triggerBtn.innerHTML = "Running...";
        statusContainer.classList.remove("ingestion-hidden");
        statusText.className = "";
        statusText.textContent = "Submitting request...";
        resultContainer.innerHTML = "";

        fetch(`/admin/ingestions/api/run/${sourceName}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.dry_run) {
                // Synchronous dry run result
                statusText.textContent = "Dry Run Completed!";
                renderDryRunQueries(data.queries);
                resetBtn();
                fetchHelpers(); // Update cache helpers
            } else if (data.status === "started" && data.task_id) {
                // Async task started
                statusText.textContent = `Background Task Started (ID: ${data.task_id})`;
                pollTaskStatus(data.task_id);
            } else {
                statusText.textContent = "Unknown response.";
                resetBtn();
            }
        })
        .catch(err => {
            statusText.className = "ingestion-status-danger";
            statusText.textContent = `Error: ${err}`;
            resetBtn();
        });
    });

    function renderDryRunQueries(queries) {
        resultContainer.innerHTML = "";
        if (!queries || queries.length === 0) {
            const msgTemplate = document.getElementById("result-message-template");
            const clone = msgTemplate.content.cloneNode(true);
            const p = clone.querySelector(".result-message");
            p.classList.add("hint");
            p.textContent = "No queries generated (possibly blocked by cooldown or no keywords).";
            resultContainer.appendChild(clone);
            return;
        }

        const tableTemplate = document.getElementById("query-table-template");
        const tableClone = tableTemplate.content.cloneNode(true);
        const tbody = tableClone.querySelector(".query-table-body");

        const rowTemplate = document.getElementById("query-row-template");

        queries.forEach((q, idx) => {
            const rowClone = rowTemplate.content.cloneNode(true);
            rowClone.querySelector(".query-index").textContent = idx + 1;
            rowClone.querySelector(".ingestion-query-code").textContent = q.query || q;
            tbody.appendChild(rowClone);
        });

        resultContainer.appendChild(tableClone);
    }

    function pollTaskStatus(taskId) {
        activePollingInterval = setInterval(() => {
            fetch(`/admin/ingestions/api/task/${taskId}`)
                .then(res => res.json())
                .then(task => {
                    statusText.textContent = `Status: ${task.status.toUpperCase()}`;
                    if (task.status === "completed") {
                        clearInterval(activePollingInterval);
                        resultContainer.innerHTML = "";
                        const msgTemplate = document.getElementById("result-message-template");
                        const clone = msgTemplate.content.cloneNode(true);
                        const p = clone.querySelector(".result-message");
                        p.classList.add("ingestion-status-success");
                        p.textContent = `Finished! Result: ${JSON.stringify(task.result)}`;
                        resultContainer.appendChild(clone);
                        resetBtn();
                        fetchHelpers();
                    } else if (task.status === "error") {
                        clearInterval(activePollingInterval);
                        resultContainer.innerHTML = "";
                        const msgTemplate = document.getElementById("result-message-template");
                        const clone = msgTemplate.content.cloneNode(true);
                        const p = clone.querySelector(".result-message");
                        p.classList.add("ingestion-status-danger");
                        p.textContent = `Failed: ${task.error}`;
                        resultContainer.appendChild(clone);
                        resetBtn();
                    }
                })
                .catch(err => {
                    clearInterval(activePollingInterval);
                    statusText.className = "ingestion-status-danger";
                    statusText.textContent = `Polling Error: ${err}`;
                    resetBtn();
                });
        }, 2000);
    }

    function resetBtn() {
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = "Execute";
    }
});
