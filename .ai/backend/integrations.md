# Integrations & Ingestion Architecture

The `app/integrations` directory acts as an Anti-Corruption Layer between Nexora and the chaotic outside world. It is responsible for ingesting content, syncing commercial items, communicating with external APIs, and enriching raw data before it ever touches the core domains.

## Core Philosophy

*   **Anti-Corruption:** External data structures (RSS XML, scraped HTML, Amazon JSON schemas) must never leak into the Domain Layer. Integrations must map external data into standardized internal DTOs (`app/shared/dto/ingestion.py`) before processing continues.
*   **Asynchronous by Default:** Fetching data from the internet is slow and prone to failure. All ingestion and synchronization tasks must run asynchronously (via background workers/schedulers) and never block a web request.
*   **Dependency Inversion:** The Domain Layer must *never* import from `app/integrations`. If a Domain requires external data, the Application Layer or Scheduler must fetch it via the Integration and pass it down into the Domain.

---

## Ingestion Architecture

The ingestion process is strictly separated into distinct phases to maximize testability and fault tolerance.

### 1. Discovery & Fetching
*   **Location:** `integrations/{domain}/fetcher_runners/` and `integrations/{domain}/core/`
*   **Responsibility:** Finding new URLs or executing API calls. Handles rate limiting, proxies, and HTTP sessions.
*   **Channels:** Data enters via specific channels:
    *   `rss.py`: Standardized XML feed parsing.
    *   `api.py`: Structured JSON from official providers (e.g., YouTube API).
    *   `scrapers/`: Fallback HTML parsing when APIs are unavailable.

### 2. Extraction & Normalization
*   **Location:** `integrations/content/utilities/`
*   **Responsibility:** Converting the raw payload into a unified internal format.
*   **Source Normalization:** Cleans malformed HTML (`cleaner.py`), resolves relative URLs to absolute, standardizes date strings, and maps external categories to internal Taxonomy slugs.

### 3. The Enrichment Pipeline
*   **Location:** `integrations/content/enrichment/pipeline.py`
*   **Responsibility:** Enhancing the raw text.
    *   `classification.py`: Assigning categories based on text NLP.
    *   `brand_detector.py` / `facet_detector.py`: Extracting entities and tagging the content for better recommendations.
*   **Rule:** Enrichment should be idempotent. If the pipeline crashes halfway, it should be safe to run again on the same content.

### 4. Persistence
*   **Responsibility:** Once normalized and enriched, the Integration passes the finalized DTO to an Application Layer workflow (e.g., `app/application/content/workflows/ingestion.py`) to actually save the data using Domain Services.

---

## Commercial Synchronization

Commercial integrations (`integrations/commercial/`) require strict synchronization rules due to pricing and availability volatility.

*   **Providers:** Separated into distinct modules (`amazon.py`, `aliexpress/`, `noon.py`). Each provider implements a common interface for fetching catalog updates and single-item price checks.
*   **Synchronization Cadence:** Stale items must be refreshed based on their popularity. High-traffic items require frequent syncing; low-traffic items can decay into slower sync cycles.

---

## Error Handling, Retries, and Scheduling

External systems will fail. The architecture must anticipate this.

### Retries & Exponential Backoff
*   Transient errors (HTTP 502, 504, 429 Rate Limit) must trigger a retry mechanism with exponential backoff.
*   Fatal errors (HTTP 404, 403 Forbidden) must halt the fetch and log the failure immediately.

### Scheduling (`scheduler.py`)
*   The scheduler is responsible for triggering ingestion runners on a cron-like schedule.
*   **Health Tracking:** Every provider/source has a "Health Score" or "Consecutive Failures" counter stored in the database. If a source fails repeatedly, the scheduler must automatically disable it or reduce its fetch frequency to prevent systemic resource drain.

---

## Integration Boundaries & Rules

1.  **Never Return UI:** Integrations must never return HTML, render templates, or concern themselves with how the data will be displayed.
2.  **No Core Business Rules:** Integrations do not decide if an article is "Trending" or calculate final Engagement Scores. They only provide the raw metrics (e.g., "This YouTube video has 10,000 views"); the Domain Layer calculates the score.
3.  **Strict Timeouts:** Every HTTP call must have a strict timeout (e.g., `timeout=10`). A hanging external API must not lock up a worker thread indefinitely.

## Anti-Patterns

1.  **Leaky Abstractions:** Passing a raw `BeautifulSoup` object or a specific API payload directly into a Domain Service.
2.  **Synchronous Fetches:** Triggering a heavy scrape or API fetch directly from a web route while the user waits for the page to load.
3.  **Silent Failures:** Using broad `except Exception:` blocks that swallow errors without logging the specific URL and Provider that failed.
