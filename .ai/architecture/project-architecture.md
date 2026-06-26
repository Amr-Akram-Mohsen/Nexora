# Project Architecture

This document defines the architectural philosophy, standards, and rules for Nexora. It serves as the highest authority for the entire codebase. Whenever there is a discrepancy between current implementation and this document, this document is correct, and the implementation must be updated.

## Architectural Philosophy

Nexora embraces a **Layered, Domain-Driven Architecture**. The core philosophy centers on strict Separation of Concerns (SoC) and clear dependency directions.

*   **Domain-Driven Organization:** Code is grouped conceptually by business domain (e.g., `content`, `item`, `recommendation`), rather than technical concern (e.g., all models together, all controllers together).
*   **Separation of Concerns:** Clear boundaries exist between Presentation (Web/Admin), Orchestration (Application), Business Logic (Domain), and External Systems (Integrations).
*   **Thin Routes, Rich Domains:** HTTP routes handle transport; all business logic lives in domain services.
*   **Decoupled Presentation:** Presentation layers (Templates, JSON responses) must only receive simple serialized data structures (Dictionaries), never ORM models.
*   **Dependency Inversion Principle:** Inner layers (like Domain) must never depend on outer layers (like Web or Admin).

## Overall Architecture & Layer Responsibilities

The codebase is strictly separated into the following major layers:

### 1. `app/domains` (The Core)
The heart of the application. It contains the fundamental business logic, data models, and serialization rules.
*   **Responsibilities:** Core business rules, SQLAlchemy ORM models, focused domain services, and serializers.
*   **Must NEVER do:** Handle HTTP requests, interact with Flask request contexts, render HTML, orchestrate complex multi-domain workflows, or depend on external APIs directly.
*   **Allowed Dependencies:** May depend on `app.shared` or `app.infrastructure`. Domains should minimize dependencies on other domains; complex cross-domain interactions belong in the Application layer.
*   **Forbidden Dependencies:** `app.application`, `app.web`, `app.admin`, `app.integrations`.

### 2. `app/application` (The Orchestrator)
The layer responsible for Use Cases and Workflows that span across multiple domains.
*   **Responsibilities:** Orchestrating complex user journeys or system processes. For example, `get_content_page` orchestrates fetching the content (Content Domain), finding related items (Recommendation Domain), and recording the view (Interaction Domain).
*   **Must NEVER do:** Contain core business rules, execute direct database queries, or return HTTP responses.
*   **Allowed Dependencies:** `app.domains`, `app.integrations`, `app.shared`.
*   **Forbidden Dependencies:** `app.web`, `app.admin`.

### 3. `app/web` & `app/admin` (The Presentation Layer)
The HTTP boundary of the application. `app/web` handles public traffic, while `app/admin` handles internal dashboard traffic.
*   **Responsibilities:** Defining routes, parsing HTTP parameters, checking authentication/authorization, invoking Application workflows (or Domain services for simple reads), and rendering templates or JSON.
*   **Must NEVER do:** Contain business logic, execute database queries, orchestrate domain interactions, or format domain objects.
*   **Allowed Dependencies:** `app.application`, `app.domains` (for simple query services), `app.shared`.
*   **Forbidden Dependencies:** `app.integrations`, or modifying `app.domains` state directly without a service.

### 4. `app/integrations` (The Anti-Corruption Layer)
The boundary between Nexora and external systems (e.g., Scrapers, Amazon, AliExpress, RSS Feeds).
*   **Responsibilities:** Fetching external data, parsing external formats, enriching data, scheduling ingests, and adapting external models into Nexora Domain Models.
*   **Must NEVER do:** Contain core internal business rules or present data to users.
*   **Allowed Dependencies:** `app.domains` (to persist mapped data), `app.shared`.
*   **Forbidden Dependencies:** `app.web`, `app.admin`, `app.application` (unless acting as an entrypoint invoking an application workflow).

### 5. `app/shared` (Cross-Cutting Concerns)
Universal utilities shared across the entire project.
*   **Responsibilities:** DTOs, string normalizers, global constants, validation helpers, and agnostic utility functions.
*   **Must NEVER do:** Contain domain-specific business logic or rely on ORM models.
*   **Allowed Dependencies:** Standard libraries, third-party non-domain libraries.
*   **Forbidden Dependencies:** `app.domains`, `app.application`, `app.web`, `app.admin`, `app.integrations`.

---

## Request Lifecycle & Data Flow

A standard HTTP request follows a strict, unidirectional flow:

1.  **HTTP Request** arrives at `app/web/routes/...` or `app/admin/...`.
2.  **Route Layer** parses arguments (e.g., pagination, IDs) and validates the HTTP context.
3.  **Application Layer** is invoked by the route (e.g., `get_content_page_data(content_id)`).
4.  **Domain Services** are coordinated by the Application Layer to fetch necessary data (e.g., fetching article, fetching recommendations).
5.  **Serialization** happens within the Domain layer. Domain models are converted into safe, standard Python Dictionaries before leaving the domain.
6.  **Application Layer** returns an aggregated dictionary context back to the Route.
7.  **Route Layer** passes the dictionary context to `render_template()`.
8.  **Template (`templates/...`)** renders the HTML without any complex logic or lazy-loading queries.

---

## Domain Architecture

Nexora utilizes a Domain-Driven Design (DDD) approach.
*   **Domain Isolation:** Each domain (e.g., `content`, `item`, `recommendation`) owns its own models, services, and serializers.
*   **Service Organization:** Services within a domain are split into focused modules (e.g., `query.py` for reads, `command.py` for writes).
*   **Cross-Domain Communication:** If Domain A needs to interact with Domain B, it should ideally happen via the Application layer. Direct domain-to-domain imports are permitted only for reading localized data (e.g., a simple lookup), but complex orchestrations must be moved up.

---

## Application Layer Responsibilities

The Application Layer exists to prevent Domain Services from becoming bloated orchestrators.
*   **When to use it:** Whenever a request requires data or actions from more than one domain. For example, rendering a catalog page requires Content, Categories, and Recommendations.
*   **When NOT to use it:** For simple, single-domain CRUD operations (e.g., updating a user's name), the Route can call the Domain Service directly.
*   **Orchestration:** It acts as the traffic cop, calling `content.service`, then `interaction.service`, then `recommendation.service`, assembling the final payload.

---

## Serialization Strategy

Serialization is a critical boundary between backend logic and frontend presentation.

*   **Where it belongs:** Inside `app/domains/{domain_name}/serializers.py`.
*   **What it does:** Transforms rich SQLAlchemy models into plain Python dictionaries (`dict`).
*   **Why it exists:** 
    1. Prevents templates from triggering N+1 database queries via lazy-loaded relationships.
    2. Decouples the database schema from the presentation layer.
    3. Provides a clear contract of what data is available to a template.
*   **Presentation Logic:** Formatting (e.g., date formats, currency symbols) belongs in the Presentation layer (Jinja Filters or Frontend JS). Serializers should provide raw, unformatted scalar values (e.g., ISO-8601 strings, floats).

---

## Shared Utilities Philosophy

The `app/shared` directory is strictly for agnostic, reusable code.
*   If a utility function mentions "Article" or "Product", it belongs in a Domain, not Shared.
*   Shared code must be highly testable and possess zero knowledge of the application's business rules.

---

## Architectural Principles

*   **Thin Routes:** A route should never be longer than ~20 lines. If it is, logic needs to be extracted to the Application or Domain layers.
*   **Rich Domain Services:** The "fat" of the application belongs here. All conditional business rules, scoring algorithms, and database mutations live in the domain.
*   **Presentation-Only Templates:** Jinja templates must be completely devoid of business logic. They receive dictionaries and render them. No database queries can be executed from a template.

---

## Anti-Patterns

The following patterns are strictly forbidden in Nexora and must be refactored if encountered:

1.  **Fat Controllers (Routes):** Writing business rules, `if/else` logic based on domain state, or executing raw SQL directly inside `routes/`.
2.  **ORMs in Templates:** Passing SQLAlchemy model instances directly to Jinja templates, resulting in hidden N+1 query performance issues.
3.  **Cross-Domain Spaghetti:** Domain A's service deeply importing and mutating Domain B's models directly. Always use Domain B's service, or better, orchestrate via the Application layer.
4.  **Presentation Logic in Domain:** Returning HTML snippets, UI text, or HTTP Response objects from a Domain Service.
5.  **Circular Dependencies:** Caused by poor layer isolation (e.g., a Domain importing from the Application layer, or Shared importing from a Domain). Dependency direction must always point inward.
