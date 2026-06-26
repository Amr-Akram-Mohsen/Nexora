# Domain Services Architecture

The Domain Layer (`app/domains`) is the heart of the Nexora application. Domain Services are where the core business logic, complex queries, and data mutations live. If the Application Layer is the conductor, the Domain Layer is the orchestra.

## Core Philosophy

*   **Rich Domain Model:** The domain is not just a collection of dumb data containers (SQLAlchemy models). It includes the rules, validations, and calculations that govern that data.
*   **Database Encapsulation:** All database queries (`db.session.query`, `.filter()`, `.group_by()`) must be encapsulated within a Domain Service. The Application Layer and Presentation Layer should never write raw queries.
*   **Decoupling:** A Domain Service should primarily interact with its own domain's models. 

---

## Service Organization: CQRS-lite

To prevent massive `service.py` files, Nexora splits domain responsibilities conceptually (and often physically) into Commands and Queries.

### 1. Queries (`query.py` or `query/` module)
*   **Purpose:** Read operations. Fetching data without side effects.
*   **Responsibilities:** 
    *   Building complex SQLAlchemy filters (e.g., `filtering.py`).
    *   Executing aggregations (e.g., `get_top_categories_by_views()`).
    *   Handling search logic (`search.py`).
*   **Rule:** Query functions must never modify database state.

### 2. Commands (`command.py`)
*   **Purpose:** Write operations. Creating, updating, or deleting records.
*   **Responsibilities:**
    *   Validating data against business rules before insertion.
    *   Managing local domain relationships (e.g., linking a new Item to a Category).
    *   Calculating and persisting scores or metadata during updates.
*   **Rule:** Command functions prepare the `db.session`, but generally rely on the Application layer to execute the final `db.session.commit()`.

---

## Specific Responsibilities

### 1. Business Logic and Calculations
Any logic that defines "how the business works" belongs here.
*   *Example:* Calculating an article's `engagement_score` based on likes, views, and shares (`domains/interaction/service/scoring.py`).
*   *Example:* Determining if an item is "Out of Stock" based on inventory thresholds.

### 2. Analytics & Aggregations
Heavy data crunching and statistical analysis.
*   *Location:* Usually in `domains/{domain}/service/analytics.py` or in a dedicated `domains/analytics/` module if the insights span globally.
*   *Responsibility:* Constructing SQLAlchemy `func.sum()`, `func.count()`, and `GROUP BY` queries to return statistical summaries for the Admin dashboards.

### 3. Validation
Ensuring data integrity *before* it hits the database constraints.
*   *Responsibility:* Checking if a provided Category slug is unique within the domain, or verifying that a Product has a valid price before marking it "active".

### 4. Ingestion & Normalization
While the `app/integrations` layer fetches the raw JSON from an external API (like Aliexpress or a RSS feed), the Domain Layer provides the services to adapt that raw data into the Nexora schema.
*   *Location:* E.g., `domains/content/service/normalization.py`.
*   *Responsibility:* Cleaning HTML text, standardizing date formats, mapping external categories to internal Taxonomies.

---

## What Belongs in Domain Services

✅ **DO Put Here:**
*   SQLAlchemy queries (`session.query(Model)`).
*   Scoring algorithms and ranking logic.
*   Validation rules (e.g., "A post must have at least 10 words").
*   Deduplication logic.
*   Data normalization (stripping HTML from descriptions).

## What MUST NEVER Belong in Domain Services

❌ **DO NOT Put Here:**
*   **HTTP Context:** Never import `flask.request` or `flask.current_app`. Domain services must be callable from a background Celery task or a CLI script just as easily as from a web route.
*   **HTML/Presentation Logic:** Never return HTML strings, CSS classes, or UI-specific text (e.g., returning "Oops, something went wrong!" instead of raising a `ValueError`).
*   **Serialization Rules:** While the domain *directory* contains `serializers.py`, the *services* themselves should ideally return domain models or raw scalars, allowing the Application Layer or Route to decide if/when serialization is needed.
*   **Heavy Cross-Domain Orchestration:** If a service method needs to save an Item, fetch a User, send an Email, and update Content stats, it has become an Application Workflow. Move it to `app/application`.
