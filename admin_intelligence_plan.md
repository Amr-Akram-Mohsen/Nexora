# Nexora Admin Intelligence Implementation Plan

> **Role**: Senior Data Strategist · Content-Intelligence Architect · Analytics Architect · Information Architect · Admin Dashboard UX Specialist
>
> **Scope**: Cross-domain intelligence derived exclusively from existing structured data. No ML, no embeddings, no external BI platforms.

---

## 1. Architecture Findings

### 1.1 Domain Inventory

| Domain | Primary Tables | Key Metrics Already Stored | Admin Visibility Today |
|--------|---------------|---------------------------|----------------------|
| **Content** | `contents`, `articles`, `videos`, `posts` | `view_count`, `like_count`, `dislike_count`, `save_count`, `comment_count`, `share_count`, `score`, `review_score`, `is_active`, `is_published`, `published_at`, `ingested_at`, `intent_id`, `gender_id`, `price_tier_id` | Partial — top-5 by views only |
| **Items** | `items`, `item_variants`, `item_store_links`, `item_images`, `item_specifications`, `stores` | `view_count`, `click_count`, `like_count`, `save_count`, `comment_count`, `rating`, `review_count`, `price`, `old_price`, `availability`, `commission_rate`, `last_checked_at`, `is_active` | Partial — top-5 by clicks only |
| **Interactions** | `views`, `reactions`, `comments`, `saves`, `shares`, `item_clicks` | Per-event timestamps, `user_id`, `ip_address`, `target_type`/`target_id`, `channel` (shares), `country` (clicks) | Aggregate totals only |
| **Taxonomy** | `categories`, `brands`, `topics`, `intent_facets`, `gender_facets`, `price_tier_facets`, `attributes`, `sections` | Structural hierarchy, `authority_score` (Source), `industry` (Brand), `is_featured`, `sort_order` | Coverage matrix only |
| **Sources** | `sources`, `article_sources` | `authority_score`, `is_active`, `domain`, content/item counts per source | Provider activity list |
| **Distribution** | `distribution_posts`, `distribution_platforms` | `status`, `publish_date`, `views_count`, `likes_count`, `clicks_count`, `shares_count`, per post | Social table (flat list) |
| **Recommendations** | `recommendation_impressions`, `recommendation_clicks`, `user_interests`, `user_entity_interests` | Impressions/clicks by `entity_type`, `context_id`, `entity_id`, user interest scores | CTR cards + benchmarks |

### 1.2 Relationship Map

```
Content ←→ Category (1:N)
Content ←→ Brand (N:M via content_brands)
Content ←→ Topic (N:M via content_topics)
Content ←→ Item (N:M via content_items)   ← rich but underused in admin
Content ←→ Source (N:1)
Content ←→ IntentFacet, GenderFacet, PriceTierFacet (N:1)
Content ←→ DistributionPost (1:N via source_target)
Content ←→ RecommendationImpression / Click (1:N via context_id)

Item ←→ Category (N:1)
Item ←→ Brand (N:1)
Item ←→ Source (N:1)
Item ←→ ItemVariant → ItemStoreLink → Store
Item ←→ ItemClick (via ItemStoreLink)
Item ←→ DistributionPost (1:N via source_target)
Item ←→ RecommendationImpression / Click (as entity_id targets)

User ←→ UserInterest → UserEntityInterest (brand_id, category_id, topic_id scores)
```

### 1.3 Critical Architecture Observations

1. **The `content_items` join table** links reviewed/mentioned items back to content. This cross-domain relationship is **completely invisible in admin** today. It is the single richest untapped relationship in the system — it enables content-to-commerce attribution.

2. **Distribution metrics** (`views_count`, `likes_count`, `clicks_count`, `shares_count` on `DistributionPost`) are stored but used only as a comment inside `performance_feedback.py` labelled `# [FUTURE FEEDBACK LOOP]`. These are real data, not simulated, and they are being discarded from admin visibility.

3. **`ItemClick.country`** field exists but is never surfaced in any admin view. Geographic demand data is being silently dropped.

4. **`Share.channel`** exists on shares but is never aggregated into admin views. Channel-level virality data is lost.

5. **`Source.authority_score`** is stored and indexed but never appears in any admin intelligence calculation or display.

6. **`UserEntityInterest.score`** (per brand/category/topic) represents actual user affinity data from the recommendation system. It is never surfaced in any admin context — not as a demand signal, not as a content opportunity signal.

7. **`Content.score`** and **`Content.review_score`** are indexed fields marked "future-proofing" but are currently unused in all analytics modules.

8. **`ItemStoreLink.commission_rate`** and `ItemStoreLink.last_checked_at` are never used in admin intelligence. Revenue potential and data freshness signals are invisible.

9. **`performance_feedback.py` simulates CTR** for content with no real `RecommendationImpression` data (`actual_ctr = 3.0 + (c_id % 20)` fallback). This simulation is mixed with real data without a clear separation in the admin UI. The `is_simulated` flag exists in the payload but is not rendered in the template.

10. **The `insights.py` cache** is in-process dictionary with no cross-worker synchronization. On multi-worker deployments, each worker builds its own cache independently.

---

## 2. Intelligence Findings

### 2.1 What the System Already Computes (Current State)

| Intelligence Area | What Exists | Quality |
|-------------------|-------------|---------|
| Content opportunity scoring | Demand × gap score per category and brand | Good |
| Coverage matrix | Category-level demand vs. content count | Good |
| Intent distribution | Per-category intent-type breakdown | Good |
| Brand opportunities | Engagement vs. article volume gap | Good |
| Recommendation CTR | By type (related_content, related_product, shop_product) | Good |
| Rec. quality scores | Normalized CTR × engagement weight per type/category/page | Good |
| Performance feedback | Per-content evaluation (overperforming / underperforming / aligned) | Mixed (simulation fallback is opaque) |
| Trend signals | 7-day vs. prior-7-day % change per category/brand/topic | Good but not surfaced in dashboard |
| Asset gap analysis | Missing YouTube/Blog/Pinterest content per entity | Good |

### 2.2 What the Data Supports But Does Not Compute Today

#### Content Intelligence Gaps
- **Content freshness score**: `published_at` + `view_count` + `created_at` are all stored. A freshness/decay index is technically available (`get_content_decay()` exists in `content_opportunities.py`) but is never called in any admin view.
- **Content completeness score**: Intent facet, gender facet, price tier, topics, brands, linked items — all nullable. Completeness % per content piece is derivable with a single query but never shown.
- **Underperforming content heat map**: The `performance_feedback` module classifies underperforming content individually but never aggregates this into a category-level or section-level health view.
- **Content-to-item linkage rate**: `content_items` table exists. % of articles that have linked items (enabling commerce attribution) is calculable but invisible.
- **Review queue age**: `is_published = False` content with oldest `ingested_at` is never shown in priority order.

#### Catalog Intelligence Gaps
- **Item completeness score**: `description`, `rating`, `review_count`, `images`, `specifications`, `variants`, `store_links` — all fields that could produce a completeness % per item. Never calculated.
- **Affiliate coverage**: % of items with at least one active `ItemStoreLink` (`is_active = True`, `availability = 'InStock'`) is derivable but invisible.
- **Pricing staleness**: `ItemStoreLink.last_checked_at` enables identifying items with outdated pricing. Not surfaced.
- **Items without content**: Items with no entries in `content_items` — products with no editorial coverage — are never identified for the admin.
- **Commission coverage**: `commission_rate` is stored per store link but never aggregated into insights about which categories or brands have better affiliate economics.

#### Source Intelligence Gaps
- **Source engagement rate**: `authority_score` on `Source` is stored but never cross-referenced with actual engagement data (views, clicks) generated by that source's content/items.
- **Source freshness**: `Content.ingested_at` grouped by `source_id` could reveal silent/stale providers that have stopped feeding new content.
- **Source content-to-item ratio**: Some sources may produce only content or only items. This balance is never analyzed.

#### Distribution Intelligence Gaps
- **Platform effectiveness by content type**: Which platform (YouTube, Pinterest, etc.) generates better engagement ratios when distributing articles vs. items? Data is in `DistributionPost` combined with content `object_type`. Never computed.
- **Distribution coverage**: What % of published content/items have at least one distribution post? Never surfaced.
- **Publishing efficiency**: Average days from `Content.published_at` to first `DistributionPost.publish_date`. Not calculated.
- **Cross-platform content lifecycle**: An asset's full journey (ingested → published → distributed → engaged) is traceable but never shown as a lifecycle view.

#### Engagement Intelligence Gaps
- **Geographic demand**: `ItemClick.country` is captured but never shown. High-demand geographies are invisible.
- **Share channel breakdown**: `Share.channel` is stored but never aggregated. Organic vs. paid virality signals are lost.
- **Comment sentiment distribution**: `Comment.sentiment` + `Comment.confidence` are stored on comments. Aggregate sentiment per content/category/brand is never surfaced.
- **Engagement composition**: The ratio of views → saves → comments → shares per content piece (funnel shape) is derivable but not shown.
- **Cross-entity engagement comparison**: Content engagement vs. item engagement by category is partially computed in `get_content_vs_product_performance()` but never shown in any admin dashboard.

#### Recommendation Intelligence Gaps
- **CTR trends over time**: All recommendation data is aggregated all-time. No time-series trend of recommendation performance exists.
- **User interest concentration**: `UserEntityInterest` records aggregate user affinity scores per brand/category/topic. This demand signal is never used in the admin dashboard despite being the most direct measure of user intent.
- **Recommendation-to-content match rate**: Which recommendation impressions resulted in clicks that led to further engagement? The data is in `RecommendationClick.context_id` → `Content` → reactions/saves — but the chain is never computed.

#### Taxonomy Intelligence Gaps
- **Topic concentration**: Some topics may cover too many content pieces (oversaturated) while others are barren. This distribution is never shown.
- **Taxonomy health**: Are categories balanced in terms of both content and product count? The `is_leaf` flag on categories enables identifying leaf-node saturation. Never surfaced.
- **Attribute coverage**: `content_attributes` links content to `AttributeFacet`. Coverage per category (which attributes are documented) is never analyzed.

---

## 3. Analytics Recommendations

### 3.1 Content Analytics

**Derive content health score** from existing columns:

```
health_score = (
  0.30 × (view_count / max_views)            -- reach
  + 0.25 × (save_count / max_saves)          -- retention intent
  + 0.20 × (like_count / max_likes)          -- positive signal
  + 0.15 × (comment_count / max_comments)    -- engagement depth
  + 0.10 × freshness_factor                  -- days since published
)
```

All inputs already exist on the `Content` model. No new data collection needed.

**Freshness factor**: Re-use `get_content_decay()` which already queries `View` counts across 30-day windows. Surface it per-content in the performance feedback table.

**Completeness audit**: A single query checking `intent_id IS NOT NULL`, `gender_id IS NOT NULL`, topic count > 0, brand count > 0, linked_items count > 0 per content piece gives a completeness %.

### 3.2 Catalog Analytics

**Item completeness score**:
```
completeness = (
  has description +
  has rating +
  has review_count > 0 +
  has at least 1 image +
  has at least 1 specification +
  has at least 1 active store link
) / 6
```

All inputs are on existing models.

**Affiliate health**: `ItemStoreLink.is_active`, `availability`, `last_checked_at` — group by `Item.category_id` and `Item.brand_id` to produce affiliate coverage rates per category/brand.

### 3.3 Engagement Analytics

**Engagement funnel per content piece**: Already stored as denormalized counters on `Content`. The funnel `views → saves → comments → likes` can be expressed as step-through ratios without new queries.

**Share channel analysis**: Simple `GROUP BY Share.channel` grouped with `Share.target_type` gives channel-level virality. Zero development cost, data already captured.

**Comment sentiment rollup**: `Comment.sentiment` grouped by `target_type` + category (via join to Content.category_id or Item.category_id) gives a category-level sentiment health score.

### 3.4 Source Analytics

**Source engagement efficiency** = total engagement generated ÷ total content published per source. Joinable from `Content.source_id` → `Content.view_count + like_count + save_count`.

**Source staleness detection**: `MAX(Content.ingested_at) GROUP BY source_id` compared to current date. Sources silent for > N days are detectable with one query.

### 3.5 Distribution Analytics

**Distribution coverage rate**: `COUNT(DISTINCT source_target_id) / total published content` gives the % of assets that have been distributed. Filter by `source_target_type`.

**Platform performance index** = `(views_count + likes_count + clicks_count) / COUNT(posts)` per platform. Derivable from existing `DistributionPost` columns.

**Time-to-distribution**: `DistributionPost.publish_date - Content.published_at` gives the publishing lag. Average per platform reveals operational efficiency.

---

## 4. Dashboard Recommendations

### 4.1 Executive Dashboard (`/admin/executive`)

**Purpose**: Single-glance operational health for decision makers. No filtering needed.

**Panels**:
1. **System Health Score** — Composite KPI: content health, catalog completeness, recommendation CTR, distribution coverage. One number, color-coded.
2. **Engagement Velocity** — Week-over-week interaction count change (already computed in `trends.py`, not displayed centrally).
3. **Revenue Readiness** — % of items with active affiliate links + average commission rate per category.
4. **Top 3 Opportunities** — Pull top 3 from existing `get_decision_intelligence_data()` output. Already computed, just needs a dedicated executive display.
5. **Alert Summary** — Count of health alerts by severity. Links to operational dashboard.

### 4.2 Operational Dashboard (Current `/admin/dashboard`) — Enhancements

**Current state**: Aggregate counts, top-5 lists, growth trend chart, provider activity.

**Recommended additions**:
1. **Review Queue Aging Widget** — `is_published = False` items sorted by `ingested_at`. The oldest unreviewed content is invisible today.
2. **Stale Source Alert Panel** — Sources with no ingested content in >7 days. One query.
3. **Content-to-Item Linkage Rate** — `content_items` JOIN count. Tells admin how much editorial content is commerce-enabled.
4. **Active/Inactive item ratio** — Mirrors the existing content active/inactive split but for items. Not currently shown.

### 4.3 Content Intelligence Dashboard (Current `/admin/insights`) — Restructured

**Current structure**: 6 widgets loaded sequentially, all focused on opportunity generation.

**Recommended structure — add 3 new sections**:

**Section A: Content Health** (new)
- Content health score distribution (histogram by score bucket)
- Freshness/decay leaderboard (most decayed content — already computed, not displayed)
- Completeness audit table (% complete per content, filterable by category)

**Section B: Content-to-Commerce Bridge** (new, uses `content_items`)
- % of articles with linked items per category
- Items most frequently reviewed (ranked by `content_items` count)
- Content pieces with no commerce link

**Section C: Intent Coverage Analysis** (existing widget, enhanced)
- Currently shows missing intents per category
- Add: intent × performance heatmap (which intent types generate higher CTR from `RecommendationClick`)

### 4.4 Catalog Health Dashboard (`/admin/catalog`) — New

**Purpose**: Item-level operational intelligence.

**Panels**:
1. **Catalog Completeness Score** — System-wide average item completeness %
2. **Completeness Breakdown by Category** — Bar chart, sortable
3. **Items Missing Affiliate Links** — Table: item name, category, brand, age
4. **Pricing Staleness Map** — Items grouped by `last_checked_at` age bucket
5. **Affiliate Coverage by Store** — Which stores are covering which categories
6. **Items Without Editorial Coverage** — Items with no `content_items` link

### 4.5 Source Intelligence Dashboard (`/admin/sources`) — New

**Purpose**: Publisher and data-provider health.

**Panels**:
1. **Source Contribution Leaderboard** — Content count + item count per source, with authority score
2. **Source Engagement Efficiency** — Engagement generated ÷ content published per source
3. **Source Freshness Monitor** — Last ingestion date per source, color-coded by staleness
4. **Authority vs. Engagement Scatter** — `authority_score` (X) vs. avg engagement (Y) per source. Reveals over-trusted or under-leveraged sources.

### 4.6 Distribution Intelligence Dashboard (`/admin/distribution`) — Enhanced

**Current state**: Flat table of posts with views/likes/clicks.

**Recommended additions**:
1. **Distribution Coverage Rate** — % of published content distributed
2. **Platform Performance Index** — Engagement per post per platform
3. **Time-to-Distribution Histogram** — Days from publish to first distribution post
4. **Top-Performing Distribution Posts** — By engagement rate, linkable to source content

---

## 5. KPI Recommendations

### 5.1 Content Intelligence KPIs

| KPI | Why It Matters | Calculation | Dashboard |
|-----|---------------|-------------|-----------|
| **Content Health Score** | Single operational health signal | Weighted composite of reach, retention, engagement, freshness | Executive, Content Intel |
| **Content Completeness Rate** | Ensures taxonomy integrity | `AVG(completeness_pct)` across all content | Operational, Content Intel |
| **Content Decay Rate** | Identifies traffic erosion | `(views_30d_prior - views_30d) / views_30d_prior × 100` | Content Intel |
| **Review Queue Age (P95)** | Ops bottleneck signal | 95th percentile `NOW - ingested_at` for `is_published=False` | Operational |
| **Content-to-Item Linkage Rate** | Commerce-enablement KPI | `COUNT(content_items rows) / COUNT(published content)` | Operational, Catalog |

### 5.2 Catalog Intelligence KPIs

| KPI | Why It Matters | Calculation | Dashboard |
|-----|---------------|-------------|-----------|
| **Catalog Completeness Score** | Data quality baseline | Avg item completeness across all items | Executive, Catalog |
| **Affiliate Coverage Rate** | Revenue readiness | `COUNT(items with active store link) / COUNT(items)` | Executive, Catalog |
| **Pricing Freshness Score** | Data currency | `AVG(NOW - last_checked_at)` for active store links | Catalog |
| **Items Without Coverage** | Editorial gap | `COUNT(items NOT IN content_items)` | Catalog |
| **Avg Commission Rate by Category** | Revenue intelligence | `AVG(commission_rate) GROUP BY category` | Catalog |

### 5.3 Engagement Intelligence KPIs

| KPI | Why It Matters | Calculation | Dashboard |
|-----|---------------|-------------|-----------|
| **Save Rate** | Intent-to-return signal | `SUM(save_count) / SUM(view_count)` | Operational |
| **Engagement Depth Score** | Quality of engagement | `(saves + comments + reactions) / views` | Content Intel |
| **Comment Sentiment Score** | Audience health | `AVG(confidence) WHERE sentiment='positive'` / total | Content Intel |
| **Share Channel Distribution** | Virality source | `COUNT GROUP BY channel` on `shares` | Distribution |

### 5.4 Source Intelligence KPIs

| KPI | Why It Matters | Calculation | Dashboard |
|-----|---------------|-------------|-----------|
| **Source Engagement Efficiency** | Value per provider | `SUM(views+saves+likes) / COUNT(content)` per source | Sources |
| **Source Freshness Score** | Feed health | `NOW - MAX(ingested_at)` per source | Sources, Alerts |
| **Authority-to-Engagement Ratio** | Validates authority scores | `SUM(engagement) / authority_score` per source | Sources |

### 5.5 Distribution Intelligence KPIs

| KPI | Why It Matters | Calculation | Dashboard |
|-----|---------------|-------------|-----------|
| **Distribution Coverage Rate** | Publishing reach | `COUNT(distinct distributed assets) / COUNT(published assets)` | Distribution |
| **Platform Engagement Index** | Platform ROI | `SUM(views+likes+clicks) / COUNT(posts)` per platform | Distribution |
| **Time-to-Distribution (Avg)** | Publishing efficiency | `AVG(publish_date - published_at)` on matched content | Distribution |
| **Distribution-to-Engagement Ratio** | Content amplification ROI | `SUM(dist.clicks) / SUM(content.view_count)` | Distribution |

### 5.6 Recommendation Intelligence KPIs

| KPI | Why It Matters | Calculation | Dashboard |
|-----|---------------|-------------|-----------|
| **Overall Recommendation CTR** | System effectiveness | Already computed | Content Intel |
| **Best/Worst Category CTR Deviation** | Targeting quality | Already computed | Content Intel |
| **Recommendation Coverage Rate** | % of content with impressions | `COUNT(DISTINCT context_id in impressions) / COUNT(content)` | Content Intel |
| **User Interest Concentration (HHI)** | Demand diversity | Herfindahl index on `UserEntityInterest.score` per category | New dashboard |

### 5.7 Taxonomy Intelligence KPIs

| KPI | Why It Matters | Calculation | Dashboard |
|-----|---------------|-------------|-----------|
| **Topic Concentration Score** | Prevents over-coverage | `STDEV(content_count per topic)` | Taxonomy |
| **Taxonomy Coverage Depth** | Leaf-node saturation | `COUNT(categories WHERE is_leaf=True AND content_count > 0)` | Taxonomy |
| **Attribute Coverage Rate** | Metadata richness | `COUNT(content_attributes) / COUNT(content)` | Catalog |

---

## 6. Visualization Recommendations

### 6.1 KPI Cards (Immediate — Phase 1)

- **System Health Score**: Large number card with color band (green/amber/red) and sub-breakdown on hover.
- **Affiliate Coverage %**: Radial progress ring. Color-coded.
- **Distribution Coverage %**: Radial progress ring.
- **Review Queue Count + Age**: Combined card — count badge + oldest item age.

### 6.2 Trend Charts (Phase 2)

- **Recommendation CTR over time**: Line chart, split by type (related_content, related_product, shop_product). Currently data is all-time aggregate only. Needs time-bucketed query added.
- **Content engagement trend**: 7-day rolling stacked area — views, saves, comments per day. `View.created_at` already supports this.
- **Source contribution trend**: Stacked bar — new content per source per week.

### 6.3 Health Dashboards (Phase 2-3)

- **Catalog Completeness Heatmap**: Category (row) × completeness dimension (col) — e.g., has description, has image, has store link. Color by coverage %.
- **Content Completeness Matrix**: Similar — content type (row) × taxonomy dimension (col).
- **Source Staleness Timeline**: Horizontal timeline per source, last-activity dot colored by recency.

### 6.4 Intelligence Dashboards (Phase 3)

- **Content-to-Commerce Attribution Funnel**: For items linked via `content_items`, show: readers → content views → item views → affiliate clicks. 4-stage funnel using existing data.
- **Demand-Coverage Quadrant Chart**: Scatter plot — demand score (X) vs. content count (Y) per category. Quadrants: over-covered, under-covered, well-balanced, low-demand.
- **Intent × CTR Heatmap**: Categories (rows) × intent types (cols) × recommendation CTR (cell color). All data exists in `RecommendationClick` → `Content.intent_id`.

### 6.5 Executive Summary (Phase 4)

- **Weekly Performance Digest**: Auto-generated from existing data. Top 3 movers (categories by engagement change from `trends.py`), top risk (highest decay content), top opportunity (highest scoring opportunity), distribution health.
- **Cross-Domain KPI Scorecard**: One row per domain, composite score, week-over-week delta.

---

## 7. Alert & Monitoring Recommendations

### 7.1 Health Alerts (Data Quality)

| Alert | Trigger | Data Source |
|-------|---------|-------------|
| **Stale Provider** | Source with no new content in >7 days | `MAX(Content.ingested_at) GROUP BY source_id` |
| **Pricing Data Stale** | Item store links with `last_checked_at` > 30 days | `ItemStoreLink.last_checked_at` |
| **Unpublished Backlog** | `is_published=False` content older than 3 days | `Content.is_published`, `ingested_at` |
| **Dead Affiliate Links** | `ItemStoreLink.is_active=False` but item still active | Join `Item.is_active` + `ItemStoreLink.is_active` |

### 7.2 Coverage Alerts

| Alert | Trigger | Data Source |
|-------|---------|-------------|
| **High-Demand, Zero-Content Category** | Category with top-quartile demand score but 0 content in last 30 days | `get_content_coverage_matrix()` |
| **Brand with No Editorial** | Brand with engagement > average but `article_volume = 0` | `get_brand_opportunity_data()` |
| **Item without Affiliate** | Item older than 7 days with no `ItemStoreLink` | Join Item + ItemStoreLink |
| **Content without Commerce** | Published article with 0 entries in `content_items` | `content_items` LEFT JOIN |

### 7.3 Quality Alerts

| Alert | Trigger | Data Source |
|-------|---------|-------------|
| **High-Severity Underperformer** | Content classified as `underperforming` with `severity=high` | `failures_detected` in `performance_feedback` |
| **Recommendation CTR Drop** | Any recommendation type CTR drops below 2% | `get_recommendation_performance_data()` |
| **Comment Sentiment Negative Spike** | Category-level negative sentiment > 40% | `Comment.sentiment GROUP BY category` |

### 7.4 Operational Alerts

| Alert | Trigger | Data Source |
|-------|---------|-------------|
| **Distribution Backlog** | Published content with no distribution post after 24h | `DistributionPost` vs `Content.published_at` |
| **Strategy Accuracy Degradation** | `average_accuracy` in `evaluate_content_performance_feedback` drops below 60% | Performance feedback module |

---

## 8. Existing Data Utilization Score

### Per-Domain Assessment

| Domain | Stored Fields | Fields Actively Used in Admin | Utilization | Hidden Value |
|--------|--------------|------------------------------|-------------|-------------|
| **Content** | 20+ columns | 6 (view_count, title, type, active, published, ingested_at) | **30%** | `score`, `review_score`, completeness fields, `ingestion_origin`, intent/gender/price_tier |
| **Items** | 15+ columns | 4 (name, click_count, rating, item_type) | **27%** | `commission_rate`, `last_checked_at`, `availability`, variant pricing gap |
| **Interactions** | 6 tables | Aggregates only — no per-table breakdown visible | **40%** | `Share.channel`, `ItemClick.country`, `Comment.sentiment`, `View.created_at` time-series |
| **Taxonomy** | 8 tables | Category coverage matrix, brand opportunities | **45%** | `authority_score` (Source), `is_featured`/`sort_order` patterns, attribute coverage |
| **Sources** | 3 fields used | name, slug, count per source | **20%** | `authority_score` vs. engagement correlation, freshness signals |
| **Distribution** | 7 metrics per post | Views, likes, clicks in flat list | **35%** | Time-to-distribution, coverage rate, platform efficiency, lifecycle view |
| **Recommendations** | Impression + Click tables | CTR by type, quality scores | **60%** | Time-series trends, `UserEntityInterest` demand signals, recommendation coverage rate |

### Key Underutilized Relationships

1. **`content_items`** — The richest untapped join. Commerce attribution from editorial content. **0% utilized in admin.**
2. **`UserEntityInterest.score`** — Direct user affinity signal per brand/category/topic. **0% utilized in admin.**
3. **`Comment.sentiment` + `Comment.confidence`** — Pre-computed sentiment data. **0% utilized.**
4. **`ItemClick.country`** — Geographic demand signal. **0% utilized.**
5. **`Share.channel`** — Virality channel. **0% utilized.**

---

## 9. Phased Implementation Roadmap

### Phase 1 — Quick-Win Intelligence (Effort: Low / Value: High)

**Goal**: Surface data that already exists in existing queries but is not rendered in admin.

#### 1.1 Expose `is_simulated` Flag in Performance Feedback Table

- **File**: `_performance_feedback_inner.html`
- **Change**: Render a small badge on simulated rows so admins know which CTR values are estimated vs. real.
- **Why now**: Zero new queries. One template change. Eliminates misleading data presentation.

#### 1.2 Add Review Queue Age Widget to Dashboard

- **File**: `stats.py` → `get_dashboard_stats_data()`
- **Change**: Add one query — `is_published=False` ordered by `ingested_at ASC`, returning oldest 5. Template: `_review_queue_aging.html`.
- **Why now**: Data exists. One query. High operational value.

#### 1.3 Add Stale Source Detection to Provider Activity

- **File**: `stats.py`
- **Change**: Extend `provider_activities` to include a `days_since_last_ingestion` field. Add color-coding in the existing `_provider_activities.html` template.
- **Why now**: `MAX(ingested_at)` already computed. One field addition.

#### 1.4 Surface Recommendation Coverage Rate

- **File**: `recommendation_performance.py`
- **Change**: Add one metric to the returned payload: `recommendation_coverage_rate = DISTINCT context_ids in impressions / total published content count`.
- **Why now**: Data is in existing tables. One additional `COUNT(DISTINCT)` query. High administrative value.

#### 1.5 Show Share Channel Breakdown

- **File**: `stats.py` (interactions section)
- **Change**: Add `GROUP BY Share.channel` query. Surface in interactions breakdown widget as a sub-table.
- **Why now**: Data is in `Share.channel`. Zero new schema changes.

#### 1.6 Surface Content Decay Leaders in Performance Feedback

- **File**: `insights.py` → `widget_performance_feedback`
- **Change**: Call `get_content_decay(content_id)` for each underperforming content and include in the rendered output. Sort by decay rate descending.
- **Why now**: `get_content_decay()` already exists in `content_opportunities.py`. Zero new code — just wire up.

---

### Phase 2 — Operational Intelligence (Effort: Medium / Value: High)

**Goal**: Create new queryable intelligence from existing data relationships.

#### 2.1 Content Completeness Audit

- **New function**: `get_content_completeness_report()`
- **Query logic**: For each content, check non-null of `intent_id`, `gender_id`, `price_tier_id`, `source_id`, and COUNT of topics, brands, linked_items. Produce a completeness % per piece and aggregate by category.
- **New route**: `/admin/insights/widget/content-completeness`
- **New template**: `_content_completeness.html`

#### 2.2 Item Catalog Health Dashboard

- **New function**: `get_catalog_health_report()`
- **Query logic**:
  - Items with 0 images → `LEFT JOIN item_images`
  - Items with 0 active store links → `LEFT JOIN item_store_links WHERE is_active=True`
  - Items with stale pricing → `last_checked_at < NOW - 30 days`
  - Items with no `content_items` entry → editorial coverage rate
- **New route**: `/admin/catalog/health`
- **New template**: Full dashboard

#### 2.3 Source Intelligence Dashboard

- **New function**: `get_source_intelligence_data()`
- **Query logic**: Join `Source` → `Content` (view_count + like_count + save_count sum) + `Item` (click_count sum). Compute engagement per content/item published. Add `days_since_last_ingestion`.
- **New route**: `/admin/sources/intelligence`

#### 2.4 Content-to-Commerce Attribution

- **New function**: `get_content_commerce_attribution()`
- **Query logic**: `content_items` JOIN → for each linked pair: content views (from Content.view_count) + item clicks (from Item.click_count) + item saves. Produce a conversion funnel per content piece.
- **New route**: `/admin/insights/widget/commerce-attribution`
- **Visualization**: 4-stage funnel card

#### 2.5 Distribution Intelligence Enhancements

- **New function**: `get_distribution_intelligence_data()`
- **Query logic**:
  - Coverage rate: `DISTINCT source_target_id` with posts / published content
  - Platform engagement index: `SUM(views+likes+clicks) / COUNT(posts) GROUP BY platform`
  - Time-to-distribution: `AVG(publish_date - content.published_at)` via JOIN
- **New route**: `/admin/distribution/intelligence`

#### 2.6 Demand-Coverage Quadrant

- **New function**: Extend `get_content_coverage_matrix()` to return raw `demand_score` and `content_count` as numeric values (not just label strings).
- **New visualization**: Scatter chart in coverage matrix widget showing quadrant positioning (High Demand / Low Coverage = top priority).

---

### Phase 3 — Cross-Domain Intelligence (Effort: Medium-High / Value: Very High)

**Goal**: Combine data across domain boundaries to produce insights unavailable within any single domain.

#### 3.1 Intent × Recommendation CTR Heatmap

- **Cross-domain join**: `Content.intent_id` × `RecommendationClick.context_id` × `RecommendationImpression`
- **Output**: Per-category, per-intent-type: impression count, click count, CTR.
- **Insight**: Which intent types (buying-guide, review, comparison) drive the best recommendation outcomes. Currently the two systems are completely disconnected.
- **Visualization**: Heatmap table. Rows = categories, cols = intent types, cells = CTR %.

#### 3.2 User Interest vs. Content Supply Gap

- **Cross-domain join**: `UserEntityInterest` (user demand per brand/category/topic) × `Content.category_id` / `content_brands`
- **Output**: Top 10 brands/categories where user interest scores are highest but content volume is lowest.
- **Insight**: Real user affinity demand vs. editorial supply — more reliable than inferred demand from views alone.
- **New function**: `get_user_interest_coverage_gap()`

#### 3.3 Source Authority vs. Engagement Validation

- **Cross-domain join**: `Source.authority_score` × engagement generated by that source's content
- **Output**: Table ranking sources by (actual engagement / authority_score). Reveals over-trusted and undervalued sources.
- **Insight**: Authority score validation against real user behavior.

#### 3.4 Geographic Demand Intelligence

- **Cross-domain join**: `ItemClick.country` × `Item.category_id` × `Item.brand_id`
- **Output**: Top 5 countries per category and brand by click volume.
- **Insight**: Where is affiliate click demand concentrated? Currently invisible.
- **New function**: `get_geographic_demand_data()`
- **Visualization**: Ranked table (no map needed — simple sortable table suffices).

#### 3.5 Comment Sentiment × Category Health

- **Cross-domain join**: `Comment` (sentiment, confidence, target_type/id) → `Content.category_id` / `Item.category_id`
- **Output**: Per-category: positive sentiment %, neutral %, negative %. Flag categories with negative sentiment > threshold.
- **New function**: `get_category_sentiment_health()`

#### 3.6 Recommendation → Content → Commerce Chain

- **Cross-domain join**: `RecommendationClick` (entity_id) → `Item.id` → `content_items` → `Content` (what article drove the journey to that item)
- **Output**: Content pieces that serve as effective commerce funnels (their recommendation widget clicks translate into item affiliate clicks).
- **Insight**: Identifies top editorial + commerce combos for prioritizing new content.

---

### Phase 4 — Executive Analytics & Intelligence (Effort: Medium / Value: Strategic)

**Goal**: Aggregate cross-domain intelligence into executive-level views that support strategic decisions.

#### 4.1 Executive Dashboard (`/admin/executive`)

Composite view pulling from all Phases 1-3 functions:
- **System Health Score**: Weighted composite of content completeness, catalog affiliate coverage, recommendation CTR, distribution coverage, stale sources count.
- **Top 3 Weekly Opportunities**: Pull top 3 from existing opportunity scorer.
- **Weekly Engagement Velocity**: 7-day change from `trends.py` for top 3 categories.
- **Risk Summary**: Count of high-severity underperformers + stale sources + dead affiliate links.

#### 4.2 Weekly Performance Digest (Automated Endpoint)

- **New route**: `/admin/executive/digest`
- **Output**: JSON payload consumable for email reports or dashboards.
- **Sources**: All Phase 1-3 functions aggregated into one structured digest payload.
- **Includes**: Top movers, top opportunities, top risks, system health KPIs.

#### 4.3 Cross-Domain KPI Scorecard

Single admin page showing one row per domain with its composite score and a week-over-week delta arrow. Gives a CEO/editor-in-chief level view of operational health across all 7 domains in one table.

#### 4.4 Content Lifecycle View

For any selected content piece, show its full journey:
1. **Ingested** — `ingested_at`
2. **Published** — `published_at`
3. **Distributed** — First `DistributionPost.publish_date` per platform
4. **Engaged** — Recommendation impressions received, clicks, reactions, saves
5. **Commerce impact** — Linked items clicked via `content_items` + `ItemClick`

All data is available. This is a per-content drill-down, not a batch computation.

#### 4.5 Taxonomy Intelligence Dashboard (`/admin/taxonomy`)

- **Topic concentration**: Bar chart of content count per topic, sorted descending. Identify saturated and barren topics.
- **Category hierarchy health**: Tree view of `Category` with `is_leaf` flags and content/item counts per node.
- **Attribute coverage matrix**: Which categories have most attribute-tagged content.

---

## 10. Implementation Prioritization Matrix

| Initiative | Phase | Effort | Value | Dependencies |
|------------|-------|--------|-------|-------------|
| Expose `is_simulated` flag | 1 | Trivial | Medium | None |
| Review queue aging widget | 1 | Low | High | None |
| Stale source detection | 1 | Low | High | None |
| Recommendation coverage rate | 1 | Low | High | None |
| Share channel breakdown | 1 | Low | Medium | None |
| Surface content decay leaders | 1 | Low | High | None |
| Content completeness audit | 2 | Medium | High | None |
| Item catalog health dashboard | 2 | Medium | Very High | None |
| Source intelligence dashboard | 2 | Medium | High | None |
| Content-to-commerce attribution | 2 | Medium | Very High | `content_items` populated |
| Distribution intelligence | 2 | Medium | High | None |
| Demand-coverage quadrant chart | 2 | Low | High | Extend existing function |
| Intent × Rec CTR heatmap | 3 | Medium | Very High | Phase 2 complete |
| User interest vs. supply gap | 3 | Medium | Very High | UserEntityInterest data |
| Source authority validation | 3 | Low | High | Phase 2 source work |
| Geographic demand intelligence | 3 | Low | Medium | ItemClick.country |
| Comment sentiment health | 3 | Medium | Medium | Comment.sentiment populated |
| Recommendation-commerce chain | 3 | High | Very High | Phase 2 commerce work |
| Executive dashboard | 4 | Medium | Strategic | Phase 1-3 complete |
| Weekly digest endpoint | 4 | Medium | Strategic | Phase 1-3 complete |
| KPI scorecard | 4 | Low | High | Phase 1-3 data functions |
| Content lifecycle view | 4 | Medium | High | Phase 2 distribution work |
| Taxonomy intelligence dashboard | 4 | Low | Medium | None |

---

## 11. Open Questions

> [!IMPORTANT]
> **Priority questions before starting Phase 2:**
>
> 1. **`content_items` population**: Is the `content_items` join table actively populated when articles are published? The entire content-to-commerce attribution chain (Phase 2.4, Phase 3.6) depends on this data existing. If it is sparse, these initiatives should be deprioritized.
>
> 2. **`Comment.sentiment`**: Is sentiment classification currently running and populating `Comment.sentiment` + `Comment.confidence`? If the field exists but is empty, the sentiment health features (Phase 3.5) have no value yet.
>
> 3. **`UserEntityInterest` population**: Is the recommendation interest scoring actively writing to `user_entity_interests`? The user-interest-vs-supply-gap analysis (Phase 3.2) is high value only if this table has meaningful data.
>
> 4. **Multi-worker deployment**: The in-process `INSIGHTS_CACHE` in `insights.py` will produce inconsistent results across Gunicorn workers. Should this be migrated to Redis or a shared backend before Phase 2 adds more cached endpoints?
>
> 5. **Distribution post metrics**: Are `views_count`, `likes_count`, `clicks_count` on `DistributionPost` populated by manual entry or API sync? The comment in `performance_feedback.py` notes this as a future feedback loop. Knowing the data quality here determines how aggressively Phase 2 distribution intelligence can be developed.

> [!WARNING]
> **Simulated data risk**: The `performance_feedback.py` module uses `c_id % 20` arithmetic simulation when no real `RecommendationImpression` data exists for a content piece. The `is_simulated` flag is in the payload but is not rendered in any template. Admins currently cannot distinguish real vs. simulated performance evaluations. This should be addressed in Phase 1 before any further intelligence is built on top of performance feedback outputs.
