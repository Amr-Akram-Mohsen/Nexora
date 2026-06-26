# Shared Architecture & Utilities

The `app/shared` directory is the foundational layer of Nexora. It houses universally reusable utilities, constants, and data structures. Because it sits at the bottom of the dependency graph, strict rules govern what can and cannot be placed here.

## Core Philosophy: The "Agnostic" Rule

If a function, class, or constant contains business rules specific to a particular domain (e.g., checking if a user has enough points to buy an item), it **must not** be placed in `app/shared`.

*   **Agnostic:** Code in `app/shared` must be completely ignorant of the application's overall business purpose. A string normalizer or an HTML sanitizer should work equally well in Nexora as it would in an entirely different project.
*   **Dependency Bottom:** The Shared layer may import Python standard libraries or generic 3rd-party packages (e.g., `datetime`, `re`, `urllib`). It must **never** import from `app.domains`, `app.application`, `app.web`, or `app.integrations`.

---

## Directory Structure & Responsibilities

### 1. Constants & Enums (`constants/`)
Global enumerations and constant values that multiple domains need to reference to avoid magic strings.
*   *Examples:* `TargetType` (Article, Video, Post, Item), `InteractionType` (Like, Save, Comment).
*   *Rule:* Enum classes should be defined using Python's `enum` module.

### 2. Data Transfer Objects (`dto/`)
Standardized object structures used to pass data across system boundaries, particularly between the Anti-Corruption Layer (`app/integrations`) and the Application Layer.
*   *Implementation:* Use `dataclasses` or simple typed dictionaries.
*   *Example:* `ingestion.py` defines the canonical structure of an incoming article before it is converted into a SQLAlchemy model.

### 3. Utility Functions (`utils/` and root modules)
Pure functions designed for single-purpose transformations.
*   `normalizer.py` / `sanitizer.py`: Removing malicious HTML tags, standardizing Unicode characters, parsing URLs.
*   `slug.py`: Generating URL-safe slugs from strings.
*   `logging.py`: Standardized logging formatters used across the app.
*   *Rule:* Utility functions should ideally be "pure"—given the same input, they always return the same output without causing side effects.

### 4. Background State Helpers (`utils/batch_state.py`, etc.)
Reusable abstractions for managing cursor pagination, rotation states, or batch processing states during background cron jobs.

### 5. Cross-Cutting Decorators (`decorators.py`)
Decorators that provide generic functionality, such as timing execution speed or wrapping functions in generic error handlers. (Note: Auth decorators usually belong in the `web` layer, not `shared`).

---

## Formatting Utilities

Formatting data for presentation (e.g., formatting `$1,000.00`) should generally be handled in the Frontend (Jinja filters or JS).

However, structural formatting (e.g., ensuring a URL always has `https://` or parsing a messy date string into a native `datetime` object) belongs in `app/shared/parsing.py` or `normalizer.py`.

---

## What Belongs in Shared

✅ **DO Put Here:**
*   A function that strips HTML tags from a string.
*   A function that generates a random token.
*   Global enums like `Platform (YOUTUBE, REDDIT, AMAZON)`.
*   Standardized custom Exceptions (e.g., `NexoraValidationError`).

## What MUST NEVER Belong in Shared

❌ **DO NOT Put Here:**
*   SQLAlchemy Base classes or DB session logic (belongs in `app/core` or `app/infrastructure`).
*   Any function that queries the database.
*   Any logic that references a specific domain model (e.g., `def format_article_title(article):` is forbidden; it should be `def format_title(title_string):`).
*   Flask route wrappers that require knowledge of the `User` model.
