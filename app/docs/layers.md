# Architecture Refinement Guidelines

## Current State

The project already follows a relatively mature layered structure and many architectural concerns are already implemented correctly.

The following are already largely enforced and should NOT be unnecessarily rewritten:

* routes are mostly thin
* Flask request/session/flash logic is mostly isolated to routes
* business/domain logic is mostly outside routes
* application workflows already exist
* integrations are already separated
* reusable domain services already exist
* content/item/recommendation domains are already modularized

This refinement phase is NOT intended to redesign the architecture from scratch.

The goal is to:

* improve consistency
* reduce duplication
* improve maintainability
* improve debugging experience
* improve query efficiency
* improve caching strategy
* improve serializer consistency
* improve workflow clarity
* reduce hidden coupling
* improve long-term scalability

---

# Architectural Direction

## Domain Layer (`domains/*`)

The domain layer owns:

* business rules
* query composition
* ranking/scoring logic
* reusable domain operations
* normalization logic
* filtering logic
* reusable serializers
* reusable domain services

Examples:

* filtering.py
* ranking.py
* normalization.py
* query.py
* command.py

The domain layer should remain reusable and framework-independent.

The domain layer already appears reasonably separated and should mainly receive refinement rather than large restructuring.

---

# Application Layer (`application/*`)

The application layer owns:

* workflows
* orchestration
* assembling page/view data
* coordinating multiple domain services
* ingestion workflows
* enrichment workflows
* page/feed assembly
* interaction workflows

Examples:

* get_item_page.py
* get_feed.py
* workflows/ingestion.py
* workflows/enrichment.py

The application layer should focus on orchestration rather than implementing reusable low-level business logic.

---

# Web Layer (`web/routes/*`)

The web layer owns:

* request parsing
* route definitions
* session/cookie handling
* response generation
* template rendering
* calling application workflows

The routes are already relatively thin and should mainly be refined for consistency and maintainability.

Avoid moving business/query logic into routes.

---

# Integration Layer (`integrations/*`)

The integration layer owns:

* external API communication
* RSS/API fetching
* scraping/parsing
* external transport logic
* fetch runners
* provider adapters

The integration layer should avoid owning orchestration-heavy workflows.

Integrations should provide data acquisition and transport functionality, while orchestration should remain in the application layer.

---

# Refinement Priorities

## 1. Reduce Duplication

Inspect for:

* repeated query patterns
* repeated serializer logic
* repeated pagination logic
* repeated filtering logic
* repeated enrichment steps
* repeated interaction handling
* repeated template preparation logic

Extract reusable abstractions only where they improve clarity and maintainability.

Avoid premature abstraction.

---

# 2. Improve Query Efficiency

Inspect for:

* N+1 queries
* repeated eager-loading definitions
* duplicated joins
* redundant database access
* repeated recommendation queries
* serializer-triggered lazy loads
* unnecessary ORM hydration

Prefer:

* reusable eager-loading configurations
* reusable query composition helpers
* batched loading
* efficient relationship loading
* query reuse across workflows

---

# 3. Improve Caching Strategy

Caching should primarily live at:

* application workflow boundaries
* reusable domain query/service boundaries

Avoid route-level caching except for very simple static responses.

Inspect for opportunities to:

* centralize cache keys
* improve cache invalidation
* avoid duplicated cache logic
* avoid stale query behavior
* cache expensive recommendation/feed operations
* cache repeated aggregation queries
* improve memoization consistency

Infrastructure/cache should remain implementation-oriented.

Application/domain layers may coordinate caching behavior.

---

# 4. Improve Serializer Consistency

Inspect serializers for:

* inconsistent output structures
* duplicated formatting logic
* template-specific formatting leaking into domains
* repeated transformation logic
* inconsistent naming conventions

Prefer:

* reusable serializer contracts
* predictable output structures
* serializer reuse across feeds/pages/APIs

Avoid tightly coupling serializers to templates where possible.

---

# 5. Improve Workflow Clarity

Inspect application workflows for:

* oversized orchestration functions
* hidden coupling
* unclear responsibility boundaries
* duplicated workflow steps
* unnecessary cross-domain dependencies

Prefer:

* composable orchestration
* clear workflow boundaries
* reusable domain operations

---

# 6. Evaluate Ingestion Workflow Organization

Some ingestion-related files currently exist directly under:

* application/content/*
* application/item/*

Evaluate whether ingestion-heavy logic would be clearer if grouped into dedicated workflow namespaces such as:

* application/content/workflows/*
* application/workflows/content_ingestion/*
* application/workflows/item_ingestion/*

This is a refinement consideration, not a mandatory rewrite.

The goal is improved workflow discoverability and maintainability.

Do NOT move orchestration-heavy ingestion workflows into integrations.

Integrations should remain transport/provider focused.

---

# 7. Preserve Existing Good Patterns

Avoid unnecessary rewrites of systems that are already reasonably separated.

This refinement phase should prioritize:

* consistency
* maintainability
* debugging clarity
* scalability
* operational clarity

rather than architectural churn.
