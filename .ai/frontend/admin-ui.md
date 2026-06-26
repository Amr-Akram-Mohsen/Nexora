# Admin UI Architecture & Design System

The Nexora Admin application uses a distinct, data-dense design system separate from the public web interface. It prioritizes information hierarchy, bulk data manipulation, and rapid inspection over marketing aesthetics.

## Overall Layout & Visual Hierarchy

*   **Structure:** A fixed left sidebar for navigation, a fixed top header for user/system context, and a scrollable main content area.
*   **Visual Language:** High contrast for data tables, subtle gray backgrounds (`var(--color-surface-alt)`) for structural distinction, and semantic colors (Red, Green, Yellow) reserved strictly for status indicators.
*   **Responsive Behavior:** 
    *   Mobile/Tablet: The sidebar collapses behind a hamburger toggle.
    *   Tables: Must wrap in a container with `overflow-x: auto` to prevent breaking the layout on narrow viewports.

---

## CRUD Pages & Table Architecture

CRUD (Create, Read, Update, Delete) pages are the backbone of the admin panel. They are strictly defined by the schema in `app/admin/tables.py` to ensure consistency.

### 1. Preview Tables (List View)
The primary view of a CRUD page is the Preview Table.
*   **Definition:** Defined in `CRUD_TABLES[domain]["preview_table"]`.
*   **Implementation:** Rendered via `admin/components/ui/tables.html`.
*   **Row Rendering:** Handled by domain-specific partials (e.g., `_item_row.html`, `_user_row.html`) to allow custom formatting (like rendering an image thumbnail or a status badge) while keeping the table structure uniform.
*   **Sorting:** Table headers marked as sortable must append `?sort_by=X&order=asc|desc` to the URL.

### 2. Inspect Pages (Detailed View)
When a user clicks on a row, they should not be taken to a completely new page. Instead, an "Inspect Panel" (a slide-out drawer) opens.
*   **Definition:** Defined in `CRUD_TABLES[domain]["detailed_table"]`. The schema groups data into logical sections (e.g., "Account Info", "Engagement Metrics").
*   **Implementation:** The Python backend uses `get_inspect_table(table_name, data)` to map raw data to the schema.
*   **Rendering:** Handled by `admin/components/ui/inspect.html`. It iterates through the sections and renders key-value pairs cleanly.

---

## Toolbars, Filters, and Bulk Actions

Every Preview Table is accompanied by a Toolbar (`admin/components/ui/toolbar.html`).

*   **Placement:** Fixed directly above the table.
*   **Filters:** Form elements (dropdowns, date pickers) that instantly update the view. **Rule:** Filter state must be stored in the URL query string (e.g., `?status=active&type=video`) so the current view is shareable and bookmarkable.
*   **Search:** A text input that debounces and applies a global text search against the active domain.
*   **Bulk Actions:** A dropdown or button group that appears *only* when one or more checkboxes in the table are selected. Bulk actions act on the selected IDs via a POST request.

---

## Pagination

*   **Implementation:** `admin/components/ui/pagination.html`.
*   **Mechanism:** Server-side pagination via URL parameters (`?page=2`).
*   **UI:** Shows Previous/Next buttons, the current page number, and total record count.

---

## Widgets and Charts

The Admin Dashboard relies heavily on visual data summaries.

*   **Summary Bars (KPI Cards):** Small cards displaying a single metric, a label, and a delta (e.g., "+5% vs last week"). Located in `dashboard/widgets/_stats_grid.html`.
*   **Charts:** All charts must be rendered using `Chart.js`.
    *   **Rule:** Chart configuration must not be hardcoded in the HTML. Initialize charts via `static/js/core/charts.js` to ensure brand colors, fonts, and tooltips are consistent.
*   **Data Injection:** Chart data is passed from Jinja as JSON inside a `data-chart-payload` attribute, which the JS reads on mount.

---

## Modals vs. Inspect Panels

*   **Inspect Panels (Drawers):** Use for viewing deep data (`detailed_table`), viewing logs, or reading content. They slide in from the right and do not block the user from seeing the table underneath.
*   **Modals:** Use strictly for blocking, decisive actions.
    *   Destructive actions (e.g., "Are you sure you want to delete this user?").
    *   Complex nested forms (e.g., "Create new Category").
    *   Rendered via `components/ui/modal.html`.

---

## UI Components & States

### Badges
*   Used for Enums, Statuses, and Classifications.
*   Rendered via `components/ui/badge.html`.
*   Variants: `success` (Active, Completed), `warning` (Pending, Stale), `danger` (Failed, Deleted), `info` (Neutral categories).

### Empty States
*   **Rule:** A table or widget must never be completely blank if there is no data.
*   **Implementation:** Render `components/ui/empty-state.html`. It must include a relevant icon, a clear message ("No users found"), and optionally a Call To Action ("Clear Filters" or "Add User").

### Loading States
*   While waiting for an HTML fragment or API response, the UI must provide feedback.
*   **Tables:** Replace the table body with a skeleton loader or a centered spinner (`components/ui/spinner.html`).
*   **Buttons:** Add a `.btn--loading` class which disables the button and replaces the icon with a spinner to prevent double-submissions.
