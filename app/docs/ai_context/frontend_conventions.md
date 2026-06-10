# Nexora Frontend Conventions

This document outlines the frontend conventions, styling rules, and scripting patterns used in Nexora. The goal of these conventions is to help future developers and AI assistants make frontend changes without introducing duplicate components, duplicate CSS utilities, duplicate JS patterns, or inconsistent UI implementations.

---

## 1. Template Organization & HTML Components

Nexora uses **Jinja2** templates for HTML generation. Templates are organized into modular, reusable files.

### Template Directory Structure (`app/web/templates/`)

* **`base.html`**: The root layout wrapper containing global SEO meta tags, Open Graph/Twitter properties, font preconnect links, stylesheets, JS files, and structural layers (e.g., `#main-content`, `flash-messages`, and `back-to-top`).
* **`partials/`**: Contains page fragment skeletons (e.g., header, footer).
* **`components/`**: Reusable component templates.
  * **`components/ui/`**: Base design system components (buttons, badges, inputs, forms, sections, etc.).
  * **`components/interactions/`**: Dynamic interactions (comments, reactions, shares).
  * **`components/listing/`**: Generic listing pages.
* **`content/`**: Templates related to content items (articles, videos, posts).
  * **`content/cards/`**: Specific layout cards.
  * **`content/dispatcher/`**: Dispatches items to their appropriate card type dynamically.
  * **`content/features/`**: Layout blocks specific to content.
* **`commercial/`**: Templates for commercial domain items (e.g., items catalog, specifications dialogs, compare layout).

### HTML Component Conventions

Base UI elements must be defined as **Jinja2 macros** in `app/web/templates/components/ui/` and imported as needed.

* **Attribute Passthrough (`attrs`)**: Component macros must accept an `attrs={}` dictionary parameter and loop through it to output arbitrary HTML attributes on the wrapper element.
  ```html
  {% for key, value in attrs.items() %} {{ key }}="{{ value }}" {% endfor %}
  ```
* **Caller Context (`caller()`)**: Wrap children blocks using `{{ caller() }}` to support nested templates.
* **State & Semantic Hooks**: Use standard `data-*` attributes (`data-id`, `data-type`, `data-domain-type`) on the outermost element of card/item components. These attributes are consumed by the CSS variable system and JS delegation handlers.

### Macro & Component Reuse Rules

1. **Explicit Imports**: Always import macros explicitly at the top of the file:
   ```html
   {% from "components/ui/button.html" import button %}
   {% from "components/ui/badge.html" import badge %}
   ```
2. **Card Dispatcher pattern**: To render a list of mixed content cards dynamically, use the card dispatcher macro in `content/dispatcher/card.html`. Avoid writing inline `if-else` loops for card types inside lists.
3. **Card inheritance**: Specific cards (e.g., `article.html`, `video.html`, `post.html`) must inherit from the base card layout (`content/cards/base.html`) using `{% extends "content/cards/base.html" %}` and override predefined blocks (`image_content`, `meta_top`, `meta_bottom`, etc.).

---

## 2. CSS Architecture & Styling

Nexora uses modular vanilla CSS with a structured cascade of imports in `style.css`.

### Cascade Hierarchy (`app/web/static/css/style.css`)

All stylesheet modules are imported in a strict order:
1. **Base Styles (`base/`)**: Globals, variables, resets, and typography.
2. **Theme Variants (`components/theme-variants.css`)**: Global semantic design classes.
3. **Layout Styles (`layout/`)**: Grid systems, header/footer layouts, sidebars.
4. **Reusable UI Components (`components/ui/`, `components/`)**: Buttons, forms, badges, newsletter boxes.
5. **Feature Modules (`content/`, `commercial/`, `features/`)**: Specific component styling (article cards, product specs, comparison tables).
6. **Utility Helpers (`utilities/`)**: Structural flex classes, animations, global helpers.

### CSS Variable Usage (`base/variables.css` & `base/domain-variables.css`)

All UI elements must utilize CSS custom properties to maintain consistency and support light/dark modes.

* **RGB Color Mapping**: Color palettes are defined as comma-separated RGB sets (e.g., `--brand-blue-rgb: 59, 130, 246;`) and mapped to an actual color property (`--brand-blue: rgb(var(--brand-blue-rgb));`). This enables components to use arbitrary transparencies dynamically:
  ```css
  background: rgba(var(--brand-blue-rgb), var(--alpha-soft));
  ```
* **Theme Variants (`theme-variants.css`)**: Components (such as `.btn` and `.badge`) must consume abstract local variables rather than hardcoded colors:
  * `--variant-bg`, `--variant-color`, `--variant-border`
  * `--variant-hover-bg`, `--variant-hover-color`, `--variant-hover-border`
* **Domain Themes (`base/domain-variables.css`)**: Interface coloring changes contextually based on the `[data-domain-type]` attribute. Do not hardcode specific colors in layout components:
  * `[data-domain-type="content"]` sets primary theme colors to blue/purple.
  * `[data-domain-type="commercial"]` sets primary theme colors to green/teal.
* **Layout and Spacing**: Use layout tokens for sizing consistency:
  * `--header-height` / `--header-height-mobile`
  * `--radius-sm` / `--radius-md` / `--radius-lg`
  * `--card-gap` / `--listing-gap`

### Utility Class Conventions

Nexora relies on specific semantic helpers to avoid duplicating layout styles. Do not write custom inline flex properties or grid layouts where existing utility classes can be applied:

* **Flexbox Layouts (`utilities/flex.css`)**:
  * `.flex`, `.flex-col`, `.flex-wrap`
  * `.justify-between`, `.justify-center`
  * `.items-center`, `.items-start`
  * `.inline-flex`
  * `.flex-center` (shortcuts for centering content horizontally and vertically)
  * `.inline-flex-center`
* **Aesthetics Helpers (`utilities/helpers.css`)**:
  * `.img-cover` (`object-fit: cover`)
  * `.img-contain` (`object-fit: contain`)
  * `.is-hidden` (`display: none`)
  * `.hover-lift` (applies dynamic translation & shadows on hover)
  * `.glass-surface` (applies backdrop-blur and soft translucent background borders)

### Responsive Design Conventions

Responsive styles must use CSS variables mapped to breakpoints:
* `--breakpoint-sm` (480px)
* `--breakpoint-md` (768px)
* `--breakpoint-lg` (1024px)
* `--breakpoint-xl` (1280px)

Layout templates should leverage auto-responsive CSS grids where possible:
* `.grid-auto`: Generates dynamic column layouts using `repeat(auto-fill, minmax(260px, 1fr))`.
* Grid systems scale down via media queries: columns switch to 2-columns (`1fr 1fr`) below 580px, and single column (`1fr`) below 360px.
* For swipeable layouts, use `.grid-carousel` (handles mobile horizontal scroll snaps smoothly).

---

## 3. JavaScript Architecture

JavaScript in Nexora uses vanilla ES6, separated into feature-specific files and orchestrated from a central event delegation model.

### Centralized Event Delegation (`main.js` & `core.js`)

To keep the DOM clean and performant, all event handlers are registered globally in `core.js` on `DOMContentLoaded` and delegated down to feature handlers in `main.js`:

* **Event Listeners**: Single global listeners are set for `click`, `submit`, and `change`.
* **Handlers Routing**: Feature click handlers receive the event and check the target element using `.closest()`. If the component matches, they execute their logic and return `true` to stop routing down the delegation chain.
  ```javascript
  // main.js
  function handleGlobalClicks(e) {
      if (handleThemeClick(e)) return;
      if (handleGalleryClick(e)) return;
      if (handleInteractionClick(e)) return;
      // ...
  }
  ```

### Feature Module Conventions (`static/js/features/`)

Every feature module (e.g., `theme.js`, `interactions.js`, `comments.js`, `search.js`) must:
1. **Initialize State**: Provide an initialization function (e.g., `initTheme()`) registered inside `initApp()` or `initUserInteractions()` in `core.js`.
2. **Handle Actions**: Implement a click/submit handler (e.g., `handleThemeClick(e)`) that performs target validation using `e.target.closest('.selector')` and returns `true` if it handles the event.
3. **Use Authentication Guard**: Protect user actions (like bookmarking, reacting, commenting) using `ensureAuthenticated(event, button, message)` from `auth.js`.

### DOM Interaction Patterns

* **Batch Requests**: When rendering listing pages with interactive buttons (like bookmarking/reactions), do not fetch states individually. Use batch endpoints (e.g., `/check-react-batch`, `/check-save-batch`) to fetch initial states in a single request during page load (see `initAllReactions()` in `static/js/features/reactions.js`).
* **Loading States**: Add the `.is-loading` class to buttons during async/API operations via `setLoading(button, true)` in `static/js/core/utils.js`. This displays a spinner and blocks interactions automatically.
* **Inline Tooltips**: Use `showInlineTooltip(targetEl, message)` to display floating notifications next to the interacting component rather than alert windows.
* **Lazy Loading**: Fetch collapsible areas (such as comments or replies) only when opened by the user, and set `data-loaded="true"` on the container to prevent redundant future fetches.
