# Nexora Backend Conventions

This document defines the preferred backend implementation conventions for Nexora. All future backend modifications, additions, and refactorings must adhere to these guidelines to ensure architectural consistency, clean dependencies, query efficiency, and maintainable workflows.

---

## 1. Domain Services

### Service Organization
* Place domain services under `app/domains/<domain>/service/`.
* For simple domains, place logic in single files: `query.py`, `command.py`, `serializers.py`, `search.py`.
* For complex domains (e.g., `content`), structure the query operations into a dedicated sub-package `query/` containing `filtering.py`, `related.py`, `trending.py`, and `utils.py`, exposing them cleanly in `query/__init__.py`.

### Business Logic Placement
* Domain services own all core business rules, entity validations, data mutations, and ranking/filtering algorithms.
* Business logic must remain framework-independent. Do not import Flask packages (`request`, `session`, `g`, etc.) in the domain layer.

### Reusable Operations
* Isolate write operations (creating, deleting, or updating records) into `service/command.py`.
* Command functions should take required identifiers/parameters first and execute logic on the database transaction. They must not perform page-rendering tasks or execute transaction commits (`db.session.commit()`).

### Query Composition
* Queries must be composed using SQLAlchemy 2.0 select statements (`select()`) rather than legacy query syntax (`session.query()`).
* Write dynamic query builders in `service/query.py` or `service/query/utils.py` to compile clauses incrementally.

### Ranking & Filtering Logic
* Perform expensive scoring or filtering operations directly at the database level using SQL expressions (e.g., `case`, `sum`, `func.coalesce`, `extract`) rather than in Python memory loops (see scored queries in [content.py](file:///app/domains/recommendation/service/content.py)).

---

## 2. Application Workflows

### Orchestration Patterns
* Application services orchestrate workflows by coordinating multiple domain services and integrations (e.g., loading a detail model, fetching its related recommendations, and saving a view interaction).
* Orchestrators are placed under `app/application/<domain>/<use_case>.py` (e.g., [get_item_page.py](file:///app/application/item/get_item_page.py)).

### Workflow Composition
* Orchestration functions should remain flat and linear.
* Keep orchestrators focused on coordinating data flows and caching. They must not contain lower-level SQL generation or business validation rules.

### Cross-Domain Coordination
* When a workflow requires entities from multiple domains (e.g., matching items with recommendation scoring), import their respective domain service queries rather than accessing the foreign database models directly.

### Page Assembly
* Page-level view model builders compile final dictionary payloads matching template requirements. 
* Always enforce safety defaults (e.g., `data.setdefault("items", [])`) on return structures to prevent rendering issues in templates.

---

## 3. Routes

### Route Responsibilities
* Keep routes extremely thin (typically under 30 lines).
* Routes must only handle incoming requests, parse inputs, call application workflows, handle session/auth context, commit database writes, and render responses.

### Request Parsing
* Extract parameters (e.g., query strings, lists, pagination values, content types) at the start of the route handler. 
* Use type validation when parsing values from request args:
  ```python
  page = request.args.get("page", 1, type=int)
  ```

### Validation
* Rely on validation schemas or model constraints at the domain level. 
* For route-level guards, perform check evaluations and abort early using standard Flask HTTP exceptions (e.g., `abort(404)`).

### Response Generation & Rendering Patterns
* Return responses by rendering templates via Flask's `render_template` or as JSON payloads via `jsonify`.
* Always pass pre-serialized, unified data structures to templates rather than raw ORM models to avoid lazy-loading exceptions.

---

## 4. Models

### Model Organization
* Place model definitions under `app/domains/<domain>/models.py` (or inside a `models/` directory for complex domains).
* Define tables explicitly inheriting from `db.Model`.

### Relationship Conventions
* Configure relationships with cascading deletions (`cascade="all, delete-orphan"`) and appropriate lazy-loading options:
  * Use `lazy="selectin"` for collections likely to be accessed during rendering (e.g., variants, specs, images) to batch-load them.
  * Use `lazy="noload"` for high-volume, dynamic properties like views or comments, which must be loaded explicitly in queries.
* Declare secondary association tables inside a common relationship module: `app/domains/relationships.py`.

### Naming Conventions
* Table names must be pluralized (e.g., `"items"`, `"item_variants"`, `"brands"`).
* Column names must follow `snake_case` (e.g., `item_type`, `created_at`).
* Define indexes using the `ix_<table_name>_<columns>` pattern.

---

## 5. Serialization

### Serializer Placement
* Place serializers inside the domain layer at `app/domains/<domain>/service/serializers.py`.
* Define polymorphic or cross-domain object serialization in a central serialization file: `app/domains/serializers.py`.

### Serializer Responsibilities
* Map ORM instances to primitive Python types (dictionaries, lists, strings) to prevent lazy-loading database triggers during template execution or JSON serialization.

### Output Structure Conventions
* Standardize output shapes. Use a polymorphic translator (e.g., `serialize_target` in [serializers.py](file:///app/domains/serializers.py)) to map diverse entities (Article, Video, Post, Item) to uniform fields (`id`, `type`, `title`, `preview_text`, `image_url`) for rendering in shared layout grids.

---

## 6. Database Access

### Query Patterns
* Execute composed statements using database sessions:
  ```python
  stmt = select(Item).where(Item.id == item_id)
  item = session.execute(stmt).scalars().first()
  ```

### Eager Loading Conventions
* Always load related objects explicitly using eager loading options (`joinedload`, `selectinload`, `subqueryload`).
* Match eager load queries to specific profiles defined in `service/options.py`:
  * `minimal`: Basic properties only (e.g., category).
  * `card`: Relationships needed to draw catalog card components.
  * `detail`: Hydrates full specifications, images, and store networks for detail pages.

### Repository/Query Helper Usage
* Place utility helpers in `service/utils.py` (e.g., `build_item_stmt`, `fetch_items`) to deduplicate query initialization.
* Resolve session contexts dynamically inside query helpers. All query helper functions must place `session` as the **last optional parameter**, defaulting to `None`, and fallback to the global `db.session`:
  ```python
  def get_item_by_id(item_id, serialize=False, session=None):
      if session is None:
          from app.core.extensions import db
          session = db.session
      # ... query execution ...
  ```

### Performance Considerations
* Ensure database pagination is handled via statement-based paginate helpers:
  ```python
  pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
  ```
* Avoid raw SQL queries where ORM statements can be composed dynamically.

---

## 7. Caching

### Where Caching Lives
* Caching decorators (`@cache.memoize` or `@cache.cached`) must live strictly at the **Application Layer** or **Domain Query Service** boundaries.

### Cache Ownership
* The Application Layer owns the caching lifecycle. Workflows must define cache TTL times matching their update frequencies.

### Cache Boundaries
* Do not apply cache decorators directly on Flask route endpoints. This isolates caching from session states, flash messages, and dynamic headers.
* Use key normalization to cache queries containing complex arguments, converting dictionary parameter arguments into hashable strings.

---

## 8. Error Handling

### Logging Patterns
* Every web route must log start, success, and error outcomes using the project's standard logging helpers (`log_route_start`, `log_route_success`, `log_route_error`):
  ```python
  try:
      log_route_start(logger, f"/contents/{content_id}")
      # ... execution logic ...
      log_route_success(logger, f"/contents/{content_id}", template="page.html")
  except Exception as e:
      log_route_error(logger, f"/contents/{content_id}", e)
      raise
  ```

### Exception Handling Patterns
* Implement descriptive exceptions inside domain query and command services. Do not catch exceptions silently in domain classes.
* Propagate exceptions up to the Web Layer, allowing the route to handle HTTP mapping (e.g., calling Flask's `abort(404)`).

### Workflow Error Handling
* Application workflows must handle downstream integration failures (e.g., scraper timeouts or network exceptions) gracefully by returning cached fallbacks or partial datasets, logging errors with diagnostic metadata.

---

## 9. Dependency Direction

### Allowed Dependencies
* **Web Layer** can depend on **Application Layer**, **Domain Layer**, and **Integration Layer**.
* **Application Layer** can depend on **Domain Layer** and **Integration Layer**.
* **Domain Layer** has no outer layer dependencies. It can only reference its own sub-packages.
* **Integration Layer** has no outer layer dependencies. It must remain decoupled from database models.

### Forbidden Dependencies
* Lower layers must never import higher layers (e.g., Domain must never import from Web or Application).
* No cross-domain database mutations. If domain A needs to modify domain B, coordinate this transaction through an Application Layer workflow.

### Layer Boundaries

```
┌────────────────────────────────────────────────────────┐
│                        WEB LAYER                       │
│                   (app/web/routes/*)                   │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                   │
│                    (app/application/*)                 │
└───────────────────────────┬────────────────────────────┘
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐   ┌────────────────────────┐
│        DOMAIN LAYER       │   │    INTEGRATION LAYER   │
│     (app/domains/*)       │   │    (app/integrations/*)│
└───────────────────────────┘   └────────────────────────┘
```

---

## 10. AI Assistant Guidelines

### When implementing backend changes:

* **Keep Routes Thin**: Do not write complex logic, query statements, or transaction commit structures inside route handlers. Delegate these to application or domain service modules.
* **Inject Sessions Properly**: Always structure service query signatures with `session=None` as the **last optional parameter**, and resolve it dynamically via `session = session or db.session`.
* **Prevent N+1 Queries**: Never serialize database models that contain lazy-loaded relationships inside loops. Ensure relationships are eager loaded via explicit load option profiles.
* **Pre-Serialize Responses**: Convert database model structures to primitive Python dictionaries in domain serializers before passing them to Flask routes or templates.
* **Isolate Cache Decs**: Never put `@cache.cached` or `@cache.memoize` on Flask route functions. Keep them on Application workflows or Domain Query services.
* **Respect Layered Boundaries**: Check imports to ensure no low-level service references routing frameworks or session state details from Flask.
