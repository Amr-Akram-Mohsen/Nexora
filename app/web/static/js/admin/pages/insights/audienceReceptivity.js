/**
 * Audience Receptivity Controller
 * Hydrates recommendation CTR, clicks, impressions, and churn risk metrics.
 */
document.addEventListener("DOMContentLoaded", () => {
    if (window.api && typeof window.api.get === "function") {
        const statsUrl = window.APP?.adminUrls?.analyticsStats || "/admin/analytics/stats";
        window.api.get(statsUrl)
            .then(data => {
                if (!data) return;
                const receptivityCtr = document.getElementById("receptivity-ctr");
                if (receptivityCtr && data.receptivity_ctr !== undefined) {
                    receptivityCtr.textContent = data.receptivity_ctr + "%";
                }

                const receptivityClicks = document.getElementById("receptivity-clicks");
                if (receptivityClicks && data.recommendation_clicks !== undefined) {
                    receptivityClicks.textContent = parseInt(data.recommendation_clicks, 10).toLocaleString();
                }

                const receptivityImpressions = document.getElementById("receptivity-impressions");
                if (receptivityImpressions && data.recommendation_impressions !== undefined) {
                    receptivityImpressions.textContent = parseInt(data.recommendation_impressions, 10).toLocaleString();
                }

                const churnRiskCount = document.getElementById("churn-risk-count");
                if (churnRiskCount && data.churn_risk_count !== undefined) {
                    churnRiskCount.textContent = parseInt(data.churn_risk_count, 10).toLocaleString();
                }
            })
            .catch(err => {
                console.debug("Audience receptivity stats pending hookup:", err);
            });
    }
});
