// app/web/static/js/admin/pages/insights/socialDistribution.js
import { fetchAndInjectHtml, getSpinnerHtml } from './utilities.js';

export function renderSocialDistribution() {
  const container = document.getElementById("social-distribution-table-body");
  if (!container) return;

  container.innerHTML = getSpinnerHtml(6, "Loading distribution history...");

  fetchAndInjectHtml(`/admin/insights/widget/social-distribution`, 'social-distribution-table-body', 'Loading distribution history...', 6)
    .catch(err => {
      console.error("Failed to load social distribution widget:", err);
    });
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
    fetchAndInjectHtml("/admin/insights/social-distribution/generate", "distribution-draft-content", "Loading post details...", null, {
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
    
    fetch(`/admin/insights/social-distribution/${postId}/publish`, {
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
