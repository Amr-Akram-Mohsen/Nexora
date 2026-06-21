# Sources & Content Ingestion — Architecture Analysis

> **Scope:** Visibility, administration, analytics, and operational monitoring.  
> No ingestion pipeline redesign. No code generation.

---

## 1. Source Inventory

### What exists in the schema

| Field | Model | Notes |
|---|---|---|
| `id`, `name`, `slug`, `domain` | `Source` | Core identity |
| `logo_url` | `Source` | Present but unused in admin UI |
| `is_active` | `Source` | Drives `failed` status in list view |
| `authority_score` | `Source` | Integer 0–100, list sorted by it descending |
| `article_sources` | `Source → ArticleSource` | One-to-many relationship to individual publication records |
| `source_id` | `Content` | FK to `sources.id`; nullable |
| `ingestion_origin` | `Content` | String (e.g. `"rss"`, `"newsapi"`), indexed |
| `ingested_at` | `Content` | Timestamp; aggregated in list view |

### What the admin currently surfaces

The `_fetch_sources_page()` helper ([providers.py L39-L117](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/admin/providers.py#L39-L117)) computes, per source, per page:

- `content_count` — total content rows
- `latest_ingested_at` — freshness signal
- `engagement` — sum of `view + like + dislike + save + comment` counts
- `last_crawl`, `success_count`, `failure_count`, `success_rate` — from `LastAPIFetch`
- A derived `status` badge: `healthy / warning / failed`

The `build_source_inspect_data()` function ([providers.py L368-L411](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/admin/providers.py#L368-L411)) adds:

- `avg_quality_score`, `avg_word_count` — from Article
- `scraped_count`, `scrape_coverage` — % of articles with full text
- `published date range` — min/max `published_at`

---

## 2. Source Relationship Mapping

### Dual-source architecture (a subtle complexity)

Articles implement a **multi-source relationship** via `ArticleSource` ([relationships.py L60-L77](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/domains/relationships.py#L60-L77)).  
A single article can be attributed to **multiple publishers simultaneously**, with:

- `url` — source-specific canonical URL
- `published_at` — source-specific publication timestamp
- `primary_source_id` (on Article) — materialized winner from authority + recency logic ([article.py L56-L69](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/domains/content/models/article.py#L56-L69))

Simultaneously, `Content.source_id` is a **flat FK** that also points to a source.

### The mapping gap

| Relationship | Used in analytics? | Used in admin? |
|---|---|---|
| `ArticleSource.published_at` per source | ❌ No | ❌ No |
| `ArticleSource.url` per source | ❌ No | ❌ No |
| Secondary / alternative source attributions | ❌ No | ❌ No |
| `Article.primary_source` winner logic | ❌ No | ❌ No |
| Cross-source article syndication patterns | ❌ No | ❌ No |

The multi-source data exists but is completely invisible. Every admin view treats each article as if it belongs to a single source, discarding co-attribution data.

---

## 3. Source Coverage Analysis

### Category coverage

`Content.category_id` + `Content.source_id` are both indexed, making per-category source distribution queries trivially cheap. No admin view currently exposes this.

**Gap:** No visibility into which categories are dominated by a single source (concentration risk), which categories have zero sources, or which sources cover which content verticals.

### Content type coverage

`Content.object_type` (`article / video / post`) is indexed. No view breaks source contribution down by content type.

**Gap:** Cannot see, for example, that Reuters contributes exclusively articles while YouTube contributes all videos, or which sources produce zero non-article content.

### Ingestion origin × source mapping

`Content.ingestion_origin` records the channel (`rss`, `newsapi`, `gnews`, `reddit`, `youtube`) for every content row. `Content.source_id` records the publisher. These two are **never joined in any admin view**.

**Gap:** Cannot see, for example, that The Verge content arrives via RSS and also via NewsAPI, creating potential duplicates, or that a source is reachable through only one channel (single-point-of-failure risk).

### Authority score distribution

`authority_score` is sorted upon but **never visualized**. No histogram, no tier segmentation (e.g., tier-1: 80+, tier-2: 50–79, tier-3: <50).

---

## 4. Ingestion Visibility Analysis

### What `LastAPIFetch` actually contains

| Field | Meaning |
|---|---|
| `section` | Content section/vertical queried |
| `query_text` | Raw query string used |
| `normalized_query` | Normalized version for dedup |
| `last_fetched_at` | When the fetch occurred |
| `category` | Category targeted |
| `source` | Ingestion channel name (`newsapi`, `rss`, etc.) |
| `etag` / `last_modified` | HTTP conditional fetch support |
| `failure_count`, `consecutive_failures` | Per-query failure tracking |
| `success_count` | Per-query success counter |
| `last_failed_at`, `last_error` | Last failure details |
| `is_active` | Whether the fetch config is active |

### What `APIUsage` contains

| Field | Meaning |
|---|---|
| `date` | Calendar date |
| `api_name` | Channel name (`newsapi`, `gnews`, `youtube`, `reddit`) |
| `request_count` | Requests made on that date |

### Current admin use of ingestion data

The `ingestions.py` file ([ingestions.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/admin/ingestions.py)) exposes only two endpoints:
- `/status` — per-channel: `requests_today`, `last_fetch`, `errors`
- `/logs` — 15 most recent `LastAPIFetch` rows

### Critical gaps in ingestion visibility

| Signal | Data Exists? | Surfaced? |
|---|---|---|
| Per-channel request volume over time (daily trend) | ✅ `APIUsage.date + request_count` | ❌ No |
| Per-channel success rate | ✅ `sum(success) / sum(success+failure)` | ❌ No |
| Consecutive failure detection | ✅ `consecutive_failures` | ❌ No |
| Last error message | ✅ `last_error` | ❌ No |
| Per-query/section fetch coverage | ✅ `section + category` | ❌ No |
| Stale fetch detection (last_fetched_at > threshold) | ✅ `last_fetched_at` | ❌ No |
| `is_active` disabled fetch configs | ✅ `LastAPIFetch.is_active` | ❌ No |
| Conditional fetch hit rate (etag reuse) | ✅ `etag + last_modified` | ❌ No |
| Content yield per fetch (content ingested ÷ fetches) | ✅ join with Content | ❌ No |
| API quota burn rate (requests vs daily limit) | ✅ `APIUsage` | ❌ No (no limit defined) |

---

## 5. Source List View — Improvement Opportunities

### Currently rendered columns
`name/domain link | content count | last crawl | success rate | failure count | engagement | status badge`

### Missing columns (all computable from existing data)

| Column | Source | Value |
|---|---|---|
| **Authority Tier** | `authority_score` | Visual badge: Tier 1 / 2 / 3 |
| **Content Types** | `Content.object_type` group count | Sparkline: Art / Vid / Post breakdown |
| **Category Spread** | `Content.category_id` distinct count | How many categories this source covers |
| **Ingestion Channels** | `Content.ingestion_origin` distinct values | Chip list: RSS, NewsAPI, GNews |
| **Avg Quality** | `Article.quality_score` avg | Inline score indicator |
| **Freshness Gap** | `now() - max(ingested_at)` | "3 hours ago" vs "14 days ago" |
| **Consecutive Failures** | `LastAPIFetch.consecutive_failures` max | Alert if > 3 |

### Filter opportunities (all indexed)
- Filter by status badge (healthy / warning / failed)
- Filter by authority tier
- Filter by ingestion channel
- Filter by category
- Filter by content type

---

## 6. Source Inspect Page — Improvement Opportunities

### Current inspect fields
`id | name | slug | domain | status | authority score | content count | article count | avg quality | avg word count | scrape coverage | published date range`

### Gaps in the inspect page

**Identity section**
- `logo_url` is stored but never rendered in the inspect panel
- No link to the live domain (it is shown in the list but not inspect)

**Multi-source relationship section (entirely missing)**
- How many distinct articles cite this source as primary vs secondary
- Authority rank among all sources that share the same articles
- Syndication partner list (other sources that co-publish the same articles)

**Ingestion channel breakdown (entirely missing)**
- Which channels (`ingestion_origin`) feed this source
- Per-channel success rate for this source
- Last error message per channel

**Content quality breakdown (partial)**
- `avg_quality_score` shown, but no distribution (low / medium / high buckets)
- No scrape failure rate (failed attempts vs success)
- `Article.status` distribution (`pending / enriching / complete / failed`) — fully exists, not shown
- `Article.content_source` — where scraped content came from

**Engagement breakdown (missing)**
- Currently engagement is a single aggregated integer in the list
- Inspect shows nothing on engagement
- Per-content-type engagement breakdown
- Top-performing articles from this source (by view count)

**Temporal activity (missing)**
- Monthly content volume trend (12-bar histogram)
- Average articles per day/week

---

## 7. Source Analytics Opportunities

All queries listed below are directly expressible from indexed existing columns.

### 7.1 Source Contribution Analysis
- **Share of total corpus** — each source's `content_count / total_content_count` as a percentage
- **Authority-weighted contribution** — `content_count × authority_score` normalized
- **Source concentration index** — Herfindahl-style score: does one source dominate a category?

### 7.2 Source Quality Analysis
- **Quality tier distribution** — histogram of `avg_quality_score` across all sources
- **Scrape coverage leaderboard** — ordered by `scraped_count / content_count`
- **Word count distribution** — histogram of `avg_word_count` per source
- **Enrichment backlog** — articles in `pending/enriching` status per source

### 7.3 Source Activity Analysis
- **Publication velocity** — average articles per day over last 30 days per source
- **Freshness index** — `now() - max(ingested_at)` per source, flagging sources silent >7 days
- **Dormant source list** — sources with `is_active=True` but no content in last 30 days

### 7.4 Source Relationship Analysis
- **Co-attribution frequency** — which pairs of sources are most often cited in the same article
- **Primary source win rate** — when two sources co-attribute, which one wins `primary_source_id` most often (authority validation signal)
- **Multi-source article count** — articles with ≥2 `ArticleSource` records (syndication signal)

---

## 8. Ingestion Analytics Opportunities

### 8.1 Channel Performance Dashboard
- **Daily request volume per channel** — 30-day line chart from `APIUsage`
- **Cumulative success vs failure per channel** — stacked bar from `LastAPIFetch` aggregates
- **Channel success rate trend** — rolling 7-day success rate per `source`
- **Content yield rate** — `content_count / success_count` (how many articles per successful fetch)

### 8.2 Ingestion Distribution
- **Channel distribution of content corpus** — pie/bar: what % of all content came from RSS vs NewsAPI vs GNews
- **Channel × Category heatmap** — which channels supply which categories
- **Channel × Source matrix** — which publishers are reachable via which channels
- **Temporal ingestion heatmap** — hour-of-day × day-of-week activity from `ingested_at`

### 8.3 Health & Alerting Signals
- **Consecutive failure leaderboard** — `LastAPIFetch` rows ordered by `consecutive_failures desc`
- **Last error log** — surface `last_error` text per fetch config; currently stored, never shown
- **Stale fetch detection** — fetch configs where `last_fetched_at` is older than expected cadence
- **Inactive fetch configs** — `LastAPIFetch.is_active = False` records with a visible count

### 8.4 API Budget & Quota Analytics
- **Quota burn rate** — `APIUsage.request_count` trend vs a configurable daily limit
- **Burst detection** — days with unusually high request counts
- **Channel cost comparison** — request counts across channels to understand relative API load

---

## 9. Source Health Dashboards

### Recommended: Source Health Summary Card (list page header)

A single row of KPI tiles above the source table:

| Tile | Computation |
|---|---|
| **Total Sources** | `count(sources)` |
| **Active Sources** | `count(is_active = True)` |
| **Healthy** | `count(success_rate ≥ 80 AND content_count > 0)` |
| **Warning** | `count(success_rate < 80 OR content_count = 0)` |
| **Failed/Inactive** | `count(is_active = False)` |
| **Silent (>7d)** | `count(now() - latest_ingested_at > 7 days)` |

### Recommended: Source Quality Ring Chart

Pie segmented by quality tier based on `avg(quality_score)` grouped by source:
- High quality (score ≥ 70)
- Medium quality (score 40–69)
- Low quality (score < 40)

### Recommended: Authority Distribution Histogram

Bar chart of `authority_score` buckets (0–20, 20–40, 40–60, 60–80, 80–100) showing how many sources fall in each tier.

### Recommended: Coverage Gap Matrix

A table of `(category × source)` showing which categories have fewer than N sources, surfacing coverage concentration risks.

---

## 10. Content Acquisition Dashboards

### Recommended: Acquisition Overview Panel (per-channel)

For each ingestion channel: requests today, success rate, last fetch, content produced today, content yield per request.

### Recommended: Ingestion Velocity Chart

30-day stacked area chart of `ingested_at` grouped by `ingestion_origin`. Shows which channels are accelerating or decelerating.

### Recommended: Channel × Category Coverage Heatmap

Grid of `ingestion_origin` (rows) × `category_name` (columns), cell = content count. Reveals which channels cover which verticals and which cells are empty (blind spots).

### Recommended: Article Enrichment Funnel

From `Article.status` distribution:
```
Ingested → Pending → Enriching → Complete
                              → Failed
```
This funnel view exists in data but has no admin surface. It is the most actionable quality signal — shows backlog and failure rate in the enrichment pipeline.

### Recommended: Content Freshness Timeline

A stacked bar showing, per source, content ingested in the last 24h / 7d / 30d / older. Surfaces sources that have gone cold while appearing active.

---

## 11. Existing Data Utilization Score

| Data Asset | Fully Used | Partially Used | Unused |
|---|---|---|---|
| `Source.name/slug/domain` | ✅ | | |
| `Source.is_active` | ✅ | | |
| `Source.authority_score` | | ✅ (sort only) | |
| `Source.logo_url` | | | ❌ |
| `ArticleSource.url` | | | ❌ |
| `ArticleSource.published_at` | | | ❌ |
| `Article.primary_source_id` (winner logic) | | | ❌ |
| `Content.source_id` | ✅ | | |
| `Content.ingestion_origin` | | ✅ (indexed, aggregated in list) | |
| `Content.ingested_at` | | ✅ (freshness signal only) | |
| `Content.object_type` | | | ❌ in source context |
| `Content.category_id` × `source_id` | | | ❌ |
| `Article.quality_score` | | ✅ (avg in inspect) | |
| `Article.word_count` | | ✅ (avg in inspect) | |
| `Article.is_content_scraped` | | ✅ (% in inspect) | |
| `Article.status` (pipeline stage) | | | ❌ |
| `Article.content_source` | | | ❌ |
| `LastAPIFetch.consecutive_failures` | | | ❌ |
| `LastAPIFetch.last_error` | | | ❌ |
| `LastAPIFetch.is_active` | | | ❌ |
| `LastAPIFetch.etag/last_modified` | | | ❌ |
| `APIUsage.request_count` per date | | | ❌ (date-level chart) |

**Estimated utilization: ~28% of available data assets are actively surfaced.**

---

## 12. Phased Implementation Roadmap

### Phase 1 — Source List & Health Hardening *(Low effort, high operational value)*

**Goal:** Make the current list page operationally complete.

1. **Add KPI header tiles** to the sources list: Total / Active / Healthy / Warning / Failed / Silent (>7d). All computable from existing aggregates.
2. **Add `logo_url` rendering** — favicon-style logo column in source list rows. Data already exists.
3. **Add authority tier badge** — derive tier from `authority_score` ranges and render as a chip alongside the name column.
4. **Add freshness gap column** — `now() - max(ingested_at)` as a human-readable duration with color coding.
5. **Add ingestion channel chips** — per source, show which `ingestion_origin` values fed it (a small chip list).
6. **Add `consecutive_failures` alert** — surface from `LastAPIFetch` in the status column tooltip or as a secondary badge.
7. **Add list-level filters** — status filter, authority tier filter, activity filter (active last 7d / 30d / never).

---

### Phase 2 — Source Inspect Page Enrichment *(Medium effort, high diagnostic value)*

**Goal:** Transform the inspect panel from a static fact sheet into an operational diagnostic tool.

1. **Render `logo_url`** in the inspect header alongside source name and domain link.
2. **Add ingestion breakdown section** — per-channel breakdown for this source: channel name, success rate, last fetch, consecutive failures, last error text.
3. **Add content type breakdown** — article / video / post count with proportional bar.
4. **Add category coverage list** — which categories this source contributes to, with item counts.
5. **Add Article pipeline status distribution** — pie or list of `Article.status` counts (pending / enriching / complete / failed) for this source's articles.
6. **Add engagement breakdown** — split engagement total into view / like / save / comment components.
7. **Add top articles panel** — top 5 articles from this source by `view_count`, with title and ingested date.
8. **Add multi-source attribution stats** — count of articles where this source is primary vs secondary attribution.

---

### Phase 3 — Ingestion Health Dashboard *(Medium effort, high operational value)*

**Goal:** A dedicated ingestion health page that surfaces channel-level and query-level health signals.

1. **Channel status grid** — one card per channel (RSS, NewsAPI, GNews, Reddit, YouTube) showing: requests today, success rate (all-time), last fetch, consecutive failures, last error, active fetch configs count.
2. **API quota burn chart** — 30-day line chart per channel from `APIUsage`. Requires a configurable daily limit constant per channel.
3. **Inactive fetch configs panel** — `LastAPIFetch.is_active = False` rows with section, query, last failure info.
4. **Stale fetch detector** — rows where `last_fetched_at` is older than expected cadence by channel type, listed as a table.
5. **Last error log expansion** — expand the 15-row log to show `last_error` text, `consecutive_failures`, and `last_failed_at`.
6. **Channel × category coverage table** — which section+category combinations each channel serves.

---

### Phase 4 — Source & Acquisition Analytics *(Higher effort, strategic value)*

**Goal:** Trend, distribution, and comparative analytics for content strategy decisions.

1. **Content acquisition velocity chart** — 30-day stacked area chart of `ingested_at` grouped by `ingestion_origin`.
2. **Source contribution analysis** — share-of-corpus table and bar chart. Top N sources by volume, quality, and engagement.
3. **Authority distribution histogram** — bar chart of source count by authority score bucket.
4. **Category × source coverage matrix** — heatmap showing which sources cover which categories and where gaps exist.
5. **Ingestion channel × category heatmap** — which channels feed which verticals.
6. **Article enrichment funnel** — funnel visualization of `Article.status` pipeline stages across all sources and per source.
7. **Source dormancy tracker** — sources with `is_active=True` but no new content in >7d, >14d, >30d.
8. **Multi-source syndication map** — which articles have ≥2 `ArticleSource` attributions and which source pairs co-attribute most frequently.

---

### Phase 5 — Quality & Freshness Monitoring *(Data-driven long term)*

**Goal:** Automate quality signal surfacing and freshness alerting.

1. **Quality tier leaderboard** — ranked source list by `avg(quality_score)` with tier segmentation.
2. **Scrape coverage leaderboard** — sources ordered by `is_content_scraped` percentage, identifying enrichment gaps.
3. **Content freshness index** — per-source freshness derived from `max(ingested_at)`, visualized as a timeline or ranked table with staleness severity.
4. **Per-source word count distribution** — histogram per source to identify thin-content suppliers.
5. **Ingestion yield rate tracking** — `content produced / fetch attempts` per channel, trended over time to catch degradation.

---

## Architectural Notes

### The `ingestion_origin` / `source` naming inconsistency

`Content.ingestion_origin` (the channel: rss, newsapi, etc.) and `LastAPIFetch.source` (also the channel name) use the same semantic but different column names. The providers.py list view joins them via `LastAPIFetch.source = Source.slug` (lowercased), which is fragile — a slug rename would silently break all fetch health data for that source. This is a correctness risk to document, not a redesign task.

### The `Content.source_id` vs `ArticleSource` dual-attribution model

Content carries a flat `source_id` FK while Article carries a rich multi-source `ArticleSource` relationship. These two systems are not synchronized in any verified way by the admin. The inspect page uses `Content.source_id` for aggregates, while `ArticleSource` data is unused in analytics. A future consolidation could derive `Content.source_id` from `Article.primary_source_id` via the `ArticleSource → Source` chain, but that's a pipeline concern, not an admin concern.

### `APIUsage` has no daily limit constants

`APIUsage.request_count` is tracked per day per channel, but there is no stored daily limit to compare against. Quota burn analytics require either a hardcoded limit map in the admin config or a `ChannelConfig` table (future). Phase 3 can proceed with configurable constants in the admin layer.
