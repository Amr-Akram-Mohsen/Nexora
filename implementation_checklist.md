# Generic "Item" Architecture Implementation Checklist

This checklist maps your conceptual shift (from rigid `product/article` to a generic `item` system) directly onto your actual file structure (`app/templates` and `app/static/css`). This turns the strategy into actionable, tickable tasks.

## Phase 1: Layout & Core Structural Components
*Goal: Make the foundational layout wrappers flexible enough to handle any content type.*

- [ ] **`app/templates/components/listing-page.html`**
  - [ ] Add a new Jinja `caller()` or macro slot for `toolbar`.
  - [ ] Prepare the toolbar area for sorting, result counting, and future view toggles.
- [ ] **`app/templates/components/detail-page.html`**
  - [ ] Remove hardcoded slots that assume specific product or article structures.
  - [ ] Implement four main flexible blocks: `header`, `main`, `sidebar`, and `extra`.
- [ ] **`app/templates/components/section.html`**
  - [ ] Add `header_extra` macro parameter (for things like inline filters or dynamic titles).
  - [ ] Add `footer` parameter (for "view more" links).
- [ ] **`app/templates/components/grid.html`**
  - [ ] Add support for multiple grid variants (e.g., passing a `layout="compact"` or `layout="horizontal"` argument).
- [ ] **`app/templates/components/section-filters.html`**
  - [ ] **Rename conditionally** to `filters-panel.html` (if you want to rename the file) or just refactor its content to no longer rely on specific product electronics filters.
- [ ] **`app/templates/components/hero-sliders.html`**
  - [ ] Refactor the loop to handle generic `item` objects (not just articles).
  - [ ] Rely entirely on the new generic `card_type` variable.

## Phase 2: Card System Standardization
*Goal: Unify how ALL content is displayed in lists and grids.*

- [ ] **`app/templates/components/cards/...`** *(Apply to all card files)*
  - [ ] Extract the shared layout into a standard order: `image` -> `meta-top` -> `title` -> `description` (wrap in `{% if %}`) -> `meta-bottom` -> `actions`.
  - [ ] Ensure all hardcoded type labels (like "Tech News") are replaced by reading `item.card_type`.
  - [ ] Make `description` completely optional so compact cards don't break.
  - [ ] Inside `meta-top`, render dynamic data arrays based on type (topic + brand for articles vs. family + brand for perfumes).
  - [ ] Add a `.card__actions` container to the bottom. Let the `item_type` dictate whether to show a primary "Buy" button or a secondary "Read" link.
  - [ ] Remove `target="_blank"` on internal routing links.

## Phase 3: Detail Pages (Items) Refactoring
*Goal: Shift from electronics-specific naming to generic blocks.*

- [ ] **`app/templates/features/` or `components/...`** (Where specific blocks live)
  - [ ] **`media-gallery.html`** *(You correctly renamed this from product-gallery)*: Ensure the JS cleanly handles mixed media (images, youtube embeds) dynamically.
  - [ ] **`product-details.html`** -> Safely rename/refactor as `item-details.html`. Keep it as the main orchestrator, but move logic out of it.
  - [ ] **`store-links.html`** -> Refactor to `purchase-options.html`. Unify the deal badges (e.g., Best Deal, Available) so they apply to perfumes/accessories too.
  - [ ] **`full-specs.html`** -> Refactor to `details-dialog.html`. It should now accept an array/dict of generic key-value pairs instead of hardcoding "RAM", "CPU", etc.
  - [ ] **NEW:** Create `breadcrumbs.html` inside `app/templates/components/ui/` to track generic tree navigation.

## Phase 4: UI System & Tokens Standardization
*Goal: Stop mixing variant names across different components.*

- [ ] **`app/templates/components/ui/button.html` & `app/static/css/style.css`**
  - [ ] **Delete** generic `.variant--*` classes from `style.css`.
  - [ ] **Implement** specific button classes: `.btn--primary`, `.btn--secondary`, `.btn--outline`, `.btn--ghost`, `.btn--danger`.
  - [ ] Add specific badge classes: `.badge--brand`, `.badge--category`, `.badge--device`, `.badge--deal`.
  - [ ] Implement sizes in the CSS and macro arguments: `sm`, `md`, `lg`.

## Phase 5: Form Systems & Accessibility Upgrade
*Goal: Make inputs fail-safe and accessible.*

- [ ] **`app/templates/components/ui/input.html` & `form.html`**
  - [ ] Fix the current bug: Ensure the `class` variable logic isn't colliding with Python's reserved keywords or generating empty strings.
  - [ ] Inject `aria-label` handling into the macro.
  - [ ] Add `required` and `aria-required` logic based on macro args.
  - [ ] Build the `.field--error` state in CSS and attach `<div role="alert">` to the input structure when validation fails.

## Phase 6: Interaction Systems & States
*Goal: Centralize user interactions.*

- [ ] **`app/static/js/interactions.js` & Templates**
  - [ ] Remove **Dislike** buttons entirely from templates and JS logic.
  - [ ] Standardize the **Save** feature—ensure it's wired everywhere (articles, guides, all generic items). 
  - [ ] Add loading states to all interaction buttons (e.g., a `.is-loading` class that swaps the icon for a spinner) so users know they clicked it while the server responds.
  - [ ] Define `.is-active`, `.hover`, and `.focus-visible` states explicitly in `style.css` without relying purely on color changes (use outlines/shadows).

## Phase 7: Create the New "Missing" Atoms
*Goal: Build completely generic atoms to be reused anywhere.*

- [ ] **`app/templates/components/ui/`** (New Files)
  - [ ] `select.html`
  - [ ] `chip.html`
  - [ ] `dropdown.html`
  - [ ] `tabs.html`
  - [ ] `accordion.html`

***

### Recommended Execution Order for You

If you want to tackle this piece-by-piece in your codebase, perform it strictly in this sequence to avoid breaking dependencies:

1. **Atoms & CSS First (Phases 4 & 5)**: Fix your buttons, badges, and inputs in `components/ui/` and `style.css`.
2. **Layout Second (Phase 1)**: Update `detail-page.html`, `listing-page.html`, and `section.html` to accept the new flexible blocks.
3. **Card Standardization (Phase 2)**: Rebuild the cards to match the new item agnostic flow.
4. **Item Detail Decomposition (Phase 3)**: Go into `item-page.html` and break down the old electronics logic into the generic `purchase-options` and `details-dialog`.
