# Public Web Architecture

The Public Web layer (`app/web`) represents the primary customer-facing interface of Nexora. Because this layer serves anonymous traffic, search engine bots, and authenticated users, its architecture prioritizes performance, SEO, caching, and strict delegation of business logic.

## Core Philosophy

*   **Ultra-Thin Controllers:** Web routes must be extremely concise. They are solely responsible for HTTP mechanics: parsing parameters, checking session auth, catching exceptions, and returning responses.
*   **Orchestration via Application Layer:** A public page (like an Article or Product page) rarely depends on a single domain. Therefore, web routes almost exclusively call the `app/application` layer rather than interacting with `app/domains` directly.
*   **SEO & Speed:** Every route must be designed with Search Engine Optimization and fast Time-to-First-Byte (TTFB) in mind.

---

## Route Organization

Routes are organized into Blueprints under `app/web/routes/`.

*   `content.py`: Handles article, video, and post feeds (`/sections/<slug>`) and detail pages (`/contents/<id>`).
*   `item.py`: Handles commercial product catalogs and product detail pages.
*   `user.py`: Handles authentication, registration, profile, and saved items.
*   `interaction.py`: Handles lightweight AJAX POST endpoints for likes, saves, and comments.
*   `system.py`: Handles static pages (`/about`, `/contact`) and SEO utility routes (`/sitemap.xml`, `/robots.txt`).

---

## Interactions with the Application Layer

Web routes **never** execute raw database queries, compute recommendations, or manually serialize models.

**The standard route flow:**
1.  **Extract:** Extract `request.args` (for pagination/filters) or URL parameters (`<content_id>`).
2.  **Contextualize:** Determine the user's state (e.g., `current_user` or `ip_address`).
3.  **Delegate:** Call the Application Layer (e.g., `get_content_page_data(content_id)`).
4.  **Validate:** If the Application Layer returns `None`, trigger `abort(404)`.
5.  **Render:** Pass the resulting dictionary to `render_template()`.

---

## Content Delivery & Page Rendering

*   **Data Passing:** As established in the serialization rules, the Application Layer returns a "Context Dictionary." The route passes this dictionary directly to `render_template`. The template must not trigger any lazy-loaded database queries.
*   **Recommendations:** Most public pages include dynamic sidebars (Trending, Related, "You May Also Like"). The Route does not fetch these separately. The Application Workflow (e.g., `get_content_page.py`) orchestrates fetching the main content *and* the recommendations simultaneously, returning them in a single payload.

---

## SEO (Search Engine Optimization)

SEO is a primary concern for the `app/web` layer.

1.  **Canonical URLs:** The application layer must provide the authoritative URL for a piece of content to prevent duplicate content penalties.
2.  **Meta Tags:** The Context Dictionary provided to the template must include a `meta` object containing the `title`, `description`, `image`, and `type` (for OpenGraph/Twitter cards).
3.  **Semantic Status Codes:** Routes must return `404 Not Found` for missing content, `410 Gone` for deleted content, and `301 Moved Permanently` if slugs change. Never return a soft 404 (a 200 OK with an "Item not found" page).

---

## Caching Strategy

Due to the high read-to-write ratio of public content, caching is mandatory.

*   **Application Level Caching:** The primary caching layer sits in the Application and Domain query services (using `@cache.memoize` from `app.infrastructure.cache`). This caches the heavily serialized DTOs and aggregation results, avoiding database hits while allowing the Web Route to quickly assemble the page for different users.
*   **Avoid Caching User State:** Do not cache entire HTML responses if the page includes user-specific data (like "Saved" button states or User Avatars). Cache the *content*, but render the template dynamically per request.

---

## Feeds, Filters, and Pagination

Catalog and Section pages rely heavily on dynamic feeds.

*   **State in URL:** All filter states, sorting preferences, and pagination must be reflected in the URL query parameters (`?category=tech&page=2&sort=recent`). Do not use POST requests for fetching filtered feeds.
*   **Helper Functions:** The web layer utilizes helpers (like `parse_active_filters` in `app/web/helpers/filters.py`) to sanitize and extract query parameters before passing them to the Application Layer.

---

## Anti-Patterns

1.  **Business Logic in Routes:** E.g., `if user.engagement_score > 50: show_premium = True`. This logic belongs in the Domain or Application layer, which should return `show_premium` as a boolean in the dictionary.
2.  **Direct DB Commits:** Calling `db.session.commit()` inside a `web/routes/` file (unless it is an incredibly simple, single-domain form submission, though delegating to the Application layer is preferred).
3.  **Rendering ORM Models:** Passing `target=Content.query.get(1)` directly into `render_template`.
