# Nexora Engineering Handbook

Welcome to the Nexora Engineering Handbook. This document serves as the master index and navigation guide for the authoritative engineering standards of the Nexora project. 

This handbook represents the **target architecture**. Whenever there is a discrepancy between the current codebase and the rules defined in these documents, the handbook is the ultimate source of truth, and the code must be refactored to comply.

**Purpose:** This handbook exists to eliminate architectural ambiguity, prevent technical debt, and provide a strict blueprint for both human developers and AI assistants contributing to Nexora.

---

## 1. Core Architecture
Start here. These documents define the high-level philosophy, boundaries, and global standards that apply universally across the entire project.

*   **[Project Architecture](architecture/project-architecture.md)**
    *   *Purpose:* Defines the layered, Domain-Driven philosophy, layer responsibilities, data flow, and the HTTP request lifecycle.
    *   *When to consult:* When planning a new feature or determining which directory a new module belongs in.
*   **[Dependency Rules](architecture/dependency-rules.md)**
    *   *Purpose:* Maps the allowed dependency graph and explicitly outlaws circular dependencies and cross-boundary violations.
    *   *When to consult:* When you need to import a file from another layer and want to ensure you aren't breaking encapsulation.
*   **[Naming Conventions](architecture/naming-conventions.md)**
    *   *Purpose:* Standardizes casing (`snake_case`, `PascalCase`, `kebab-case`) across Python, JS, CSS (BEM), HTML, and URLs.
    *   *When to consult:* Whenever creating a new file, variable, class, or CSS component.

---

## 2. Backend Engineering
These documents define the Python backend, enforcing strict separation between business logic, orchestration, presentation, and external systems.

*   **[Domain Services](backend/domain-services.md)**
    *   *Purpose:* Defines the core business logic layer, CQRS-lite queries/commands, validations, and the absolute prohibition of HTTP context.
    *   *When to consult:* When writing complex database aggregations, scoring algorithms, or data mutations.
*   **[Application Layer](backend/application-layer.md)**
    *   *Purpose:* Details the orchestrator pattern, transaction boundaries, and how cross-domain use cases are managed.
    *   *When to consult:* When a feature requires coordinating multiple domains or triggering side effects.
*   **[Serialization](backend/serialization.md)**
    *   *Purpose:* Explains the boundary between raw ORM objects and the presentation layer, defining DTOs and ViewModels.
    *   *When to consult:* When preparing data to be passed to a Jinja template or returned as JSON.
*   **[Public Web Routes](backend/web.md)**
    *   *Purpose:* Covers the architecture of customer-facing endpoints, SEO requirements, caching, and delegation to the Application Layer.
    *   *When to consult:* When adding a new public page or adjusting feed filters.
*   **[Admin Backend](backend/admin.md)**
    *   *Purpose:* Defines the data-dense, fragment-first AJAX backend used exclusively for the management dashboard.
    *   *When to consult:* When building bulk actions, new CRUD endpoints, or dashboard widget endpoints.
*   **[Integrations (Anti-Corruption)](backend/integrations.md)**
    *   *Purpose:* Details the ingestion pipeline, source normalization, scheduling, and boundaries preventing external schema leaks.
    *   *When to consult:* When adding a new API provider, scraper, or modifying synchronization tasks.
*   **[Shared Utilities](backend/shared.md)**
    *   *Purpose:* Defines the agnostic foundational layer for pure functions, constants, and formatting tools.
    *   *When to consult:* When you want to extract a reusable utility function without violating domain boundaries.

---

## 3. Frontend Engineering
These documents define the presentation layer, focusing on server-side rendering, component-driven design, and vanilla technologies.

*   **[Jinja Templates](frontend/templates.md)**
    *   *Purpose:* Defines the component-driven macro architecture, domain isolation, and the "dumb template" rendering rules.
    *   *When to consult:* When structuring a new HTML view or creating a reusable UI component.
*   **[CSS Architecture](frontend/css.md)**
    *   *Purpose:* Outlines the Vanilla CSS strategy, strict BEM methodology, ITCSS layering, and responsive design tokens.
    *   *When to consult:* When styling a component, tweaking layouts, or managing theme variables.
*   **[JavaScript Architecture](frontend/javascript.md)**
    *   *Purpose:* Formalizes the Vanilla JS approach, event delegation, HTML fragment injection, and anti-patterns (no HTML generation in JS).
    *   *When to consult:* When adding interactivity, fetching AJAX fragments, or binding events.
*   **[Admin UI Design System](frontend/admin-ui.md)**
    *   *Purpose:* The specialized UI standard for the dashboard, including CRUD tables, slide-out inspect panels, and toolbars.
    *   *When to consult:* When designing an Admin interface or configuring `tables.py`.
*   **[Charts & Visualizations](frontend/charts.md)**
    *   *Purpose:* Details the use of the `nexoraCharts` core wrapper, CSS variable integration, and data injection patterns.
    *   *When to consult:* When rendering analytics or metrics via Chart.js.
