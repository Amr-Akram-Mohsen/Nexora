# Distribution Intelligence — Implementation Plan
> **Role:** Senior Content-Distribution Architect · Publishing-Operations Specialist · Social-Distribution Analyst · Admin-Dashboard UX Expert
> **Scope:** Maximize operational value from existing distribution data. No architectural redesign.

---

## 1. Distribution Data Inventory

### 1.1 Models Available

| Model | Table | Key Fields |
|---|---|---|
| `DistributionPlatform` | `distribution_platforms` | `id`, `name`, `is_active`, `created_at` |
| `DistributionPost` | `distribution_posts` | `id`, `platform_id`, `source_target_type`, `source_target_id`, `status`, `platform_specific_text`, `external_url`, `publish_date`, `created_at`, `updated_at`, `views_count`, `likes_count`, `clicks_count`, `shares_count` |

### 1.2 Status Vocabulary

| Status | Meaning |
|---|---|
| `draft` | Post exists but is unpublished and may still need editing |
| `scheduled` | Post is approved and has a target `publish_date` in the future |
| `published` | Post has been published; `external_url` may be available |

### 1.3 Source Target Types

| Value | Entity |
|---|---|
| `content` | Nexora Content entity |
| `item` | Nexora Item entity |

### 1.4 Performance Metrics Available

| Metric | Column | Notes |
|---|---|---|
| Views | `views_count` | Currently manual / future API sync |
| Likes | `likes_count` | Currently manual / future API sync |
| Clicks | `clicks_count` | Currently manual / future API sync |
| Shares | `shares_count` | Currently manual / future API sync |

### 1.5 Timestamp Fields

| Field | Purpose |
|---|---|
| `publish_date` | Target or actual publish date. Nullable. Used for scheduling. |
| `created_at` | Record creation timestamp |
| `updated_at` | Last modification timestamp |

### 1.6 Currently Underutilized Fields

| Field | Current Utilization | Hidden Value |
|---|---|---|
| `shares_count` | **Never exposed in any UI component** | Viral amplification signal |
| `external_url` | Only shown in modal if status is not `published` | Direct verification of live post |
| `updated_at` | Never surfaced in admin views | Staleness detection for drafts |
| `is_active` (Platform) | Not surfaced in social distribution tracking | Platform health indicator |
| `platform_specific_text` | Only editable in modal | Caption quality signal |
| `publish_date` | Shown as raw date string in table only | Scheduling urgency, overdue detection |

---

## 2. Distribution Relationship Mapping

### 2.1 Primary Relationship Graph

```
DistributionPlatform (1)
    └── DistributionPost (N)           [platform_id FK → distribution_platforms.id]
            ├── Content (0..1)         [source_target_type='content', source_target_id → content.id]
            └── Item (0..1)            [source_target_type='item', source_target_id → item.id]
```

### 2.2 Direct Relationships

| Relationship | Mechanism | Operational Meaning |
|---|---|---|
| Platform → Posts | `back_populates="platform"` | All posts published on a given platform |
| Post → Content | `primaryjoin` viewonly, selectin | Content entity behind the distribution post |
| Post → Item | `primaryjoin` viewonly, selectin | Item entity behind the distribution post |
| Post.source | Python property `content_target or item_target` | Unified accessor regardless of target type |

### 2.3 Indirect Relationships (Currently Unexploited)

| Relationship | How to Derive | Operational Insight |
|---|---|---|
| Content → Platforms | Via posts where `source_target_type='content'` | Which platforms distribute this content piece |
| Item → Platforms | Via posts where `source_target_type='item'` | Which platforms distribute this item |
| Platform → Content Count | Count posts by platform + type | Platform focus distribution |
| Platform → Total Engagement | Sum metrics by platform | Platform-level ROI signal |
| Content without Distribution | Content LEFT JOIN posts → null | Coverage gap |
| Item without Distribution | Item LEFT JOIN posts → null | Coverage gap |
| Stale Drafts | `status='draft'` AND `updated_at < NOW() - N days` | Operational health risk |
| Overdue Scheduled | `status='scheduled'` AND `publish_date < NOW()` | Publishing failure signal |
| Dead Posts | `status='published'` AND `views_count=0` | Broken or low-reach posts |

### 2.4 Composite Engagement Signal (Computable from Existing Data)

```
Engagement Score = views_count + (likes_count × 2) + (shares_count × 3) + (clicks_count × 1.5)
```
This is derivable today from existing columns. It is currently **nowhere computed or surfaced**.

---

## 3. Distribution Coverage Analysis

### 3.1 Coverage Gaps — What Is Missing

The `widget/social-distribution` endpoint fetches the last 50 posts ordered by `created_at`. It does **not** answer these critical operational questions:

| Gap | Description | Impact |
|---|---|---|
| Undistributed Content | Content entities with zero posts of any status | Zero reach |
| Undistributed Items | Item entities with zero posts of any status | Zero reach |
| Single-Platform Content | Content distributed on only one platform | Underutilized reach |
| Platform Monopolization | One platform absorbing most distribution effort | Platform risk |
| Draft Accumulation | Many posts stuck at `draft` status | Publishing velocity signal |
| Scheduled Backlog | Posts with `publish_date` passed but still `scheduled` | Publishing failure |
| Published Without URL | `status='published'` AND `external_url IS NULL` | Verification gap |

### 3.2 Coverage Metrics to Expose (All Derivable Now)

| Metric | Query Basis |
|---|---|
| Total Content Distributed | `COUNT(DISTINCT source_target_id) WHERE source_target_type='content' AND status='published'` |
| Total Items Distributed | `COUNT(DISTINCT source_target_id) WHERE source_target_type='item' AND status='published'` |
| Coverage % (Content) | Distributed Content / Total Content × 100 |
| Coverage % (Items) | Distributed Items / Total Items × 100 |
| Platform Post Count | `GROUP BY platform_id, COUNT(*)` |
| Platform Engagement Total | `GROUP BY platform_id, SUM(views+likes+clicks+shares)` |
| Avg Posts per Content | Total Content Posts / Distinct Content IDs |
| Avg Posts per Item | Total Item Posts / Distinct Item IDs |

### 3.3 Multi-Platform Distribution Density

Track how many platforms each content/item is distributed on. Target: every published content piece should ideally appear on at least 2 platforms. This "multi-platform score" is computable from existing data.

---

## 4. Publishing Workflow Visibility

### 4.1 Current State

The distribution page has four sections:
1. **Tactical Action Queue** — AI-driven, derived from `get_decision_intelligence_data()`
2. **Content Publishing Plan** — AI-generated weekly kanban (YouTube, Pinterest, Blog — hardcoded)
3. **Social Distribution Tracking** — Table of last 50 posts (platform, title, source type, status, publish date, views, likes, clicks)
4. **Autonomous Execution + Governance** — AI pipeline

### 4.2 What Is Missing from Each Section

#### Social Distribution Tracking Table
| Missing Column | Operational Value |
|---|---|
| `shares_count` | Viral amplification, never surfaced |
| `external_url` presence indicator | Whether live link exists (✓/✗ icon) |
| `updated_at` (draft age) | Staleness detection |
| Engagement Score | Combined signal — currently not computed anywhere |
| Source Type badge | Content vs Item disambiguation (currently text only) |
| Overdue flag | `scheduled` posts past `publish_date` |

#### Publishing Plan Kanban
| Gap | Impact |
|---|---|
| Hardcoded platforms: `youtube`, `pinterest`, `blog` | Does not reflect actual `DistributionPlatform` records |
| No link to actual `DistributionPost` records | Plan exists in AI cache, disconnected from DB state |
| No draft count per week column | Missing publishing funnel context |
| No published count per week column | Missing velocity context |

#### Workflow Indicators Missing
- No **Draft Queue** count badge visible on page load
- No **Scheduled Upcoming** countdown or summary
- No **Overdue Scheduled** alert
- No **Published Today / This Week** count
- No **Platform Health** status (is_active = false platforms)

---

## 5. Admin List View Improvements

### 5.1 Social Distribution Table — Current Columns

```
platform | source_title | source_type | status | publish_date | views | likes | clicks
```

### 5.2 Recommended Column Improvements

| Priority | Column | Improvement Recommendation |
|---|---|---|
| **High** | `status` | Replace text with colored badge (draft=gray, scheduled=amber, published=green) |
| **High** | `source_type` | Replace plain text with Content/Item icon badge |
| **High** | `shares` | Add `shares_count` column — currently completely missing |
| **High** | `engagement` | Add computed Engagement Score column |
| **Medium** | `publish_date` | Show relative time (e.g., "2 days ago", "in 3 days") + overdue indicator |
| **Medium** | `external_url` | Show ✓ / ✗ link existence indicator |
| **Medium** | `platform` | Replace text with platform icon + name badge |
| **Low** | `updated_at` | Show draft age for draft-status posts only (staleness hint) |

### 5.3 Table-Level Filters to Add

| Filter | Basis |
|---|---|
| Status filter (All / Draft / Scheduled / Published) | `status` column |
| Platform filter | `platform_id` JOIN |
| Source type filter (All / Content / Item) | `source_target_type` |
| Date range filter | `publish_date` |

### 5.4 Table-Level Summary Bar

Add a compact summary row above the table showing:

```
[Draft: N]  [Scheduled: N]  [Published: N]  [Overdue: N]  [No URL: N]
```

---

## 6. Inspect / Detail View Improvements

### 6.1 Current Modal State

The `_distribution_modal_inner.html` shows:
- Platform name + Post Type
- Status badge
- `platform_specific_text` (editable textarea)
- `external_url` (input, unpublished only)
- Mark as Published button

### 6.2 Recommended Information Hierarchy for Detail View

#### Section 1: Source Entity Context
- Source type badge (Content / Item)
- Source entity title (linked to source inspect page)
- Source entity ID
- Source entity status (published, draft)
- Source entity category / tags (if available)

#### Section 2: Platform Details
- Platform name + icon
- Platform `is_active` status
- Total posts on this platform for this source (cross-reference count)
- Platform-level engagement totals for this source

#### Section 3: Publishing Details
- Current `status` badge (color-coded)
- `publish_date` (formatted with relative time)
- `created_at` + `updated_at`
- Draft age (if status = draft)
- Overdue indicator (if status = scheduled and `publish_date` < NOW)
- `external_url` — clickable link with open icon (if published)

#### Section 4: Platform-Specific Content
- `platform_specific_text` textarea (editable if not published)
- Character count indicator
- Post type label

#### Section 5: Performance Summary (if published)
| Metric | Display |
|---|---|
| Views | `views_count` with icon |
| Likes | `likes_count` with icon |
| Clicks | `clicks_count` with icon |
| Shares | `shares_count` with icon — **CURRENTLY MISSING** |
| Engagement Score | Computed from all four metrics |

---

## 7. Distribution Performance Analytics

All analytics below are derivable **exclusively** from existing model fields.

### 7.1 Platform Performance

| Metric | Derivation |
|---|---|
| Posts per Platform | `GROUP BY platform_id COUNT(*)` |
| Published per Platform | `WHERE status='published' GROUP BY platform_id` |
| Total Views per Platform | `SUM(views_count) GROUP BY platform_id` |
| Total Likes per Platform | `SUM(likes_count) GROUP BY platform_id` |
| Total Clicks per Platform | `SUM(clicks_count) GROUP BY platform_id` |
| Total Shares per Platform | `SUM(shares_count) GROUP BY platform_id` |
| Engagement per Platform | Combined sum of all metrics per platform |
| Avg Engagement per Post | Per-platform engagement / post count |
| Draft Rate per Platform | `draft count / total count` per platform |

### 7.2 Content Performance by Platform

| Metric | Derivation |
|---|---|
| Top Performing Content | `WHERE source_target_type='content' ORDER BY views_count DESC` |
| Content → Platform Matrix | Content ID vs Platform engagement pivot |
| Content with Most Platforms | `GROUP BY source_target_id COUNT(DISTINCT platform_id)` |
| Content Click Leaders | `WHERE source_target_type='content' ORDER BY clicks_count DESC` |

### 7.3 Item Performance by Platform

| Metric | Derivation |
|---|---|
| Top Performing Items | `WHERE source_target_type='item' ORDER BY views_count DESC` |
| Item Distribution Spread | Items distributed on N platforms |
| Item Engagement by Platform | Cross-tab of item × platform engagement |

### 7.4 Publishing Volume Trends

| Metric | Derivation |
|---|---|
| Posts Published per Day/Week | `GROUP BY DATE(publish_date) WHERE status='published'` |
| Draft Creation Rate | `GROUP BY DATE(created_at) WHERE status='draft'` |
| Draft-to-Published Conversion Time | `publish_date - created_at` for published posts |
| Scheduling Lead Time | `publish_date - created_at` for scheduled posts |
| Publishing Velocity | Published posts per week (trend) |

### 7.5 Engagement Rate Metrics (Computable)

| Metric | Formula |
|---|---|
| Click-Through Rate (CTR) | `clicks_count / views_count` (where views > 0) |
| Like Rate | `likes_count / views_count` |
| Share Rate | `shares_count / views_count` |
| Engagement Rate | `(likes + clicks + shares) / views` |
| Top Click Driver | Highest CTR post per platform |

---

## 8. Visualization Opportunities

### 8.1 KPI Cards Strip (Page-Level Header)

Place these KPI cards at the top of the Distribution page, populated from DB queries (not AI cache):

| Card | Value | Sub-text |
|---|---|---|
| Total Posts | Count of all `DistributionPost` records | Across all platforms |
| Published | Count where `status='published'` | Live on platforms |
| Scheduled | Count where `status='scheduled'` | Upcoming queue |
| Drafts | Count where `status='draft'` | In progress |
| Overdue | Count where `scheduled` AND `publish_date < NOW()` | ⚠️ Requires action |
| Total Views | `SUM(views_count)` | Reach to date |
| Total Engagement | `SUM(views+likes+clicks+shares)` | Full engagement signal |

**Placement:** Above the Tactical Action Queue section.

### 8.2 Platform Distribution Bar Chart

**What:** Horizontal bar chart showing post count and engagement per platform.
**Data:** `GROUP BY platform_id` with metric sums.
**Placement:** New "Platform Overview" section, between KPI cards and Action Queue.

### 8.3 Publishing Status Donut / Pie Chart

**What:** Draft / Scheduled / Published proportions.
**Data:** Status count from `DistributionPost`.
**Placement:** Next to Platform bar chart in Platform Overview section.

### 8.4 Coverage Dashboard Panel

**What:** Two coverage meters:
- Content Coverage: `% of Content entities with at least one published post`
- Item Coverage: `% of Item entities with at least one published post`

**Data:** Cross-join Content/Item counts with distinct `source_target_id` counts.
**Placement:** New "Distribution Coverage" section.

### 8.5 Publishing Velocity Sparkline

**What:** Line chart showing posts published per day/week over time.
**Data:** `GROUP BY DATE(publish_date) WHERE status='published'`.
**Placement:** Inside Coverage dashboard or separate "Trends" row.

### 8.6 Engagement Performance Table

**What:** Per-platform table showing:
- Platform name
- Total posts
- Total views, likes, clicks, shares
- Computed CTR
- Computed engagement rate

**Placement:** New "Engagement Performance" panel below Social Distribution Tracking.

### 8.7 Scheduling Dashboard

**What:** Timeline view of upcoming scheduled posts sorted by `publish_date`.
**Columns:** Platform, Source Title, Source Type, Scheduled Date, Relative Time, Overdue badge.
**Placement:** Dedicated "Scheduling Queue" panel, separated from the main tracking table.

### 8.8 Distribution Health Panel

**What:** Health checklist-style panel with actionable counts:
- Drafts older than 7 days: N
- Overdue scheduled posts: N
- Published posts with no external URL: N
- Published posts with zero views: N
- Platforms with no posts this month: N

**Placement:** Below governance panel, or as a sidebar widget.

---

## 9. Distribution Health & Quality Visibility

### 9.1 Health Signals Available from Existing Data

| Signal | Detection Query | Severity |
|---|---|---|
| Stale Drafts | `status='draft' AND updated_at < NOW() - 7 days` | Warning |
| Overdue Scheduled | `status='scheduled' AND publish_date < NOW()` | Critical |
| Published Without URL | `status='published' AND external_url IS NULL` | Warning |
| Zero-View Published Posts | `status='published' AND views_count = 0` | Info |
| Zero-Engagement Published | All metrics = 0 AND status = published | Warning |
| Inactive Platform Posts | Platform `is_active=False` but posts still exist | Info |
| Content with Zero Distribution | Content LEFT JOIN posts null | Info |
| Items with Zero Distribution | Item LEFT JOIN posts null | Info |

### 9.2 Recommended Operational Indicators

| Indicator | Location |
|---|---|
| Overdue badge (🔴 Overdue) | Social Distribution table row, scheduled posts past date |
| Stale draft badge (🟡 Stale) | Rows where `status=draft` and `updated_at` is old |
| Missing URL warning (⚠️) | Published rows without `external_url` |
| Dead post flag | Published rows with 0 across all metrics for 7+ days |
| Coverage health bar | Distribution Coverage panel (% content + % items distributed) |
| Platform health indicator | Platform list showing `is_active` + last post date |

### 9.3 Health Workflow Recommendation

Introduce a **Distribution Health Summary** that appears as a contextual alert strip below the KPI cards when any of the following is true:
- Overdue scheduled posts > 0 → Red alert
- Stale drafts > 5 → Yellow alert
- Content coverage < 50% → Orange alert
- Item coverage < 50% → Orange alert

---

## 10. Existing Data Utilization Score

| Field / Metric | Current Utilization | Utilization Grade |
|---|---|---|
| `views_count` | Shown in table | ✅ Utilized |
| `likes_count` | Shown in table | ✅ Utilized |
| `clicks_count` | Shown in table | ✅ Utilized |
| `shares_count` | **Never shown anywhere** | 🔴 Zero utilization |
| `external_url` | Only in draft modal (never shown in table) | 🔴 Near-zero |
| `publish_date` | Shown as raw string only | 🟡 Underutilized |
| `updated_at` | **Never shown** | 🔴 Zero utilization |
| `created_at` | **Never shown** | 🔴 Zero utilization |
| `status` | Shown as raw text | 🟡 Underutilized (needs badge + filter) |
| `platform_specific_text` | Editable in modal only | 🟡 Underutilized |
| `source_target_type` | Shown as raw text | 🟡 Underutilized (needs badge) |
| `DistributionPlatform.is_active` | **Never surfaced** | 🔴 Zero utilization |
| Engagement Score (computed) | **Never computed or shown** | 🔴 Missing entirely |
| CTR (computed) | **Never computed or shown** | 🔴 Missing entirely |
| Coverage % (computed) | **Never computed or shown** | 🔴 Missing entirely |
| Draft Age (computed) | **Never computed or shown** | 🔴 Missing entirely |
| Overdue Detection (computed) | **Never computed or shown** | 🔴 Missing entirely |

**Overall Utilization Score: ~25% of available data is surfaced with operational value.**

---

## 11. Architectural Finding: Two Separate Distribution Systems

> [!IMPORTANT]
> The distribution page currently contains **two operationally distinct systems** that are visually merged but functionally separate.

### System A — AI-Driven Publishing Intelligence
- **Source:** `get_decision_intelligence_data()`, `generate_content_strategy()`, `generate_content_publishing_plan()`, `generate_execution_plan()`, `generate_execution_governance_layer()`
- **Storage:** In-memory cache only (`get_cached` / `set_cached`)
- **Data:** Not persisted to database
- **Sections:** Action Queue, Publishing Plan Kanban, Autonomous Execution, Governance

### System B — Database-Persisted Distribution Tracking
- **Source:** `DistributionPost` + `DistributionPlatform` models
- **Storage:** `distribution_posts` and `distribution_platforms` database tables
- **Data:** Real, persisted publishing records with metrics
- **Sections:** Social Distribution Tracking table

### The Problem
System A (AI pipeline) and System B (actual DB records) **do not communicate**. The AI publishing plan recommends actions. System B records actual publishing history. There is no feedback loop, no reconciliation, and no visibility into alignment between planned and actual publishing.

> [!WARNING]
> The `widget/social-distribution` endpoint returns only 50 posts with no pagination, no filtering, no aggregation, and no health signals. It delegates rendering to `admin/content_intelligence/_insights_rows.html` — a template from a different domain, suggesting the social distribution tracking is still using a generic widget not purpose-built for distribution.

---

## 12. Phased Implementation Roadmap

### Phase 1 — Quick Wins & Visibility Improvements
**Effort:** Low | **Value:** High | **Time Estimate:** 1–3 days

#### 1.1 Fix the Social Distribution Table
- Add `shares_count` column to `widget/social-distribution` view model and table template
- Add `external_url` presence indicator (✓/✗) to table
- Replace status text with colored status badge (draft=gray, scheduled=amber, published=green)
- Replace `source_type` text with Content/Item icon badge
- Add relative time formatting to `publish_date` (e.g., "3 days ago", "in 2 days")
- Add `updated_at` to view model for draft staleness display

#### 1.2 Add KPI Cards Strip to Distribution Page Header
- New endpoint: `GET /admin/distribution/stats/overview`
- Returns: total posts, published count, scheduled count, draft count, overdue count, total views, total engagement
- Render as 7 KPI cards above the Action Queue section
- Requires: 2 aggregate SQL queries over `DistributionPost`

#### 1.3 Add Status Summary Bar Above the Social Distribution Table
- Display inline: `[Draft: N] [Scheduled: N] [Published: N] [Overdue: N]`
- Add as part of the `widget/social-distribution` response headers or in a separate fast endpoint
- Zero JS overhead — inject as part of existing widget response

#### 1.4 Expose `shares_count` in Modal
- Add Shares row to `_distribution_modal_inner.html` performance section
- Add computed Engagement Score display row

---

### Phase 2 — Publishing Workflow Enhancements
**Effort:** Medium | **Value:** High | **Time Estimate:** 3–5 days

#### 2.1 Add Status Filters to Social Distribution Tracking
- Add filter bar above distribution table: All / Draft / Scheduled / Published
- Extend `widget/social-distribution` endpoint to accept `?status=` query param
- Add platform filter dropdown and source type filter

#### 2.2 Add Scheduling Queue Panel
- New widget endpoint: `GET /admin/distribution/widget/scheduling-queue`
- Query: `status='scheduled' ORDER BY publish_date ASC` (all upcoming)
- Template: sorted list showing platform, source, title, publish_date, relative countdown, overdue badge
- Separate from Social Distribution Tracking — focused purely on future schedule

#### 2.3 Add Distribution Health Alert Strip
- New endpoint: `GET /admin/distribution/stats/health`
- Returns: stale_drafts_count, overdue_scheduled_count, published_no_url_count, zero_view_published_count
- Render as dismissable contextual alert strip below KPI cards
- Critical (overdue > 0) = red; Warning (stale > 5) = amber; Info = blue

#### 2.4 Upgrade Social Distribution Widget to Purpose-Built Template
- Create new `_social_distribution_rows.html` replacing the generic `content_intelligence/_insights_rows.html`
- Include all new columns: shares, URL indicator, relative dates, status badge, source type badge
- Add pagination support (next 50 posts) via `?page=` param on widget endpoint

#### 2.5 Improve Distribution Modal Detail View
- Restructure `_distribution_modal_inner.html` following the 5-section hierarchy:
  1. Source entity context
  2. Platform details + `is_active` status
  3. Publishing details (dates, age, overdue flag)
  4. Platform-specific content area
  5. Performance summary (all 4 metrics + engagement score)

---

### Phase 3 — Distribution Analytics
**Effort:** Medium–High | **Value:** High | **Time Estimate:** 5–8 days

#### 3.1 Platform Performance Analytics Endpoint
- New endpoint: `GET /admin/distribution/analytics/platforms`
- Returns per-platform: post_count, published_count, draft_count, total_views, total_likes, total_clicks, total_shares, avg_engagement, ctr
- Render as: horizontal bar chart (views, engagement) + sortable table

#### 3.2 Distribution Coverage Dashboard
- New endpoint: `GET /admin/distribution/analytics/coverage`
- Joins `Content` and `Item` tables against `DistributionPost` to compute:
  - content_total, content_distributed, content_coverage_pct
  - items_total, items_distributed, items_coverage_pct
  - content_multi_platform_count (distributed on 2+ platforms)
  - items_multi_platform_count
- Render as: two large coverage meters + breakdown by platform

#### 3.3 Engagement Performance Table
- New endpoint: `GET /admin/distribution/analytics/engagement`
- Per-platform aggregated engagement: CTR, like rate, share rate, engagement rate
- Render as: sortable table with sparkline trend if multi-week data available

#### 3.4 Publishing Volume Trend Sparkline
- New endpoint: `GET /admin/distribution/analytics/publishing-trend`
- Returns: `GROUP BY DATE(publish_date)` for last 30 days, count of published posts per day
- Render as: simple line sparkline in the KPI card strip or Distribution Coverage panel

#### 3.5 Content & Item Performance Leaderboards
- New endpoint: `GET /admin/distribution/analytics/top-content`
- Returns: top 10 content by views, top 10 items by views, top by clicks (CTR)
- Render as: compact ranked lists with platform badges

---

### Phase 4 — Advanced Publishing Intelligence
**Effort:** High | **Value:** High | **Time Estimate:** 8–14 days

#### 4.1 AI-to-DB Feedback Loop
- When the Autonomous Execution Panel marks a task as executed, write a corresponding `DistributionPost` record to the database
- This closes the loop between System A (AI) and System B (DB) identified in Architecture Finding §11
- Creates real publishing history that feeds back into analytics

#### 4.2 Distribution Coverage Gap Workflow
- New workflow page or panel: "Undistributed Content & Items"
- Lists all Content and Item entities with `source_target_id` not in `distribution_posts` at all
- Each row has a "Generate Draft" action button (already exists: `/social-distribution/generate`)
- Filter by category, type, date range

#### 4.3 Platform Utilization Intelligence
- Show platform-level utilization: posts per week per platform + trend
- Surface platforms that have gone X days without a new published post
- Surface platforms where `is_active=False` but still have active posts

#### 4.4 Multi-Platform Coverage Matrix
- Visual heatmap: Content/Item rows × Platform columns
- Cell = published ✓ / scheduled ⏰ / draft ✏️ / missing ✗
- Enables at a glance: which content has been distributed everywhere, which hasn't

#### 4.5 Publishing Calendar View
- Replace the AI-only weekly kanban with a real calendar backed by `publish_date`
- Show: actual scheduled posts (from DB) merged with AI-recommended tasks
- Color coding: DB-scheduled (blue), AI-recommended (purple), overdue (red)

#### 4.6 Distribution Trend Comparison
- Compare platform performance month-over-month
- Compare content vs item distribution volume over time
- Show publishing velocity trend: are we publishing more or fewer posts per week?

---

## Open Questions

> [!IMPORTANT]
> **1. AI Plan ↔ DB Reconciliation Priority**
> The AI publishing plan (System A) and real DB posts (System B) are completely separate. Is connecting them in scope, or should the two systems remain independent with separate visibility sections?

> [!IMPORTANT]
> **2. Pagination for Social Distribution Table**
> The widget currently limits to 50 posts. With 50+ records, critical visibility is lost. Should pagination be added in Phase 1 or Phase 2?

> [!NOTE]
> **3. Platform Icon Set**
> The publishing plan kanban hardcodes icons for YouTube, Pinterest, and Blog. Are there additional platforms in `distribution_platforms` that need icon support?

> [!NOTE]
> **4. Metric Sync**
> Metrics (views, likes, clicks, shares) are currently manual. Is there an API sync plan? This affects whether CTR and engagement rate analytics have reliable data.

> [!NOTE]
> **5. Coverage Denominator**
> Distribution coverage % requires knowing total Content and Item counts. Should coverage be calculated against ALL content/items or only published/active ones?
