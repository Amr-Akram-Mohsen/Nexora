# Admin Backend Architecture

The Admin Backend (`app/admin`) is a specialized presentation layer dedicated exclusively to the internal Nexora dashboard. Unlike the public web routes, the admin layer is optimized for heavy data aggregation, bulk operations, and rapid CRUD inspection.

## Core Philosophy

*   **Fragment-First AJAX:** The admin UI relies heavily on asynchronous loading to feel fast. Instead of returning full HTML pages on every click, many admin endpoints return small Jinja HTML fragments (e.g., an inspect panel or a table row) which the frontend JavaScript injects into the DOM.
*   **Separation from Public Web:** Admin logic is strictly isolated from `app/web`. They do not share controllers.
*   **Thin Controllers:** Admin route functions extract parameters, enforce permissions, and format the response, but delegate all business logic and data fetching to the Domain or Application layers.

---

## Architecture & Endpoints

The `app/admin` directory is divided into module files reflecting administrative domains (e.g., `contents.py`, `users.py`, `insights.py`).

### 1. CRUD Endpoints (List Views)
The primary entry points for data tables.
*   **Responsibilities:** 
    *   Extract pagination (`page`), sorting (`sort_by`, `order`), and filtering parameters from `request.args`.
    *   Call the appropriate Domain Query Service (e.g., `content.service.query.search_contents`).
    *   Fetch the table definition from `app/admin/tables.py` (`CRUD_TABLES`).
    *   Pass the serialized data and the table definition to `render_template`.

### 2. Inspect Endpoints (Detail Views)
Triggered via AJAX when a user clicks a row in a CRUD table.
*   **Route Pattern:** Usually `/admin/{domain}/{id}/inspect`
*   **Responsibilities:**
    *   Fetch a detailed, eagerly-loaded entity from the Domain layer.
    *   Serialize the entity.
    *   Pass the serialized dictionary to `get_inspect_table(table_name, data)` (from `tables.py`) to map it to the standard inspect schema.
    *   Return a rendered `components/_inspect.html` fragment.

### 3. Bulk Operations
Triggered when users select multiple checkboxes in a table and select an action.
*   **Route Pattern:** Usually `POST /admin/{domain}/bulk-action`
*   **Payload:** Expects a JSON payload or form data containing a list of `ids` and the `action_type`.
*   **Responsibilities:** Validate the action, loop through the IDs (or use a bulk update query in the Domain layer), and commit the transaction. Return a JSON success message or an updated HTML table fragment.

### 4. Widget & Chart Endpoints
Endpoints that power the dashboard KPI cards and Chart.js instances.
*   **Responsibilities:** Call analytics domain services (e.g., `analytics/service/trends.py`) to retrieve aggregations.
*   **Response Format:** Often returns pure JSON (`jsonify(data)`) to be consumed by `core/charts.js`, rather than HTML fragments.

---

## Data Flow & Dependencies

### Interactions with the Application Layer
*   **Reads (Queries):** For standard CRUD lists, Admin routes generally bypass the Application layer and call Domain Query Services directly (e.g., `user_service.get_users(filters)`). This is acceptable as long as it's a simple read.
*   **Writes (Commands/Orchestrations):** For complex mutations (e.g., "Run Bulk Ingestion" or "Merge Categories"), the Admin route **must** call an Application Layer workflow to orchestrate the multiple domains involved.

### Serialization Usage
*   Admin routes must **never** format data manually.
*   They rely on the Domain DTO serializers to convert SQLAlchemy models into dictionaries.
*   If an Admin page requires a unique blend of data not covered by standard DTOs, an Admin-specific ViewModel serializer should be constructed (either in the Application layer or locally in a helper within `app/admin/`).

---

## Permissions & Security

*   **Global Enforcement:** Every route within a Blueprint in `app/admin` must be protected. This is typically achieved using a global `before_request` hook on the Admin blueprint, or via strict `@admin_required` decorators on every route function.
*   **CSRF Protection:** All mutating endpoints (POST, PUT, DELETE), including those accessed via AJAX for bulk actions or inline edits, must validate CSRF tokens. The `api.js` frontend script handles appending these automatically.

---

## Response Formatting Standards

1.  **Full Page Load (GET):** Returns `render_template('admin/domain/page.html', ...)` containing the Sidebar, Header, and the main layout.
2.  **Fragment Load (AJAX GET):** Returns `render_template('admin/components/_table_body.html', ...)` without the layout wrapper.
3.  **Data/Action Response (AJAX POST/JSON):** Returns `jsonify({'success': True, 'message': '3 items updated', 'data': {...}})` for chart data or action confirmations.

---

## Anti-Patterns

1.  **Executing SQL in Admin Routes:** Calling `db.session.query(...)` directly in an admin controller. This circumvents domain business rules and validation.
2.  **Duplicating HTML Structure:** Building HTML strings manually in Python (e.g., `return "<tr><td>" + name + "</td></tr>"`) for AJAX responses. Always render a Jinja macro/partial and return the string output.
3.  **Ignoring Table Schemas:** Manually passing random variables to an inspect panel instead of mapping them through `app/admin/tables.py`. This breaks UI consistency.
