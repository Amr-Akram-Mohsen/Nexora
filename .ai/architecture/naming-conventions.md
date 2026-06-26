# Naming Conventions

This document establishes the strict naming conventions for the Nexora codebase. Consistency in naming prevents cognitive friction, improves code readability, and enforces a unified engineering standard across both backend and frontend.

## Case Types Defined

Before detailing specific rules, ensure alignment on terminology:
*   **`snake_case`**: All lowercase, words separated by underscores.
*   **`kebab-case`**: All lowercase, words separated by hyphens.
*   **`PascalCase`**: Capitalized words, no separators.
*   **`camelCase`**: First word lowercase, subsequent words capitalized, no separators.
*   **`UPPER_CASE`**: All uppercase, words separated by underscores.

---

## File and Directory Naming

### Python (Backend)
*   **Python Files / Modules**: `snake_case.py` (e.g., `content_access.py`, `query_service.py`).
*   **Packages / Directories**: `snake_case`. Prefer single, short words without underscores when possible (e.g., `domains`, `application`, `content`).

### UI (Frontend)
*   **HTML Templates (Views)**: `kebab-case.html` (e.g., `catalog-page.html`, `reset-password.html`).
*   **HTML Partials / Macros**: `_kebab-case.html` (e.g., `_item-card.html`, `_navigation.html`). *The leading underscore denotes that the file is not intended to be rendered directly.*
*   **CSS Files**: `kebab-case.css` (e.g., `variant-selector.css`, `admin-dashboard.css`).
*   **JavaScript Files**: `kebab-case.js` (e.g., `variant-selector.js`, `hero-slider.js`).

---

## Backend Code (Python)

*   **Classes**: `PascalCase` (e.g., `RecommendationEngine`, `ContentItem`).
*   **Functions & Methods**: `snake_case` (e.g., `get_content_page()`, `calculate_score()`).
*   **Variables**: `snake_case` (e.g., `user_id`, `active_filters`).
*   **Constants**: `UPPER_CASE` (e.g., `DEFAULT_PAGE_SIZE`, `MAX_RETRIES`).
*   **Enums**:
    *   Class Name: `PascalCase` (e.g., `TargetType`, `IngestionStatus`).
    *   Members: `UPPER_CASE` (e.g., `ARTICLE`, `VIDEO`, `PENDING`).

### Database Models
*   **Class Name**: `PascalCase`, strictly singular (e.g., `User`, `Content`, `Category`).
*   **Table Name**: `snake_case`, strictly plural (e.g., `users`, `contents`, `categories`).

### Data Transfer Objects (DTOs) & Serializers
*   **Serialization Keys (JSON fields)**: `snake_case` (e.g., `{"first_name": "John", "is_active": true}`).
*   *Rule:* We retain `snake_case` for JSON payloads sent to the frontend to map 1:1 with database columns and Python objects, avoiding the CPU overhead of translating entire payloads between `snake_case` and `camelCase`.

---

## Frontend Code (HTML / CSS / JS)

### CSS Architecture (BEM)
Nexora uses strict **BEM (Block, Element, Modifier)** for CSS class naming.
*   **Block**: `kebab-case` (e.g., `.item-card`). Represents the standalone entity.
*   **Element**: Appended with `__` (e.g., `.item-card__title`, `.item-card__image`). Represents a part of the block.
*   **Modifier**: Appended with `--` (e.g., `.item-card--featured`, `.item-card__title--large`). Represents a variation in state or appearance.
*   *Forbidden:* Do not use `camelCase` or `snake_case` in CSS. Do not chain elements (e.g., `.block__el1__el2` is illegal).

### HTML & DOM
*   **HTML IDs**: `kebab-case` (e.g., `id="main-navigation"`, `id="submit-button"`).
*   **Data Attributes**: `data-kebab-case` (e.g., `data-user-id="123"`, `data-action-type="save"`).
*   **Form Inputs (Names)**: `snake_case` (e.g., `name="first_name"`). This allows seamless mapping to backend Python variables and HTTP form payloads.

### JavaScript
*   **Variables & Let/Const**: `camelCase` (e.g., `activeFilters`, `modalContainer`).
*   **Functions**: `camelCase` (e.g., `fetchUserData()`, `toggleMenu()`).
*   **Classes**: `PascalCase` (e.g., `AnalyticsTracker`, `DropdownMenu`).
*   **Constants**: `UPPER_CASE` (e.g., `API_TIMEOUT`, `MAX_RETRIES`).

### Jinja Templates
*   **Macros (Definition)**: `snake_case` (e.g., `{% macro render_item_card() %}`).
*   **Jinja Variables**: `snake_case` (Matching the Python backend context payloads).

---

## Flask & HTTP Routing

*   **Routes (URLs)**: `kebab-case` (e.g., `/user-profile`, `/reset-password`). URLs must be entirely lowercase and use hyphens for spaces.
*   **Endpoints (View Functions)**: `snake_case` (e.g., `def user_profile():`, `def reset_password():`).
*   **Query Parameters**: `snake_case` (e.g., `?page_size=20&sort_by=date`).

---

## Summary Matrix

| Entity | Convention | Example |
| :--- | :--- | :--- |
| Python Files | `snake_case.py` | `query_service.py` |
| UI Files (HTML/CSS/JS) | `kebab-case.ext` | `catalog-page.html` |
| Python Classes | `PascalCase` | `ContentService` |
| Python Functions/Vars | `snake_case` | `get_user_data()` |
| DB Tables | `snake_case` (Plural) | `users`, `saved_items` |
| JSON / DTO Keys | `snake_case` | `{"user_id": 1}` |
| CSS Classes | BEM (`kebab-case`) | `.btn`, `.btn__icon`, `.btn--primary`|
| HTML IDs / Data Attrs | `kebab-case` | `id="main-nav"`, `data-target` |
| JS Variables/Functions | `camelCase` | `fetchData()`, `activeMenu` |
| JS Classes | `PascalCase` | `ThemeManager` |
| URLs | `kebab-case` | `/auth/reset-password` |
| Constants (Any Lang) | `UPPER_CASE` | `MAX_LIMIT` |
