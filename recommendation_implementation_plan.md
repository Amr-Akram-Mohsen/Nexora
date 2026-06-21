# Recommendation Intelligence — Analysis & Implementation Plan

> **Analyst Roles**: Senior Recommendation-Systems Analyst · Engagement Analyst · Data Analyst · Admin-Dashboard UX Specialist  
> **Scope**: Visibility, CTR analysis, recommendation performance, quality monitoring, administrative insight  
> **Constraint**: No redesign of recommendation generation logic. No new data models.

---

## 1. Recommendation Data Inventory

### 1.1 Core Data Assets

| Model | Table | Key Fields | Status |
|---|---|---|---|
| `RecommendationImpression` | `recommendation_impressions` | `entity_type`, `context_id`, `entity_ids (JSON)`, `user_id`, `created_at` | ✅ Tracked, **underutilized** |
| `RecommendationClick` | `recommendation_clicks` | `entity_type`, `entity_id`, `context_id`, `user_id`, `created_at` | ✅ Tracked, **underutilized** |
| `UserInterest` | `user_interests` | `user_id`, `target_type`, `target_id`, `interaction_count`, `last_interaction_at` | ✅ Tracked |
| `UserEntityInterest` | `user_entity_interests` | `brand_id`, `category_id`, `topic_id`, `score` | ✅ Tracked |
| `ItemClick` | `item_clicks` | `item_store_link_id`, `referrer`, `user_id`, `country`, `created_at` | ✅ Tracked |
| `content_items` (association) | relationship table | `content_id`, `item_id` | ✅ Tracked, admin-managed |

### 1.2 Recommendation Activity Types

| Type String | Description | Has Impressions | Has Clicks |
|---|---|---|---|
| `related_content` | Suggested articles/guides alongside content | ✅ | ✅ |
| `related_product` | Products shown on content pages | ✅ | ✅ |
| `shop_product` | Primary shop/listing page product slots | ✅ | ✅ |

### 1.3 CTR Computation — What Exists vs. What Is Used

The raw ingredients for a full CTR pipeline are all present:

- **Numerator**: `RecommendationClick` (per entity_type, per context_id, per entity_id)  
- **Denominator**: `RecommendationImpression` (per entity_type, per context_id, entity_ids JSON array)  
- **Proxy signal**: `ItemClick.referrer` (used in `inspect_match` to approximate recommendation-sourced clicks)  

**What is currently computed (in `_summary_cards.html` + insights pipeline)**:
- Overall CTR
- Related Products CTR
- Related Content CTR  
- Shop Products CTR
- Cross-category benchmarking (best/worst category)
- Quality score per rec type and page context
- Diagnoses + action suggestions

**What is NOT computed or surfaced anywhere**:
- Per-context CTR (i.e., which specific article/page drives the most recommendation engagement)
- Per-entity CTR (i.e., which individual recommended item performs best across all contexts it appears in)
- Time-series CTR (trend by day/week — is performance improving or degrading?)
- Impression volume trend (is the recommendation system reaching more/fewer users over time?)
- User-level CTR segmentation (authenticated vs. anonymous users)
- Geographic CTR breakdown (country data exists on `ItemClick`, not surfaced for recommendations)
- Position/slot efficiency (entity_ids is an ordered JSON list — slot 1 vs. slot 4 click-through rates)
- Recommendation density (avg. items per impression set — are recommendation slots being fully populated?)
- Zero-click impression tracking (impressions that generated no clicks at all — cold content)

---

## 2. Recommendation Relationship Mapping

```
Content (article/guide)
    │
    ├──[content_items]──► Item (product)
    │         │
    │         └── RecommendationImpression (entity_type=related_product, context_id=content.{type}/{id})
    │         └── RecommendationClick      (entity_type=related_product, context_id=..., entity_id=item.id)
    │
    └──[RecommendationImpression]──► entity_type=related_content  (context: article viewed)
    └──[RecommendationClick]──────► entity_type=related_content  (target: another article clicked)

Shop Page
    │
    └──[RecommendationImpression]──► entity_type=shop_product
    └──[RecommendationClick]──────► entity_type=shop_product

UserInterest ──► UserEntityInterest (brand/category/topic scores)
    │
    └── Powers recommendation generation (not exposed in admin in any performance-linked way)
```

### Key Gap: The `content_items` Association Table Has No Impression/Click Backlink

The `recommendations.py` admin uses `content.view_count` as the denominator for CTR in `inspect_match`, but `view_count` is a **static denormalized counter**, not the actual impression count for recommendation widgets. This means:

- CTR shown in the inspect modal = `ItemClick (referrer match) / content.view_count`  
- True recommendation CTR = `RecommendationClick / RecommendationImpression` matched on `entity_id` + `context_id`  

**These two numbers can be very different.** A content page may have 5,000 views but the recommendation widget only rendered on 2,000 of them (different scroll depth, A/B variants, page layout differences). Using `view_count` overestimates the denominator, producing deflated CTR figures.

---

## 3. CTR Analysis Opportunities

### 3.1 True Impression-Based CTR (Highest Priority)

**Available data**: Join `RecommendationImpression` ↔ `RecommendationClick` on `entity_type + context_id`.

**Computable metrics** (not yet surfaced in admin):

| Metric | Query Pattern | Value |
|---|---|---|
| Per-context CTR | GROUP BY context_id, entity_type | Identifies which articles drive clicks best |
| Per-entity CTR | GROUP BY entity_id, entity_type | Identifies which recommended items perform best |
| Slot position CTR | JSON array position analysis on entity_ids | Reveals positional bias — do users only click position 1? |
| CTR by user auth status | WHERE user_id IS NULL vs. NOT NULL | Reveals if authenticated users engage differently |
| CTR trend (7d/30d) | DATE_TRUNC(created_at) GROUP BY day | Shows if recommendation quality is improving |
| Impression volume per day | COUNT impressions by day | Detects traffic spikes or dead periods |

### 3.2 Referrer-Based CTR for `ItemClick` (Existing Proxy, Improvable)

The `inspect_match` endpoint already uses `ItemClick.referrer` pattern matching (`%content_type/content_id%`). This is a valid proxy but:

- It conflates all clicks from that content page (not just recommendation widget clicks)
- The pattern `%{object_type}/{object_id}%` can match unrelated referrers if URL formats vary
- It is only shown in the inspect modal — not aggregated at list level

**Opportunity**: Surface per-item referrer-based CTR in the recommendations list view as a sortable column.

### 3.3 Hybrid CTR: Cross-Referencing Both Sources

For any `content_id + item_id` pair in `content_items`:
- **Signal 1**: `RecommendationImpression` where `entity_ids` contains `item_id` and `context_id` matches content
- **Signal 2**: `RecommendationClick` where `entity_id = item_id` and `context_id` matches content
- **Signal 3**: `ItemClick` where `referrer` matches the content URL

All three exist today. Combining them produces a confidence-weighted CTR that is more reliable than any single source.

---

## 4. Context Performance Analysis

### 4.1 Untapped: Context-Level Performance Table

**Currently missing**: Any admin view that answers "Which contexts (pages/articles) generate the most recommendation impressions and clicks?"

**Available data**: `context_id` field on both `RecommendationImpression` and `RecommendationClick`.

The `context_id` follows a pattern like `article/123` or `product/456`. This can be parsed to:
1. Identify the domain type (article, product, shop)
2. Join back to the `Content` table by `object_type + object_id` to get human-readable titles
3. Compute per-context impression volume, click volume, and CTR

**Proposed Context Performance Table columns**:

| Column | Source |
|---|---|
| Context Title | Content.title JOIN on context_id parse |
| Context Type | entity_type |
| Total Impressions | COUNT(RecommendationImpression) |
| Total Clicks | COUNT(RecommendationClick) |
| CTR | clicks / impressions × 100 |
| Unique Users Reached | COUNT(DISTINCT user_id) on impressions |
| Avg Items Per Set | AVG(JSON_ARRAY_LENGTH(entity_ids)) |

### 4.2 Page-Type Distribution

`entity_type` differentiates context buckets (`related_content`, `related_product`, `shop_product`). Comparing CTR across types is already done in `_summary_cards.html` at the aggregate level but is **not drillable** — admin cannot click into "Related Products" and see individual context performance.

---

## 5. Recommendation List Improvements

### Current State of `recommendations.html` + `/matches/rows`

The list page currently shows:

| Column | Source |
|---|---|
| Content Title (#ID) | `Content.title` |
| Content Views | `Content.view_count` |
| Linked Items Count | COUNT from `content_items` |
| Linked Items List | Item IDs from `content_items` |
| Actions | Inspect / (unlink in modal) |

**Missing columns that exist in the data**:

| Proposed Column | Data Source | Admin Value |
|---|---|---|
| Impression Count | COUNT RecommendationImpression WHERE context_id matches | Know which content actually serves recommendations |
| Recommendation CTR | Clicks / Impressions | Primary performance signal at list level |
| Referrer-Sourced Clicks | COUNT ItemClick WHERE referrer matches | Proxy for recommendation-driven commerce activity |
| Last Impression At | MAX(created_at) on RecommendationImpression | Detect stale or abandoned content |
| Coverage Flag | content_items count vs. total items available | Is this content under-matched? |

### Sortable Columns Opportunity

The list currently sorts by `func.max(Content.view_count).desc()` only. Adding sort-by-CTR and sort-by-impressions would allow admins to prioritize work on:
- High-impression, low-CTR content (optimization opportunity)
- High-CTR, low-impression content (scaling opportunity)

### Filter Opportunities

The current search is title/name text search only. Missing filters:
- Filter by `entity_type` (which recommendation slot type)
- Filter by CTR range (e.g., "CTR below 1%")
- Filter by impression volume range
- Filter by "no impressions recorded" (zero-reach content)
- Filter by last impression date (stale content)

---

## 6. Recommendation Inspect Improvements

### Current State of `inspect_match`

The modal already shows:
- Content metadata (id, title, type, views)
- Per-item context_clicks (referrer-matched) with CTR % string
- Overall item click_count
- Unlink action per item

**Gaps in the inspect modal**:

| Missing Element | Data Source | Admin Value |
|---|---|---|
| True impression count for this context | RecommendationImpression WHERE context_id matches | True denominator |
| True recommendation CTR | Clicks / Impressions (not Views) | Accurate CTR |
| Last impression timestamp | MAX(created_at) | Is this content still serving recs? |
| Recommendation reach (unique users) | COUNT DISTINCT user_id on impressions | Audience sizing |
| Top performing item in this context | MAX CTR among linked items | Quick win signal |
| Item position analysis | entity_ids JSON position vs. click entity_id | Slot bias visibility |
| Entity type breakdown | Which slots served impressions | rec type distribution |
| Impression trend mini-chart | Daily impression count, last 14 days | Trend visibility in modal |

### Inspect for `UserInterest` (Already Exists)

The `inspect_user_interests` endpoint at `/recommendations/user_interests/<id>/inspect` shows top-5 affinity scores. This is solid but:
- It is not linked from anywhere in the admin UI (no list of users to inspect from)
- There is no way to see which users have the strongest recommendation signals
- The `interaction_count` and `last_interaction_at` on `UserInterest` are not shown
- The `target_type` (item vs. article) breakdown is not shown

---

## 7. Recommendation Dashboards

### 7.1 Currently Existing: Insights Dashboard (`insights.html` + `_summary_cards.html`)

The Content Intelligence Insights dashboard already has a substantial "Recommendation Widget Performance" section:
- Overall CTR, Related Products CTR, Related Content CTR, Shop Products CTR
- Cross-Category Benchmarks (best/worst category with deviation)
- Quality Score Breakdown table (rec types, page types, top categories)
- Action Suggestions Engine (diagnoses per module)

**This is the most data-rich recommendation view in the system.** However, it lives under "Editorial Intelligence" — not under "Recommendations" — creating a discoverability problem for recommendation administrators.

### 7.2 Missing: Dedicated Recommendation Analytics Dashboard

The `recommendations.html` page only has three stat cards (Total Matches, Linked Contents, Linked Products). It is missing any analytics layer.

**Recommended dashboard additions** (using existing data):

#### Overview Stats Row (extend existing 3 cards → 7 cards)

| New Stat Card | Data Source |
|---|---|
| Total Impressions (all time) | COUNT RecommendationImpression |
| Total Clicks (all time) | COUNT RecommendationClick |
| Overall CTR | Clicks / Impressions |
| Impressions (Last 30d) | Windowed count |
| Active Contexts | COUNT DISTINCT context_id on impressions |

#### Analytics Section (new, below stats)

**Panel A: CTR by Recommendation Type** (bar chart or metric row)  
- 3 bars: related_content, related_product, shop_product  
- Source: GROUP BY entity_type on impressions + clicks

**Panel B: Top 10 Contexts by Impressions** (table)  
- context_id → resolved title, impression count, click count, CTR  
- Sortable by CTR ascending (identify problem contexts)

**Panel C: Top 10 Items by Recommendation CTR** (table)  
- entity_id → resolved item name, total impression appearances, clicks, CTR  
- Reveals star performers

**Panel D: Impression Volume Trend** (line chart)  
- Daily impression counts, last 30 days  
- Overlaid with click counts

**Panel E: CTR Trend** (line chart, 30 days)  
- Detects improvement or degradation over time

### 7.3 Existing Data Utilization Score

| Data Field | Currently Used | Possible Uses |
|---|---|---|
| `entity_type` | ✅ CTR breakdown in insights | ✅ Fully utilized |
| `context_id` | ⚠️ Only as filter in inspect_match | ❌ Not aggregated in any admin view |
| `entity_ids` (JSON array) | ❌ Not analyzed | ❌ Position CTR, density analysis unused |
| `entity_id` (click target) | ⚠️ Only in inspect_match via proxy | ❌ Not surfaced in list or dashboard |
| `user_id` (impression) | ❌ Not used | ❌ Auth vs. anon CTR analysis |
| `user_id` (click) | ❌ Not used | ❌ User-level recommendation engagement |
| `created_at` (impression) | ❌ Not used | ❌ Time-series, trend, stale detection |
| `created_at` (click) | ❌ Not used | ❌ Time-series, peak analysis |
| `UserInterest.interaction_count` | ❌ Not surfaced | ❌ Interest strength signal |
| `UserInterest.last_interaction_at` | ❌ Not surfaced | ❌ Interest decay detection |
| `ItemClick.country` | ❌ Not used | ❌ Geographic CTR analysis |
| `ItemClick.referrer` | ⚠️ Used in inspect only | ❌ Not aggregated or sorted at list level |

**Estimated Existing Data Utilization: ~28%**  
The system captures far more signal than it surfaces. Most impression and click metadata is dark.

---

## 8. Recommendation Health Monitoring

### 8.1 Signals for Health Alerts (Derivable from Existing Data)

| Health Signal | Detection Method | Severity |
|---|---|---|
| CTR drop below threshold | CTR < 1% for any entity_type in last 7d | ⚠️ Warning |
| Zero impressions in last 48h | MAX(created_at) on impressions > 48h ago | 🔴 Critical |
| Context impression collapse | A context_id with previously high impressions drops to zero | 🔴 Critical |
| Recommendation list depleted | content_items count < 2 for a high-view content | ⚠️ Warning |
| All-zero-click impressions | impression record exists, zero matching clicks, for 7d | ⚠️ Warning |
| User interest staleness | UserInterest.last_interaction_at > 30d | ℹ️ Info |

### 8.2 Missing: Health Status Banner on Recommendations Page

The recommendations page has no health indicators. A simple inline health panel showing:
- "Recommendation system: ✅ Active — 1,240 impressions in last 24h"  
- "⚠️ 3 content pages have impressions but 0 clicks (last 7 days)"  
- "✅ Shop product CTR is above baseline (2.1%)"  

This can be derived entirely from existing `RecommendationImpression` and `RecommendationClick` tables.

### 8.3 Missing: Entity Freshness Tracking

The `last_impression_at` derived value (MAX created_at per context_id) is not exposed anywhere. Admin cannot currently identify:
- Content that had recommendation widgets active but stopped receiving impressions (page traffic collapsed)
- Items that were recommended frequently but are no longer appearing (removed from slots)

---

## 9. Existing Data Utilization Score (Summary)

| Dimension | Score | Commentary |
|---|---|---|
| `RecommendationImpression` utilization | 25% | entity_type used; context_id, entity_ids, user_id, timestamps largely unused |
| `RecommendationClick` utilization | 30% | entity_type used; entity_id only in inspect proxy; time-series unused |
| `UserInterest` utilization | 40% | Top-5 affinity in inspect; interaction_count and last_interaction_at unused |
| `UserEntityInterest` utilization | 55% | Scores shown in inspect; not aggregated at system level |
| `ItemClick.referrer` utilization | 20% | Used in single endpoint; not aggregated or sorted in list |
| `content_items` utilization | 70% | Core list + inspect; CTR overlay missing |
| **Overall** | **~28%** | Significant untapped analytical depth |

---

## 10. Phased Implementation Roadmap

### Phase 1 — Inspection & CTR Accuracy (Foundational)
*Fix incorrect CTR calculations and enrich the inspect modal with true impression-based data.*

> [!IMPORTANT]
> The CTR shown in `inspect_match` uses `content.view_count` as the denominator, which is incorrect. This should be the highest-priority fix because it corrects misleading data currently shown to admins.

#### Backend (`recommendations.py`)

**`recommendation_stats` endpoint** — extend to include:
- `total_impressions` (COUNT RecommendationImpression)
- `total_clicks` (COUNT RecommendationClick)
- `overall_ctr` (clicks / impressions)
- `impressions_last_30d`, `clicks_last_30d`

**`inspect_match` endpoint** — augment data with:
- True impression count for the context (COUNT RecommendationImpression WHERE context_id matches content)
- True impression-based CTR per item (RecommendationClick / RecommendationImpression)
- Last impression timestamp for the context
- Unique users reached (COUNT DISTINCT user_id on impressions)
- Keep referrer-based `ItemClick` data as a secondary signal (labeled clearly as "Affiliate Click Proxy")

#### Template (`recommendations.html`)

**Stats row** — extend from 3 to 6 cards:
- Add: Total Impressions, Total Clicks, Overall CTR

**Inspect modal (`_inspect.html`)** — add new section "Recommendation Performance":
- True impression count, True CTR, Last impression date, Unique users reached

---

### Phase 2 — List Intelligence & Sortability
*Surface CTR and impression data at the list level, enabling bulk prioritization.*

#### Backend (`recommendations.py`)

**`_fetch_matches_page` / `matches_rows`** — add per-row:
- `impression_count` (subquery or join on RecommendationImpression by context_id)
- `rec_click_count` (subquery on RecommendationClick by context_id)
- `rec_ctr` (computed ratio)
- `last_impression_at` (MAX created_at)
- Sortable by: CTR (asc/desc), impressions (asc/desc), view_count (current default)

**New endpoint**: `/admin/recommendations/stats/impressions` — detailed impression stats for the analytics panel (async-loaded).

#### Template (`recommendations.html`)

**Toolbar** — add filters:
- Filter by entity_type (related_content, related_product, shop_product)
- Filter by CTR range (below 1%, 1–3%, above 3%)
- Filter by "no impressions" toggle

**Table columns** — add:
- Impressions column with badge coloring (low/medium/high)
- CTR column with badge coloring (danger/warning/success)
- Last Active column

#### JS (`recommendations.js`)

- Extend `loadStats()` to render 6 cards
- Add filter parameter passing for new filters
- Add sort control wiring

---

### Phase 3 — Context Performance Dashboard
*New analytics section on the recommendations page surfacing context-level CTR.*

#### Backend (`recommendations.py`)

**New endpoint**: `/admin/recommendations/context-performance`
- Returns top N contexts sorted by impressions (or CTR)
- Response: `[{context_id, context_title, entity_type, impressions, clicks, ctr, last_active}]`
- Resolves context_id → human-readable title by parsing `entity_type/entity_id` and joining Content

**New endpoint**: `/admin/recommendations/entity-performance`
- Top N recommended entities (items/content) by CTR
- Response: `[{entity_id, entity_type, entity_name, impression_appearances, total_clicks, ctr}]`

#### Template — New analytics section on `recommendations.html`

Add a collapsible analytics section below the filters, with:

**Panel A: Top Contexts by Impressions** (server-rendered or JS-loaded table)  
Columns: Context, Type, Impressions, Clicks, CTR, Last Active

**Panel B: Top Recommended Entities by CTR** (table)  
Columns: Entity, Type, Appearances, Clicks, CTR

**Panel C: CTR by Recommendation Type** (three metric chips with trend arrow)

---

### Phase 4 — Health Monitoring & Alerting Banner
*Proactive signal about recommendation system health.*

#### Backend (`recommendations.py`)

**New endpoint**: `/admin/recommendations/health`
- Returns: `{status, signals: [{level, message}], last_impression_at, impressions_24h, clicks_24h, ctr_24h}`
- Checks:
  - No impressions in last 48h → CRITICAL
  - CTR < 0.5% for any entity_type in last 7d → WARNING
  - Content with impressions but 0 clicks for 7d → WARNING

#### Template (`recommendations.html`)

**Health Banner** — above stats row:
- Color-coded: green (healthy) / amber (warning) / red (critical)
- Shows: last activity timestamp, 24h impression count, active context count
- Expandable: lists individual signals with descriptions

---

### Phase 5 — Time-Series Analytics & User Segmentation
*Long-term performance visibility and audience understanding.*

#### Backend (`recommendations.py`)

**New endpoint**: `/admin/recommendations/trend`
- Returns daily impression + click counts for last 30/90 days
- Segmentable by entity_type

**New endpoint**: `/admin/recommendations/user-segments`
- Authenticated vs. anonymous CTR comparison
- Users with UserInterest records vs. without (tests personalization effectiveness)

#### Template

**Trend Chart** (line chart, Chart.js — already used in `interactions.html`)  
- Overlaid impressions + clicks daily
- Toggle by entity_type

**User Segmentation Panel**  
- Metric cards: Auth CTR vs. Anon CTR
- If Auth CTR > Anon CTR: recommendation personalization is effective
- If equal or lower: personalization signals not being leveraged

---

### Phase 6 — Entity Slot Position Analysis
*Advanced: leverage ordered JSON `entity_ids` array for positional CTR intelligence.*

#### Backend (`recommendations.py`)

**New endpoint**: `/admin/recommendations/slot-analysis`
- For each impression, decode `entity_ids` JSON to get ordered list
- Match against `RecommendationClick.entity_id` to determine click position
- Aggregate: click rate by position (position 1 vs. position 2 vs. position 3+)

#### Template

**Slot Position Chart** (bar chart)  
- X axis: slot position (1, 2, 3, 4+)
- Y axis: click rate (%)
- Reveals positional bias — if position 1 dominates, slots 2+ may need attention

**Recommendation**: If position bias is extreme (>80% of clicks on slot 1), recommend reducing the recommendation set size to only show high-confidence matches.

---

## Summary: File Change Map

### Files to Modify

#### [MODIFY] [recommendations.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/admin/recommendations.py)
- Extend `recommendation_stats` with impression/click totals
- Fix `inspect_match` CTR to use true impression count
- Add impression/CTR columns to `_fetch_matches_page`
- Add new endpoints: `context-performance`, `entity-performance`, `health`, `trend`, `slot-analysis`

#### [MODIFY] [recommendations.html](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/templates/admin/content_intelligence/recommendations.html)
- Extend stats block from 3 to 6 cards
- Add toolbar filters (entity_type, CTR range)
- Add analytics section (context table, entity table, health banner)
- Add trend chart container

#### [MODIFY] [recommendations.js](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/static/js/admin/pages/recommendations.js)
- Extend `loadStats()` for 6 cards
- Add `loadContextPerformance()`, `loadEntityPerformance()`, `loadHealth()`, `loadTrend()`
- Wire new filter controls

#### [MODIFY] [_inspect.html](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/templates/admin/components/_inspect.html)
- Add conditional recommendation performance section when `rec_impressions` context variable is present
- Show true impression count, CTR, last active, unique users

#### [MODIFY] [_rows.html](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/templates/admin/components/_rows.html)
- Add CTR badge rendering for `domain_type == 'rec'`
- Add impression count cell rendering

### Files to Create

#### [NEW] `app/web/templates/admin/content_intelligence/_recommendation_analytics.html`
- Standalone analytics section partial (context table, entity table, health panel)
- Included by `recommendations.html`

#### [NEW] `app/web/templates/admin/content_intelligence/_recommendation_health.html`
- Health banner partial
- Color-coded system status with expandable signal list

---

## Open Questions

> [!IMPORTANT]
> **CTR Denominator Strategy**: Should the corrected inspect CTR use `RecommendationImpression` count exclusively, or a hybrid of impressions + view_count? The current referrer-based approach via `ItemClick` measures affiliate clicks (commerce intent), while impression-based CTR measures widget engagement. Both are valid but measure different things. Recommend exposing both with clear labels.

> [!IMPORTANT]
> **Context ID Format Consistency**: The `context_id` field is a free-text string (e.g., `article/123`). Is this format consistent across all client-side impression tracking calls? If not, joining context_id back to Content rows will have gaps. Requires audit of the front-end tracking code before building context-performance queries.

> [!NOTE]
> **`UserInterest` Admin Entry Point**: The `inspect_user_interests` endpoint exists but has no corresponding list page or navigation link. Should a "User Affinity" sub-tab be added to the Users admin page, or a dedicated section within the Recommendations page?

> [!NOTE]
> **Chart Library**: The `interactions.html` page already uses Chart.js via CDN. Should Chart.js be added to the recommendations page for trend and slot charts, or use a different visualization approach (pure CSS bars, SVG sparklines)?
