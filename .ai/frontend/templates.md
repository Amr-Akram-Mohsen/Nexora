# Templates Architecture

The Nexora frontend uses Jinja2 as its templating engine. The architecture is explicitly designed to mimic modern component-based frameworks (like React or Vue) while remaining fully server-side rendered.

## Architectural Philosophy

1.  **Component-Driven Design:** The UI is constructed from small, highly reusable, and composable Jinja macros rather than large monolithic HTML files.
2.  **Domain Separation:** Templates are strictly grouped by their business domain (e.g., `commercial`, `content`). Generic UI elements are isolated from domain-specific layouts.
3.  **Dumb Templates:** Templates are presentation-only. They execute **zero** business logic and perform **zero** database queries.
4.  **No ORM Models:** Templates must only receive serialized Python dictionaries or primitive types. Passing SQLAlchemy model instances is strictly forbidden to prevent N+1 database queries.

---

## Directory Structure

The `app/web/templates` directory follows a strict hierarchy designed for scale:

```text
templates/
├── base.html                  # Root layout wrapper (HTML shell)
├── components/                # Domain-agnostic UI elements
│   ├── ui/                    # Atomic components (Buttons, Inputs, Badges)
│   ├── cards/                 # Generic card containers
│   └── interactions/          # Universal interaction blocks (Comments, Saves)
├── partials/                  # Global site regions (Header, Footer, Nav)
├── {domain}/                  # Domain-specific modules (e.g., commercial, content)
│   ├── cards/                 # Macros for displaying domain entities (e.g., item-card)
│   ├── catalog/               # List and grid views
│   ├── features/              # Domain-specific UI blocks (e.g., variant-selector)
│   ├── page/                  # The final assembled page layouts
│   └── dispatcher/            # Polymorphic routing layouts
└── admin/                     # Admin dashboard templates (follows a similar pattern)
```

### 1. `components/ui/` (The Atomic Layer)
This directory contains the lowest-level building blocks.
*   **Contents:** `button.html`, `input.html`, `modal.html`, `badge.html`.
*   **Rules:** Must consist entirely of Jinja macros (`{% macro ... %}`). They must never know about domain concepts (e.g., an `Article`). They only accept generic parameters like `text`, `icon`, `variant`, `class`.

### 2. Domain Directories (e.g., `commercial/`, `content/`)
These directories contain all logic specific to a given business vertical.
*   **`features/`**: Complex blocks that require domain data (e.g., an `item-gallery.html` macro that accepts a list of images).
*   **`cards/`**: Macros for displaying specific entities (e.g., `article-card`, `video-card`).
*   **`page/`**: The top-level files passed to `render_template()` from the Python routes. These files assemble the layout by importing and calling the necessary macros.
*   **`dispatcher/`**: Used for polymorphic rendering (e.g., rendering a different page layout if the target is an `Article` vs a `Video`).

---

## Macro Usage & Composition

Jinja Macros are the core mechanism for reusability. 

### Defining Macros
Macros must clearly define their inputs. Provide sensible defaults where appropriate, and always include an extensible `class=""` and `attrs={}` argument.

```html
{# components/ui/button.html #}
{% macro button(text="", type="button", variant="primary", class="", icon=None, attrs={}) %}
<button type="{{ type }}" class="btn btn--{{ variant }} {{ class }}" {% for k, v in attrs.items() %}{{ k }}="{{ v }}"{% endfor %}>
  {% if icon %}<i class="{{ icon }}"></i>{% endif %}
  {{ text }}
</button>
{% endmacro %}
```

### Composing Macros
Higher-level macros compose lower-level ones.
```html
{# content/cards/article-card.html #}
{% from "components/ui/badge.html" import badge %}

{% macro article_card(article) %}
<div class="article-card">
  <div class="article-card__header">
     {{ badge(text=article.category, variant="info") }}
  </div>
  <h3>{{ article.title }}</h3>
</div>
{% endmacro %}
```

---

## Data Passing Rules

To enforce the "Dumb Templates" philosophy, the backend application layer must provide fully resolved, formatted data structures to the template.

**Forbidden Pattern (ORM in Template):**
```html
<!-- BAD: Triggers a hidden SQL query from Jinja -->
{% for comment in article.comments %} 
  ...
{% endfor %}
```

**Correct Pattern (Serialized Dicts):**
```html
<!-- GOOD: The backend resolved everything and passed a simple list of dicts -->
{% for comment in comments %}
  ...
{% endfor %}
```

If a template needs to display a formatted date or currency, the backend serializer or a registered Jinja filter should handle the formatting. Complex `if/else` logic regarding business state (e.g., "Can this user buy this item?") must be calculated in the backend and passed as a boolean flag (e.g., `can_purchase=True`).

---

## Naming Conventions (Recap)

As established in the naming conventions:
*   **Views / Pages**: `kebab-case.html` (e.g., `catalog-page.html`).
*   **Partials / Macros**: `_kebab-case.html` (e.g., `_article-card.html`). *If it is not meant to be routed directly, prefix it with an underscore.*
*   **Macro Function Names**: `snake_case` (e.g., `{% macro render_item() %}`).
*   **CSS Classes**: Strict BEM (e.g., `item-card__title--featured`).
