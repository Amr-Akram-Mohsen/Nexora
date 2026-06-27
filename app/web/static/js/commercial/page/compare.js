// app/static/js/compare.js

class CompareManager {
    constructor() {
        this.storageKey = 'nexora_compare_ids';
        this.maxItems = 4;
        this.compareIds = this.loadIds();
        this.init();
    }

    loadIds() {
        const stored = localStorage.getItem(this.storageKey);
        return stored ? JSON.parse(stored) : [];
    }

    saveIds() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.compareIds));
    }

    toggleItem(id) {
        id = parseInt(id);
        const index = this.compareIds.indexOf(id);
        if (index > -1) {
            this.compareIds.splice(index, 1);
            this.saveIds();
            this.updateUI();
            return 'removed';
        } else {
            if (this.compareIds.length >= this.maxItems) {
                alert(`You can compare up to ${this.maxItems} items at once.`);
                return 'full';
            }
            this.compareIds.push(id);
            this.saveIds();
            this.updateUI();
            return 'added';
        }
    }

    init() {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.compare-toggle-btn');
            if (btn) {
                e.preventDefault();
                e.stopPropagation();
                const id = btn.dataset.id;
                this.toggleItem(id);
            }
        });

        // Initial UI update
        this.updateUI();
    }

    updateUI() {
        // Update all buttons status
        document.querySelectorAll('.compare-toggle-btn').forEach(btn => {
            const id = parseInt(btn.dataset.id);
            btn.classList.toggle('active', this.compareIds.includes(id));
        });

        this.renderCompareBar();
    }

    renderCompareBar() {
        let bar = document.getElementById('compare-floating-bar');
        if (!bar) return;
        
        if (this.compareIds.length === 0) {
            bar.style.display = 'none';
            return;
        }

        bar.style.display = 'flex';
        const compareUrl = `/compare?ids=${this.compareIds.join(',')}`;
        
        const countEl = bar.querySelector('.compare-bar__count');
        if (countEl) countEl.textContent = this.compareIds.length;
        
        const linkEl = bar.querySelector('.compare-bar__link');
        if (linkEl) linkEl.href = compareUrl;

        const clearBtn = bar.querySelector('.compare-bar__clear');
        if (clearBtn && !clearBtn.dataset.bound) {
            clearBtn.dataset.bound = 'true';
            clearBtn.addEventListener('click', () => {
                this.compareIds = [];
                this.saveIds();
                this.updateUI();
            });
        }
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.compareManager = new CompareManager();
});
