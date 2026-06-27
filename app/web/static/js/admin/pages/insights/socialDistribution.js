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
function viewDistributionDraft(postId, sourceType, sourceId, platform) {
    const modalContent = document.getElementById("distribution-draft-content");
    if (!modalContent) return;
    
    // Show loading state
    modalContent.replaceChildren();
    const loadDiv = document.createElement('div');
    loadDiv.className = 'py-5 text-center';
    loadDiv.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin text-2xl mb-2 text-muted"></i><p>Loading post details...</p>';
    modalContent.appendChild(loadDiv);
    
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
            modalContent.replaceChildren();
            const errDiv = document.createElement('div');
            errDiv.className = 'text-center py-5';
            errDiv.style.color = 'var(--brand-red)';
            errDiv.innerHTML = `<div class="mt-2">Failed to load draft: ${err.message}</div>`;
            modalContent.appendChild(errDiv);
        }
    });
}

function publishDistributionPost(postId) {
    const textEl = document.getElementById("distribution-post-text");
    const urlEl = document.getElementById("distribution-external-url");
    const text = textEl ? textEl.value : "";
    const url = urlEl ? urlEl.value : "";
    
    window.api.post(`/admin/distribution/social-distribution/${postId}/publish`, {
        text: text,
        external_url: url
    })
    .then(data => {
        // Hide modal using Nexora architecture
        const modalEl = document.getElementById('distributionDraftModal');
        if (modalEl) {
            modalEl.classList.remove('active');
        }
        
        // Refresh table
        renderSocialDistribution();
    })
    .catch(err => alert("Error publishing: " + err.message));
}

document.addEventListener('click', e => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const { action, id, sourceType, sourceId, platform, url, target, loadingMsg, colspan } = btn.dataset;
    
    if (action === 'view-distribution-draft') {
        viewDistributionDraft(id, sourceType, sourceId, platform);
    } else if (action === 'publish-distribution-post') {
        publishDistributionPost(id);
    } else if (action === 'fetch-and-inject-html') {
        if (typeof fetchAndInjectHtml === 'function') {
            fetchAndInjectHtml(url, target, loadingMsg, parseInt(colspan) || null);
        }
    }
});
