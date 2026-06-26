# Serialization Architecture

Serialization forms the crucial boundary between the Backend (Domain/Application logic) and the Frontend (Jinja Templates/JSON APIs). The Nexora architecture demands strict enforcement of this boundary to prevent N+1 queries and decouple presentation from data access.

## Core Responsibilities

1.  **Transforming Rich Models:** Convert SQLAlchemy ORM models, complex query results, or aggregation tuples into plain, primitive Python dictionaries (lists, dicts, strings, ints, floats, booleans).
2.  **Safeguarding the DB Connection:** Once data passes through a serializer, all relationships must be eagerly loaded or ignored. The resulting dictionary cannot trigger lazy-loading queries in the template.
3.  **Providing a Contract:** The output of a serializer is the explicit data contract guaranteed to the UI.

---

## Types of Serializers

### 1. Domain DTO Serializers
Located in `app/domains/{domain}/serializers.py`. These represent the standard representation of an entity.
*   **Purpose:** The default way to serialize an object (e.g., `serialize_article(article)`).
*   **Reusability:** Highly reusable. `serialize_content()` might call `serialize_user()` internally.
*   **Polymorphism:** Nexora utilizes generic target serializers like `serialize_target(obj)` (found in `app/domains/serializers.py`) to handle polymorphic feeds where an item could be an Article, Video, or Post.

### 2. ViewModels
While DTOs are raw representations of database entities, ViewModels are tailored for a specific UI page.
*   **Purpose:** If a page requires deeply merged data (e.g., an Item blended with user-specific Recommendation Scores), the Application Layer uses a ViewModel serializer to assemble this bespoke dictionary.

### 3. Admin Table & Inspect Serializers
The Admin UI relies on highly structured data formats.
*   **Table Serializers:** Map domain data into the specific columns required by the `preview_table` definitions in `app/admin/tables.py`.
*   **Inspect Serializers:** The `get_inspect_table(table_name, data)` function takes a standard DTO and structurally maps it into the grouped key-value pairs required by the slide-out Inspect Panel.

### 4. Chart & Widget Serializers
Usually located in analytics domains (e.g., `app/domains/analytics/service/serializers.py`).
*   **Chart Serializers:** Transform SQL aggregation results (like `[(Date, Count)]`) directly into the structure expected by Chart.js (`{ labels: [...], datasets: [{ data: [...] }] }`).
*   **Widget Serializers:** Output specific KPI shapes: `{"label": "Total Users", "value": 1500, "delta": "+5%", "trend": "up"}`.

---

## Formatting Rules

Serialization is about data structure, not presentation styling.

*   **Dates:** Always serialize datetime objects to standard formats, such as ISO-8601 strings (`dt.isoformat()`). *Do not* serialize dates to localized, human-readable strings like "June 25th, 2026" in the backend. Let Jinja filters or the frontend JS handle localization.
*   **Currency:** Serialize prices as floats or integers (cents). Do not prepend currency symbols (e.g., return `15.99`, not `"$15.99"`).
*   **Relationships:** Only serialize relationships that are necessary for the payload. Be wary of deeply nested serialization graphs that serialize the entire database.

---

## Reusable Composition

Avoid duplicating serialization logic. If Domain A needs to serialize Domain B, it should import Domain B's serializer.

```python
from app.domains.user.service.serializers import serialize_user_basic

def serialize_comment(comment):
    return {
        "id": comment.id,
        "body": comment.body,
        # Reusing the user serializer to ensure standard format
        "author": serialize_user_basic(comment.author) if comment.author else None,
        "created_at": comment.created_at.isoformat()
    }
```

---

## Serialization Anti-Patterns

1.  **Serializing in Routes:** Constructing the final dictionary manually inside `app/web/routes/...`. Routes must call Application/Domain services which return the serialized dict.
2.  **ORM Objects in Templates:** The most critical anti-pattern. Passing `user` (an instance of `models.User`) directly to `render_template()`. This leads to hidden N+1 queries when the template iterates over `user.comments`.
3.  **HTML in Serializers:** Returning structural markup from a serializer (e.g., `{"title": "<b>My Title</b>"}`). HTML structure belongs entirely in the Jinja templates.
4.  **Implicit Lazy Loading:** Allowing a serializer to trigger hundreds of queries because the relationship was not eagerly loaded in the `query_service` beforehand. Always `joinedload` or `selectinload` what you plan to serialize.
