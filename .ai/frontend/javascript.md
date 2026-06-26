# JavaScript Architecture

Nexora utilizes a modern, lightweight, Vanilla ES6 JavaScript architecture. Our goal is to enhance server-rendered pages with dynamic interactivity without the overhead, complexity, or build-step requirements of a Single Page Application (SPA) framework like React or Vue.

## Architectural Philosophy

1.  **Server-Rendered First:** The server delivers fully formed HTML. JavaScript exists to progressively enhance the UI, not to render it from scratch.
2.  **No HTML Generation in JS:** JavaScript must never construct HTML strings (e.g., `container.innerHTML = '<div class="card">...</div>'`).
3.  **Event Delegation:** Minimize event listeners. Bind listeners high in the DOM tree and use event bubbling to handle interactions.
4.  **State in the DOM:** Rely on HTML `data-*` attributes for state whenever possible, minimizing out-of-sync bugs between JS memory and the DOM.

---

## Directory Structure

The `app/web/static/js/` directory is organized modularly:

```text
js/
├── core/                  # Core infrastructure
│   ├── api.js             # Unified fetch() wrapper (CSRF, error handling)
│   ├── dom.js             # DOM querying and manipulation helpers
│   ├── loading.js         # Global spinner/loading state management
│   ├── notifications.js   # Toast notifications
│   └── charts.js          # Chart.js initialization and theming
├── features/              # Cross-domain interactive components
│   ├── comments.js
│   ├── theme.js
│   └── interactions.js
├── {domain}/              # Domain-specific scripts
│   └── commercial/        # e.g., variant-selector.js, gallery.js
├── admin/                 # Isolated admin scripts
└── main.js                # Global initialization entrypoint
```

---

## Rendering Philosophy: HTML Fragments

To adhere to the "No HTML Generation in JS" rule, any dynamic content loading (e.g., "Load More", submitting a form, fetching live data) must follow the **HTML Fragment Pattern**.

1.  **JS calls the API:** `api.get('/api/comments/123')`
2.  **Backend renders Jinja:** The Flask route renders a Jinja macro (e.g., `_comment-list.html`) and returns it as a string in the JSON payload (or directly as text/html).
3.  **JS injects the Fragment:** `container.insertAdjacentHTML('beforeend', response.html);`

*Why?* This ensures the single source of truth for UI structure remains entirely within Jinja templates.

---

## Event Delegation

Do not attach event listeners in a loop. Attach them to a stable parent container or `document.body` and use `.closest()`.

**Anti-Pattern:**
```javascript
// BAD: Attaches 50 listeners, causes memory leaks, breaks if buttons are dynamically added.
document.querySelectorAll('.save-btn').forEach(btn => {
    btn.addEventListener('click', handleSave);
});
```

**Correct Pattern:**
```javascript
// GOOD: One listener, handles dynamically injected elements automatically.
document.addEventListener('click', (e) => {
    const saveBtn = e.target.closest('.save-btn');
    if (!saveBtn) return;
    
    e.preventDefault();
    handleSave(saveBtn.dataset.itemId);
});
```

---

## API Usage (`core/api.js`)

Never use raw `fetch()` directly in feature scripts. Always use the `api.js` wrapper.
The core API module automatically handles:
*   Appending CSRF tokens to mutating requests (POST, PUT, DELETE).
*   Standardizing Error handling (catching 4xx and 5xx errors).
*   Parsing JSON automatically.

```javascript
import { api } from '../core/api.js';

// GET Request
const data = await api.get('/api/user/profile');

// POST Request
const result = await api.post('/api/interactions/save', { item_id: 123 });
```

---

## State Management & DOM Querying

*   **DOM State:** Use HTML5 `data-*` attributes to hold state.
    ```html
    <button class="toggle-btn" data-active="false" data-target-id="content-1">Toggle</button>
    ```
    ```javascript
    const isActive = btn.dataset.active === 'true';
    btn.dataset.active = !isActive;
    ```
*   **Querying:** Cache DOM queries if they are used repeatedly, but prefer querying relative to the event target to ensure isolation.
    ```javascript
    const container = e.target.closest('.widget-container');
    const input = container.querySelector('.widget-input');
    ```

---

## Chart.js Usage (`core/charts.js`)

When implementing data visualization (especially in the Admin dashboard):
1.  **Never configure Chart.js directly in a view script.**
2.  Import initialization functions from `core/charts.js`.
3.  This centralizes color palettes, font settings, and responsive configurations to match the CSS Design Tokens.

---

## Naming Conventions (Recap)

*   **Files:** `kebab-case.js` (e.g., `variant-selector.js`).
*   **Variables / Functions:** `camelCase` (e.g., `fetchData`, `activeElement`).
*   **Classes:** `PascalCase` (e.g., `class ImageGallery`).
*   **Constants:** `UPPER_CASE` (e.g., `const MAX_RETRIES = 3`).

---

## Anti-Patterns (Forbidden Practices)

1.  **Constructing HTML strings in JS:** E.g., `` const html = `<div class="${myClass}">${myData}</div>`; ``. Always fetch pre-rendered Jinja fragments.
2.  **Direct `fetch()` calls:** Bypassing `api.js` means losing CSRF protection and centralized error handling.
3.  **Inline Event Handlers:** e.g., `<button onclick="doSomething()">`. Always use `addEventListener` via delegation.
4.  **Heavy Global State:** Storing complex objects in `window` or global variables. Keep state bound to the DOM or isolated within closures/modules.
5.  **Spaghetti Queries:** Using heavily nested CSS selectors to find elements (e.g., `document.querySelector('#main div .wrapper ul li.active')`). Use specific BEM classes or `data-target` attributes.
