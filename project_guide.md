# Developer Collaboration Guide: Architecture & Reusable Components

Since you are splitting the work vertically (by feature), any of the 3 developers may touch the Backend, Frontend HTML, CSS, and JS. To prevent stepping on each other's toes or duplicating code, rely on the established patterns mapped below.

---

## 1. CSS/Styling Architecture (`app/static/css/style.css`)

The project uses a **CSS Variable + Semantic utility** approach, closely resembling Tailwind CSS concepts but built manually. 
**RULE:** Never hardcode colors, spacing, or font sizes. Always write utility variables.

### Reusable Global Variables
*   **Brand Colors**: `--brand-blue`, `--brand-purple`, `--brand-green`, `--brand-orange`, `--brand-red`.
*   **Semantic Colors (Dark Mode Support)**: `--background`, `--foreground`, `--card`, `--primary`, `--secondary`, `--muted`, `--destructive`, `--border`.
    *(Note: These automatically adjust based on `body.dark-mode` or `body.light-mode`)*.
*   **Typography Sets**: `--text-xs`, `--text-sm`, `--text-base`, `--text-xl` up to `--text-5xl`.
*   **Font Weights**: `--weight-md`, `--weight-bold`, `--weight-xbold`.
*   **Shadows / Overlays**: `--shadow-sm` up to `--shadow-2xl`, `--overlay-dark-40` up to `--overlay-dark-70`.
*   **Radius**: `--radius-sm` through `--radius-full`.

### Reusable Global Components & Utilities
*   **Layout Utilities**: `.flex`, `.flex-col`, `.items-center`, `.justify-between`, `.container`.
*   **Buttons & Badges**: 
    Use the base class `.btn` or `.badge`, then attach a variant. 
    *Variants:* `.variant--primary`, `.variant--secondary`, `.variant--outline`, `.variant--ghost`, `.variant--destructive`.
*   **Forms**: `.input`, `.textarea`, `.checkbox`, `.label`.
*   **Cards Base**: `.card`. Contains nested structures like `.card__img-wrapper`, `.card__title`, etc. You can apply contexts: `.card--article` (Blue/Purple) or `.card--item` (Green/Teal).

---

## 2. JavaScript Event Architecture (`app/static/js/main.js`)

**RULE:** Do not write random `element.addEventListener('click', ...)` throughout the codebase. The app uses an **Event Delegation** pattern.

### The Global Handlers
All primary interactions are routed through two main functions inside `main.js`:
1.  **`handleGlobalClicks(e)`**: Intercepts ALL clicks on the document. It uses `e.target.closest('.selector')` to determine what was clicked.
    *   *Examples handled:* `.mode-toggle` (Dark mode), `.react-btn`, `.save-btn` (Interactions), `.item-buy-link`, `.comments-toggle-btn`.
    *   **How to add a new click feature:** Just add a new `if (e.target.closest('.your-new-btn')) { doSomthing(); return; }` block inside `handleGlobalClicks()`.

2.  **`handleGlobalSubmits(e)`**: Intercepts ALL form submissions on the document.
    *   *Examples handled:* `.comment-form`, `[data-newsletter-form]`, `.contact-form`, `.header-search__form`.
    *   **How to add a new form feature:** Add a new `e.target.closest('.your-form')` check in `handleGlobalSubmits`, prevent default if needed, and call an async fetch function.

### Authentication Checks
*   `ensureAuthenticated(e, btnElelemnt, message)`: If a feature requires the user to log in (like clicking "Save"), call this function first.

---

## 3. HTML / Jinja Components (`app/templates/`)

**RULE:** Do not copy-paste complex repeating HTML blocks. Use Jinja `{% include %}`.

### The Building Blocks
*   **Master Layout**: `base.html` handles the generic `<head>`, `<nav>`, and `<footer>`.
*   **Pages**: `article-page.html`, `item-page.html`, `index.html` extend `base.html`.
*   **`components/` Directory**: Contains micro-structures designed for reuse down the component tree.
    *   `components/detail-page.html`: Shared shell layout for individual detail pages.
    *   `components/hero-sliders.html`: Used to show moving hero banners on pages.
    *   `components/cards/`: Stores the card design templates for articles or retail items.
    *   `components/section-filters.html` & `components/filter_chip.html`: Filtering UI headers.

---

## 4. Backend Models & Relationships (`app/models.py`)

**RULE:** Check `models.py` before making a new database table. The relationships are already heavily cross-linked.

### Key Entities
*   `User`: Handles Local/Google auth and links up with everything the user does.
*   `Article` & `Item`: The two main content types. They share common ground through Polymorphic relationships (Reactions, Comments, Views, Saves logic work interchangeably for both!).
*   **Taxonomy Models**: `Section`, `Topic`, `Brand`, `Category`. Both Articles and Items are linked to these categorization tables.
*   **Item Specifics**: `ItemVariant`, `ItemImage`, `ItemSpecification`, `Store`, `ItemStoreLink` - These handle the complex real-world e-commerce structure for retail items.

### Convenience Helpers (Keep using these)
*   **In `models.py`**: Properties like `item.details`, `item.quick_details`, `item.default_variant`, and `item.store_links`. Do not recalculate this data manually in JSON/routes, rely on the Class properties!

---

## 🚀 How to start working together (The Workflow)

1.  **Map Out New Features against this Architecture.** 
    *   *Example Task: User Dashboard.* 
    *   *Action:* Don't build new styles. Use `.container`, `.flex`, and `.card` from `style.css`. Query the `Save` and `Reaction` tables linked to the `User` model.
2.  **Create Separate GitHub Feature Branches.**
    *   Dev 1 works on branch `feature/profile-dashboard`
    *   Dev 2 works on branch `feature/admin-panel`
3.  **To avoid CSS/JS conflicts:** Ensure all new JS is bound to the document through `handleGlobalClicks` rather than standalone ad-hoc listeners. If someone alters `.btn` CSS, they must notify the team.
