# CSS Architecture

Nexora utilizes a highly structured, scalable Vanilla CSS architecture. By leveraging modern CSS Custom Properties (Variables) and strict naming conventions, we achieve the modularity of preprocessors without the build complexity.

## Architectural Philosophy

1.  **Vanilla CSS First:** Rely on native CSS variables, flexbox, grid, and native nesting (where supported) instead of frameworks like Tailwind, SASS, or LESS.
2.  **Strict BEM Naming:** The Block, Element, Modifier (BEM) methodology is mandatory for all component classes.
3.  **Mobile-First Responsive Design:** Base styles target mobile devices, with `@media (min-width: ...)` queries layering on desktop styles.
4.  **Domain Isolation:** Just like the Python backend and HTML templates, CSS is strictly isolated by domain (e.g., `commercial/`, `content/`).

---

## Directory Structure & ITCSS Layering

The `app/web/static/css/` directory follows an adapted ITCSS (Inverted Triangle CSS) methodology, increasing in specificity from top to bottom.

```text
css/
├── base/                      # Layer 1: Globals & Resets
│   ├── variables.css          # Core design tokens (colors, spacing, radii)
│   ├── domain-variables.css   # Domain-specific color overrides
│   ├── reset.css              # CSS reset
│   └── typography.css         # Font families and scale
├── layout/                    # Layer 2: Macro Structure
│   ├── grid.css               # Core grid system
│   └── header.css, footer.css # Major structural regions
├── components/                # Layer 3: Reusable UI (Atomic)
│   ├── ui/                    # Buttons, Badges, Modals, Forms
│   └── cards.css              # Generic card structures
├── {domain}/                  # Layer 4: Domain Specific
│   ├── commercial/            # e.g., product galleries, pricing tables
│   └── content/               # e.g., article sidebars, reading layouts
├── features/                  # Layer 5: Cross-Domain Pages
│   └── auth.css, profile.css
├── utilities/                 # Layer 6: Overrides (High Specificity)
│   └── helpers.css, flex.css
└── admin/                     # Isolated Dashboard Styles
```

---

## Design Tokens (CSS Variables)

All hardcoded values must be extracted to CSS variables in `base/variables.css`.

*   **Colors:** Semantic naming is required.
    ```css
    :root {
      --color-primary: #3b82f6;
      --color-primary-hover: #2563eb;
      --color-surface: #ffffff;
      --color-text-main: #1f2937;
      --color-border: #e5e7eb;
    }
    ```
*   **Spacing System:** Base-4 or Base-8 scale.
    ```css
    :root {
      --spacing-xs: 0.25rem;  /* 4px */
      --spacing-sm: 0.5rem;   /* 8px */
      --spacing-md: 1rem;     /* 16px */
      --spacing-lg: 1.5rem;   /* 24px */
      --spacing-xl: 2rem;     /* 32px */
    }
    ```
*   **Radii, Shadows, Transitions:**
    ```css
    :root {
      --radius-sm: 4px;
      --radius-md: 8px;
      --shadow-subtle: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      --transition-fast: 150ms ease-in-out;
    }
    ```

---

## BEM Naming Convention

BEM (`block__element--modifier`) is strictly enforced to prevent CSS specificity wars and unintended side effects.

*   **Block:** The standalone entity (`.item-card`).
*   **Element:** A part of the block that has no standalone meaning (`.item-card__image`).
*   **Modifier:** A flag that changes appearance or behavior (`.item-card--featured`).

**Example:**
```css
/* BAD: High specificity, generic class names */
#catalog-list .card .title { ... }
.active-btn { ... }

/* GOOD: BEM */
.item-card { ... }
.item-card__image { ... }
.item-card__title { ... }
.item-card--featured { ... }
.item-card__title--large { ... }
```

---

## Responsive Strategy

Nexora uses a mobile-first approach. Do not use `max-width` queries unless specifically targeting a rare edge case.

```css
/* 1. Mobile (Default) */
.grid-container {
  grid-template-columns: 1fr;
}

/* 2. Tablet (md: 768px) */
@media (min-width: 768px) {
  .grid-container {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 3. Desktop (lg: 1024px) */
@media (min-width: 1024px) {
  .grid-container {
    grid-template-columns: repeat(4, 1fr);
  }
}
```

---

## Utilities & Helpers

The `utilities/` directory contains single-purpose classes meant to override or rapidly assemble layouts without writing custom CSS for every margin tweak. 
*   **Naming:** Utility classes often reflect their CSS property (e.g., `.d-flex`, `.mt-4`, `.text-center`).
*   **Rule:** If you find yourself applying more than 5 utility classes to an element, you should extract those styles into a BEM component class.

---

## Animations and Micro-Interactions

Dynamic, premium aesthetics are a core requirement for Nexora. All interactive elements must have defined state changes (`:hover`, `:focus`, `:active`).

*   **Transitions:** Apply transitions to the default state, not the hover state.
    ```css
    .btn {
      transition: background-color var(--transition-fast), transform var(--transition-fast);
    }
    .btn:hover {
      transform: translateY(-2px);
    }
    ```
*   **Animations:** Stored in `utilities/animations.css` (e.g., `.fade-in`, `.slide-up`). Use keyframes for mounting animations (e.g., modals popping in).

---

## Admin Styling Boundaries

The Admin application (`app/admin`) has a distinct, denser aesthetic tailored for data heavy interfaces.
*   **Isolation:** Admin CSS lives entirely within `static/css/admin/`.
*   **No Cross-Contamination:** Admin CSS must never be loaded on the public website, and vice versa. 
*   If a component (like a button) is visually identical, it should be defined in `components/ui/` and loaded by both. However, most admin tables and panels are bespoke to the admin layer.

---

## Anti-Patterns

1.  **The `!important` tag:** Forbidden in component CSS. It may only be used in `utilities/` (e.g., `.d-none { display: none !important; }`).
2.  **Deep Nesting & High Specificity:** CSS rules should rarely exceed a specificity depth of 2 (e.g., `.block__element:hover`). Never target HTML tags inside a block without an element class (e.g., `.item-card h2` is forbidden; use `.item-card__title`).
3.  **Hardcoded Magic Numbers:** E.g., `margin: 17px;` or `color: #ff3344;`. Use the spacing system (`var(--spacing-md)`) and semantic color tokens (`var(--color-primary)`).
4.  **CamelCase or snake_case classes:** Stick strictly to `kebab-case`.
