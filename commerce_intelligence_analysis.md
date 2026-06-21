# Commerce Intelligence Analysis — Nexora
> Role: Senior Commerce Architect · Affiliate-Operations Analyst · Catalog-Management Specialist · Admin-Dashboard UX Expert  
> Scope: Visibility, Management, Monitoring & Analytics — no architectural changes

---

## 1. Commerce Data Inventory

### 1.1 Model Surface

| Layer | Model | Key Fields Available |
|---|---|---|
| **Store** | `Store` | `name`, `slug`, `website`, `country`, `currency`, `affiliate_network`, `network_slug`, `api_enabled`, `feed_enabled`, `logo_url`, `is_active`, `created_at` |
| **Link** | `ItemStoreLink` | `affiliate_url`, `original_url`, `price`, `old_price`, `currency`, `availability`, `commission_rate`, `program_name`, `merchant_category`, `tracking_code`, `network_metadata` (JSON), `external_item_id`, `deeplink_generated_at`, `last_synced_at`, `last_checked_at`, `is_active`, `created_at` |
| **Variant** | `ItemVariant` | `price`, `old_price`, `currency`, `attributes`, `sku`, `is_default`, `created_at` |
| **Item** | `Item` | `click_count`, `view_count`, `save_count`, `like_count`, `dislike_count`, `share_count`, `comment_count`, `rating`, `review_count`, `item_type`, `brand_id`, `category_id`, `source_id` |
| **Interactions** | `ItemClick`, `View` | `item_store_link_id`, `target_id`, `target_type` |

### 1.2 Rich but Under-Used Fields in `ItemStoreLink`

The following fields exist in the DB schema but are **completely absent** from admin surfaces:

| Field | Type | Current Admin Use |
|---|---|---|
| `commission_rate` | `Numeric(5,2)` | Only in `coverage_stats` (avg per store) — never at link level |
| `program_name` | `String(100)` | Not shown anywhere in list/inspect |
| `merchant_category` | `String(255)` | Mapped in inspect modal only, shown as "—" |
| `tracking_code` | `String(255)` | Never surfaced |
| `network_metadata` | `JSON` | Shown as raw object in inspect — never parsed |
| `deeplink_generated_at` | `DateTime` | Never surfaced |
| `last_checked_at` | `DateTime` | Shown in inspect but not in dashboards |
| `old_price` | `Numeric(10,2)` | Discount flag exists (`has_discount`) but actual savings % never computed |
| `original_url` | `Text` | In inspect only — never compared to affiliate URL for drift detection |
| `external_item_id` | `String(150)` | In inspect only — never used for deduplication visibility |

### 1.3 Rich but Under-Used Fields in `Store`

| Field | Current Admin Use |
|---|---|
| `network_slug` | Never surfaced anywhere |
| `feed_enabled` | Never surfaced anywhere |
| `api_enabled` | In inspect — not in list or dashboards |
| `logo_url` | Never used in admin |
| `country` | In inspect only |
| `currency` | In inspect only |
| `created_at` | Never surfaced |

---

## 2. Relationship Mapping

```
Item (1)
  └── ItemVariant (N)          ← price, old_price, currency, attributes, sku
        └── ItemStoreLink (N)  ← affiliate commerce layer (ALL affiliate data)
              └── Store (1)    ← merchant identity & configuration
              └── ItemClick    ← interaction trace
```

**Key structural observations:**
- A single Item can have prices across **multiple variants × multiple stores** — price dispersion is rich but unexposed.
- `ItemStoreLink.commission_rate` is per-link, enabling per-product, per-store commission analysis.
- `deeplink_generated_at` vs `last_synced_at` vs `last_checked_at` represents a **3-tier sync timeline** that is currently collapsed into a single "Never Synced" count.
- `network_metadata` (JSON) may contain affiliate-network-specific payloads (clickout IDs, deeplink tokens, etc.) — completely opaque in admin.
- `merchant_category` is a **store-side** classification that can diverge from Nexora's own taxonomy — this gap is never visualized.

---

## 3. Store Coverage Analysis

### 3.1 What Is Currently Tracked

| Metric | Tracked? | Notes |
|---|---|---|
| Total stores | ✅ | Via `Store` count |
| Active stores | ✅ | `is_active` flag |
| Products per store | ✅ | `_fetch_stores_page` — distinct items via variants |
| Clicks per store | ✅ | Via `ItemClick` join |
| CTR per store | ✅ | clicks/views — but views is overcounted (joins all item views, not link-specific) |
| Conversions | ❌ | Hardcoded `0` in serializer — never implemented |
| Store OOS rate | ✅ | `get_store_health_stats` — top 5 only |
| Category coverage | ✅ | `get_store_coverage_stats` |
| Commission rates | ✅ | Avg per store |
| Inactive stores with links | ❌ | Never shown |
| Stores added this month | ❌ | `created_at` never used |
| API-enabled vs feed-enabled | ❌ | Never in dashboards |
| Stores without any link | ❌ | Zero-product ghost stores |
| Country/currency distribution | ❌ | Never visualized |

### 3.2 Critical Gaps

1. **Ghost stores** — inactive or zero-product stores that occupy affiliate budget/configuration but yield no revenue.
2. **Store growth trend** — `Store.created_at` is never used; no onboarding velocity visible.
3. **Network distribution** — which affiliate networks dominate the catalog is not surfaced at the store-list level.
4. **Feed vs API stores** — stores where `feed_enabled=True` but `api_enabled=False` (or vice versa) represent different sync mechanisms; lumped together.

---

## 4. Affiliate Coverage Analysis

### 4.1 What Is Currently Tracked

| Metric | Tracked? | Notes |
|---|---|---|
| Affiliate URL existence | ✅ | `affiliate_url` is NOT NULL by constraint |
| Program name | ❌ | Never surfaced in lists |
| Commission rate distribution | ✅ | Avg per store in panel |
| Links with commission defined | ❌ | Never counted |
| Links without commission | ❌ | Never flagged |
| Deeplink age | ❌ | `deeplink_generated_at` completely unused |
| Tracking code coverage | ❌ | `tracking_code` completely unused |
| Network metadata richness | ❌ | JSON blob, never parsed |
| Program name distribution | ❌ | `program_name` index exists but never queried for analytics |

### 4.2 Affiliate Health Signals Available but Unused

| Signal | Source Field | Actionable Question |
|---|---|---|
| Stale deeplinks | `deeplink_generated_at` | Deeplinks older than 30d may be expired |
| Missing commissions | `commission_rate IS NULL` | Which products yield no trackable revenue? |
| Orphaned tracking codes | `tracking_code IS NULL` | Which links can't be attribution-tracked? |
| URL drift | `original_url` ≠ `affiliate_url` root domain | Has the merchant changed domains? |
| Program fragmentation | `program_name` cardinality | How many programs per store — complexity indicator |

---

## 5. Pricing Visibility Analysis

### 5.1 What Is Currently Tracked

| Metric | Tracked? | Notes |
|---|---|---|
| Min price per item | ✅ | Via `_load_item_aggregates` |
| Max price per item | ✅ | Via `_load_item_aggregates` |
| Has discount (any store) | ✅ | `has_discount` flag — binary only |
| Price range in list | ✅ | "min – max currency" string |
| Discount percentage | ❌ | Never computed |
| Price freshness | ❌ | `last_synced_at` relative to now exists but is labeled "sync age" not "price age" |
| Price null coverage | ❌ | Links with `price IS NULL` never counted |
| Currency mismatch | ❌ | Link currency vs store currency vs variant currency never reconciled |
| Old price vs new price delta | ❌ | Savings amount/percentage never computed |
| Price spread across stores | ❌ | Cheapest vs most expensive store for same product |
| Stale pricing | ❌ | Links not re-priced in 7/14/30 days |

### 5.2 Stale Pricing Definition

A link has **stale pricing** when `last_synced_at` is older than the operator-defined threshold (default: 7 days). The system already tracks `stale_sync_items` in `items.py` health stats — but this is framed as a **sync** problem, not a **pricing accuracy** problem. These are the same signal viewed from different business dimensions.

### 5.3 Price Intelligence Opportunities

| Insight | Derivable From |
|---|---|
| Best price per product | `MIN(ItemStoreLink.price)` where `is_active=True` |
| Highest-discount product | `(old_price - price) / old_price` sorted desc |
| Products where ALL stores are out-of-stock | `COUNT(*) = COUNT(*) WHERE availability='OutOfStock'` |
| Currency mix across catalog | `GROUP BY currency` on links |
| Price-null rate per store | `SUM(price IS NULL) / COUNT(*)` per store |
| Price staleness by store | `AVG(CURRENT_TIMESTAMP - last_synced_at)` per store |

---

## 6. Store List — Current State & Improvement Opportunities

### 6.1 Current Columns (from `tables.py` `stores.preview_table`)

`Name | Affiliate Network | Product Count | Clicks | CTR | Conversions | Status | Actions`

### 6.2 Problems

| Problem | Evidence |
|---|---|
| **Conversions hardcoded to 0** | `"conversions": 0` in serializer — misleads operators |
| **CTR denominator is wrong** | Views joined via `ItemVariant.item_id` = inflated (all item views, not store-specific views) |
| **No price visibility** | Min/avg price per store never shown |
| **No sync freshness** | `last_synced_at` not in store list |
| **No affiliate program** | `program_name` not in list |
| **No OOS rate** | Only total OOS in health panel — not per row |
| **Status oversimplified** | Only `healthy/warning/failed` — no sub-status (stale, no-commission, etc.) |
| **No filtering** | No filter by network, country, feed/API type, active status |

### 6.3 Recommended List Improvements

**New columns to add (replace Conversions with meaningful data):**

| Column | Source | Priority |
|---|---|---|
| Avg Commission | `AVG(commission_rate)` per store | P1 |
| Sync Age (days) | `MAX(last_synced_at)` per store | P1 |
| OOS Rate (%) | `OOS_links / total_links` per store | P1 |
| Active Link Count | `COUNT(is_active=True)` per store | P1 |
| Affiliate Network | Already present | Keep |
| Price Null Rate | `NULL price / total` per store | P2 |
| Feed / API Badge | `feed_enabled`, `api_enabled` | P2 |

**New filter controls:**
- Filter by `affiliate_network`
- Filter by `country`
- Filter by `is_active`
- Filter by sync staleness (synced in last 7d / 30d / never)
- Filter by OOS rate threshold

**New sortable columns:**
- Sort by `avg_commission_rate`
- Sort by `sync_age`
- Sort by `oos_rate`
- Sort by `product_count`

---

## 7. Store Inspect — Current State & Improvement Opportunities

### 7.1 Current Inspect Fields (from `tables.py` `stores.detailed_table`)

```
store info: id, name, slug, website, status, affiliate network
commercial & localization: country, currency, api enabled, product count
```

### 7.2 Problems

| Problem | Evidence |
|---|---|
| **No live link health** | inspect builds from `Store` only — no `ItemStoreLink` aggregates |
| **No pricing summary** | Min/avg/max price across all links not shown |
| **No sync summary** | Never-synced count, last sync date not shown |
| **No OOS breakdown** | OOS link count not in inspect |
| **No commission summary** | `commission_rate` completely absent |
| **No program listing** | `program_name` distribution not shown |
| **`feed_enabled` absent** | Only `api_enabled` shown |
| **`network_slug` absent** | Network identifier never shown |
| **`logo_url` unused** | Store logo never rendered |

### 7.3 Recommended Inspect Sections

Add a **"Link Health"** section to `stores.detailed_table`:

```python
"link health": [
    "total links", "active links", "inactive links",
    "never synced", "stale links (7d)", "out of stock",
    "avg sync age (days)", "last synced at"
]
```

Add a **"Affiliate & Commission"** section:

```python
"affiliate & commission": [
    "feed enabled", "network slug", "program count",
    "avg commission rate", "max commission rate",
    "links with commission", "links without commission",
    "links with tracking code"
]
```

Add a **"Pricing Summary"** section:

```python
"pricing summary": [
    "min price", "avg price", "max price",
    "links with discount", "avg discount %",
    "links with null price", "currency mix"
]
```

---

## 8. Pricing Dashboard — Recommendations

### 8.1 Missing Dashboard Entirely

There is **no dedicated pricing dashboard**. Pricing data is scattered across:
- Item list (min/max price column)
- Item health stats (stale_sync_items — proxy for stale pricing)
- Store coverage stats (commission avg)

### 8.2 Recommended Pricing KPI Cards (new `pricing_stats` endpoint)

| Card | Value | Alert Threshold |
|---|---|---|
| Links with Current Price | `COUNT(price IS NOT NULL)` | < 90% = warning |
| Links with Stale Price (7d+) | `COUNT(last_synced_at < now()-7d)` | > 10% = warning |
| Links with Discount | `COUNT(old_price IS NOT NULL AND old_price > price)` | — |
| Avg Discount % | `AVG((old_price - price)/old_price * 100)` | — |
| Zero-Price Links | `COUNT(price IS NULL OR price = 0)` | > 0 = alert |
| All-OOS Products | Items where ALL store links = OutOfStock | > 0 = alert |

### 8.3 Recommended Pricing Panels

| Panel | Chart Type | Data Source |
|---|---|---|
| Price Distribution by Store | Horizontal bar | `AVG(price)` GROUP BY store |
| Discount Depth Ranking | Sorted bars | `(old_price-price)/old_price` |
| Price Staleness Heatmap | Store × age grid | `last_synced_at` age buckets |
| Currency Mix | Donut | `COUNT(*)` GROUP BY currency |
| Price Null Rate by Store | Bar | `SUM(price IS NULL)/COUNT(*)` |

---

## 9. Affiliate Dashboard — Recommendations

### 9.1 Missing Dashboard

No dedicated affiliate monitoring view exists. Commission and program data lives only in `coverage_stats`.

### 9.2 Recommended Affiliate KPI Cards (extend `coverage_stats`)

| Card | Query |
|---|---|
| Links WITH Commission | `COUNT(commission_rate IS NOT NULL)` |
| Links WITHOUT Commission | `COUNT(commission_rate IS NULL)` |
| Avg Commission Rate | `AVG(commission_rate)` (global) |
| Top Commission Store | `MAX(AVG(commission_rate))` by store |
| Links with Tracking Code | `COUNT(tracking_code IS NOT NULL)` |
| Stale Deeplinks (30d+) | `COUNT(deeplink_generated_at < now()-30d)` |

### 9.3 Recommended Affiliate Panels

| Panel | Data Source | Insight |
|---|---|---|
| Commission Rate by Store | `AVG(commission_rate)` per store | Which stores yield best margin? |
| Program Distribution | `COUNT(*)` GROUP BY `program_name` | Program fragmentation visibility |
| Commission Coverage | `NULL vs non-NULL commission_rate` | Monetization gap |
| Deeplink Age Distribution | Bucket `deeplink_generated_at` | Expiry risk |
| Tracking Code Coverage | `NULL vs non-NULL tracking_code` per store | Attribution gap |

---

## 10. Synchronization Dashboard — Current State & Improvements

### 10.1 What Exists

The `health_stats` endpoint and `stores.html` dashboard cover:
- Active links
- Synced today / this week
- Never synced
- Out of stock by store

### 10.2 3-Tier Sync Timeline (Completely Collapsed)

The model has **three distinct timestamps**:

| Timestamp | Meaning | Used? |
|---|---|---|
| `deeplink_generated_at` | When the deeplink/affiliate URL was created | ❌ Never |
| `last_synced_at` | When pricing/availability was last refreshed | ✅ Partial |
| `last_checked_at` | When availability was last verified | ✅ In inspect only |

Conflating these hides different failure modes:
- Deeplink expired but price was checked → `last_checked_at` OK, revenue lost
- Price synced but availability not checked → false InStock signals
- Neither synced → full staleness

### 10.3 Recommended Sync KPI Additions

| Card | Query |
|---|---|
| Synced in 24h | `last_synced_at >= now()-1d` |
| Synced in 7d | `last_synced_at >= now()-7d` |
| **Checked in 24h** | `last_checked_at >= now()-1d` ← **new** |
| **Deeplink refreshed in 30d** | `deeplink_generated_at >= now()-30d` ← **new** |
| **Never checked** | `last_checked_at IS NULL` ← **new** |
| **Never had deeplink** | `deeplink_generated_at IS NULL` ← **new** |

### 10.4 Recommended Sync Panels

| Panel | Insight |
|---|---|
| Sync Health by Store (bar chart) | `AVG(EXTRACT(day FROM now()-last_synced_at))` per store |
| Availability Drift | Items that changed availability since last check |
| Sync Cadence Timeline | Rolling 30d count of syncs per day (volume sparkline) |
| Top Stale Stores | Stores with highest avg sync age |
| Deeplink Freshness | Bucket deeplink age: <7d / 7–30d / >30d / never |

---

## 11. Existing Data Utilization Score

Based on the full inventory of available fields vs. what is surfaced in admin:

| Domain | Fields Available | Fields Utilized | Utilization % |
|---|---|---|---|
| **Store** | 13 fields | 6 (name, website, affiliate_network, country, currency, api_enabled) | **46%** |
| **ItemStoreLink** | 17 fields | 6 (affiliate_url, price, old_price, availability, is_active, last_synced_at) | **35%** |
| **ItemVariant** | 8 fields | 4 (price, old_price, currency, is_default) | **50%** |
| **Item Interactions** | click_count, view_count + ItemClick join | Both used | **100%** |
| **Sync Timeline** | 3 timestamps | 1 (`last_synced_at`) | **33%** |
| **Commission** | `commission_rate`, `program_name`, `tracking_code` | Avg commission only | **20%** |
| **Network Metadata** | `network_metadata` JSON, `external_item_id`, `merchant_category` | None at dashboard level | **0%** |

> **Overall Commerce Data Utilization: ~40%**  
> The most valuable untapped layer is the affiliate operations layer (commission, deeplink, tracking, program metadata).

---

## 12. Phased Implementation Roadmap

### Phase 1 — Fix Existing Surfaces (1–2 weeks)
*Fix incorrect metrics, surface already-queried data, zero new endpoints*

| Item | File | Change |
|---|---|---|
| Remove `conversions: 0` | `providers.py` | Suppress or replace with `commission_revenue_estimate` |
| Fix CTR denominator | `providers.py` `_fetch_stores_page` | Use `ItemClick.item_store_link_id` join directly to store (not via item views) |
| Add `sync_age_days` to store list | `providers.py` | Add `MAX(last_synced_at)` to existing store aggregate query |
| Add `oos_rate` to store list | `providers.py` | Add `SUM(availability='OutOfStock')/COUNT(*)` per store |
| Add `avg_commission` to store list | `providers.py` | Add `AVG(commission_rate)` to existing store aggregate |
| Expand store inspect sections | `providers.py` `build_store_inspect_data` | Add link health, affiliate & commission, pricing summary |
| Add `feed_enabled` to inspect | `providers.py` | One-line addition to data dict |
| Surface `program_name` in item inspect | `items.py` `build_item_inspect_data` | Already in `store_links_data` — add to inspect table |
| Add store list filters | `stores.html` / `stores.js` | Affiliate network, country, sync staleness dropdowns |

---

### Phase 2 — Sync & Availability Intelligence (2–3 weeks)
*New endpoint + new dashboard panels, extend existing health_stats*

| Item | Endpoint / Template | Change |
|---|---|---|
| Extend `health_stats` | `providers.py` | Add `last_checked_at` KPIs, deeplink KPIs, sync-age histogram |
| Add `sync_age_by_store` panel | `stores.html` | Bar chart: avg sync age per store |
| Add 3-tier sync timeline KPI cards | `stores.html` | 3 new stat cards for deeplink / checked / synced |
| Availability breakdown donut | `stores.html` | InStock / OutOfStock / PreOrder / Unknown ratio |
| Top stale stores panel | `stores.html` | Table: stores sorted by avg `last_synced_at` age |
| Rolling sync volume sparkline | `stores.html` | 30d sparkline of daily sync volume from `last_synced_at` |

---

### Phase 3 — Affiliate & Commission Intelligence (3–4 weeks)
*New `affiliate_stats` endpoint + new dashboard section or tab*

| Item | Endpoint / Template | Change |
|---|---|---|
| New `affiliate_stats` endpoint | `providers.py` | Commission coverage, program distribution, tracking coverage, deeplink age |
| Commission KPI cards | `stores.html` | Links with/without commission, avg rate, top program |
| Program distribution panel | `stores.html` | `program_name` breakdown bar chart |
| Commission rate ranking | `stores.html` | Store ranked by avg commission — monetization priority view |
| Tracking code coverage panel | `stores.html` | Attribution gap by store |
| Deeplink freshness panel | `stores.html` | Bucket: fresh / aging / stale / never |
| Commission gap alert | `stores.html` | Alert card when >X% links have no commission rate |

---

### Phase 4 — Pricing Intelligence (4–6 weeks)
*New `pricing_stats` endpoint + pricing tab or dedicated panel set*

| Item | Endpoint / Template | Change |
|---|---|---|
| New `pricing_stats` endpoint | `providers.py` | Price null rate, discount depth, stale price count, currency mix |
| Pricing KPI cards | `stores.html` | Null price rate, stale price count, avg discount |
| Price distribution by store panel | `stores.html` | Avg price per store bar chart |
| Discount depth ranking panel | `stores.html` | Top discounted products/stores |
| Price staleness heatmap | `stores.html` | Store × time-bucket grid |
| Currency mix donut | `stores.html` | Distribution of link currencies |
| All-OOS product alert | `stores.html` | Count of items where every store link is OOS |
| Price null alert per store | `stores.html` | Stores where price null rate > 20% flagged |
| Price spread per product | Item inspect | Min vs max price across all stores for a product |

---

## Summary: Highest-Priority Single Actions

| Priority | Action | Impact |
|---|---|---|
| 🔴 **P1** | Fix CTR denominator (views overcount) | Data integrity — current CTR is meaningless |
| 🔴 **P1** | Remove `conversions: 0` | Misleading hardcoded zero in every store row |
| 🟠 **P2** | Add `sync_age_days` to store list | Core operational visibility |
| 🟠 **P2** | Add `oos_rate` to store list | Inventory health per row |
| 🟠 **P2** | Expand store inspect with link health + commission | Doubles inspect utility with 2–3 queries |
| 🟡 **P3** | Add `last_checked_at` and deeplink KPIs to health_stats | Exposes hidden sync timeline |
| 🟡 **P3** | Build program distribution panel | First affiliate program-level visibility |
| 🟢 **P4** | New `pricing_stats` endpoint + dashboard section | Pricing intelligence layer |
