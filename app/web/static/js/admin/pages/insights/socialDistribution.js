// app/web/static/js/admin/pages/insights/socialDistribution.js
import { fetchAndInjectHtml, getSpinnerHtml } from './utilities.js';

export function renderSocialDistribution() {
  const container = document.getElementById("social-distribution-table-body");
  if (!container) return;

  container.innerHTML = getSpinnerHtml(7, "Loading distribution history...");

  const status = document.getElementById("dist-filter-status")?.value || "";
  const type = document.getElementById("dist-filter-type")?.value || "";
  const platform = document.getElementById("dist-filter-platform")?.value || "";
  
  let url = `/admin/distribution/widget/social-distribution`;
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (type) params.append("source_type", type);
  if (platform) params.append("platform", platform);
  
  if (params.toString()) {
      url += `?${params.toString()}`;
  }

  fetchAndInjectHtml(url, 'social-distribution-table-body', 'Loading distribution history...', 7)
    .catch(err => {
      console.error("Failed to load social distribution widget:", err);
    });
}

export function initSocialDistributionFilters() {
    const statusSelect = document.getElementById("dist-filter-status");
    const typeSelect = document.getElementById("dist-filter-type");
    const platformSelect = document.getElementById("dist-filter-platform");
    
    if (statusSelect) statusSelect.addEventListener("change", renderSocialDistribution);
    if (typeSelect) typeSelect.addEventListener("change", renderSocialDistribution);
    if (platformSelect) platformSelect.addEventListener("change", renderSocialDistribution);
}

// Attach modal handlers globally so inline onclick works
window.viewDistributionDraft = function(postId, sourceType, sourceId, platform) {
    const modalContent = document.getElementById("distribution-draft-content");
    if (!modalContent) return;
    
    // Show loading state
    modalContent.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <div class="mt-2 text-muted">Loading post details...</div>
        </div>
    `;
    
    // Open modal using Nexora architecture
    const modalEl = document.getElementById('distributionDraftModal');
    if (modalEl) {
        modalEl.classList.add('active');
    }
    
    // Fetch or generate draft
    fetchAndInjectHtml("/admin/distribution/social-distribution/generate", "distribution-draft-content", "Loading post details...", null, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || ''
        },
        body: JSON.stringify({
            source_type: sourceType,
            source_id: sourceId,
            platform: platform
        })
    }).catch(err => {
        if (modalContent) {
            modalContent.innerHTML = `
                <div class="text-center py-5" style="color: var(--brand-red);">
                    <div class="mt-2">Failed to load draft: ${err.message}</div>
                </div>
            `;
        }
    });
};

window.publishDistributionPost = function(postId) {
    const textEl = document.getElementById("distribution-post-text");
    const urlEl = document.getElementById("distribution-external-url");
    const text = textEl ? textEl.value : "";
    const url = urlEl ? urlEl.value : "";
    
    fetch(`/admin/distribution/social-distribution/${postId}/publish`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || ''
        },
        body: JSON.stringify({
            text: text,
            external_url: url
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        
        // Hide modal using Nexora architecture
        const modalEl = document.getElementById('distributionDraftModal');
        if (modalEl) {
            modalEl.classList.remove('active');
        }
        
        // Refresh table
        renderSocialDistribution();
    })
    .catch(err => alert("Error publishing: " + err.message));
};
