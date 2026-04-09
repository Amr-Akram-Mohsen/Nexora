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
        
        if (this.compareIds.length === 0) {
            if (bar) bar.remove();
            return;
        }

        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'compare-floating-bar';
            bar.className = 'compare-bar flex items-center justify-between';
            document.body.appendChild(bar);
        }

        const compareUrl = `/compare?ids=${this.compareIds.join(',')}`;
        
        bar.innerHTML = `
            <div class="compare-bar__info flex items-center">
                <div class="compare-bar__count">${this.compareIds.length}</div>
                <span class="compare-bar__text">Items selected for comparison</span>
            </div>
            <div class="compare-bar__actions flex items-center">
                <button class="compare-bar__clear btn btn--link">Clear All</button>
                <a href="${compareUrl}" class="btn btn--primary">Compare Now</a>
            </div>
        `;

        bar.querySelector('.compare-bar__clear').onclick = () => {
            this.compareIds = [];
            this.saveIds();
            this.updateUI();
        };
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.compareManager = new CompareManager();
});
