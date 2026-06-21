# Taxonomy System — Architecture Analysis & Implementation Plan
### Nexora Admin · Taxonomy Domain · Senior Architect Review

---

## Executive Summary

The Nexora taxonomy system contains a richer, more interconnected data model than its current admin UI reveals. Eight taxonomy entities exist in the models layer, yet the administration surface manages only four. Significant relationships — three scalar facets on Content, one commented-out relationship table, and a cross-domain bridge via `content_items` — are either invisible to admins or entirely absent from the admin layer. The existing inspect endpoints already perform sophisticated multi-table joins; the gap is not in what the data *can* tell you, but in what the admin UI *chooses to show*.

This document maps every gap and proposes a phased roadmap to extract full operational value from existing data without redesigning the taxonomy architecture.

---

## 1. Taxonomy Data Inventory

### 1.1 Entities Currently in `models.py`

| Entity | Table | Admin-Managed? | Admin-Inspectable? | Key Metadata |
|---|---|---|---|---|
| `Category` | `categories` | ✅ Yes | ✅ Yes | `name`, `slug`, `parent_id`, `is_active`, `is_leaf`, `sort_order`, `normalized_name` |
| `Brand` | `brands` | ✅ Yes | ✅ Yes | `name`, `slug`, `industry`, `is_featured`, `is_active`, `sort_order`, `normalized_name` |
| `Topic` | `topics` | ✅ Yes | ✅ Yes | `name`, `slug`, `is_featured`, `is_active`, `sort_order`, `normalized_name` |
| `Section` | `sections` | ✅ Yes | ✅ Yes | `name`, `slug`, `description`, `allowed_filters` (JSON), `is_active`, `sort_order` |
| `Source` | `sources` | ❌ No CRUD | ✅ Yes (inspect only) | `name`, `slug`, `domain`, `logo_url`, `is_active`, `authority_score` |
| `GenderFacet` | `gender_facets` | ❌ **Not managed** | ❌ **Not inspectable** | `name`, `slug` |
| `IntentFacet` | `intent_facets` | ❌ **Not managed** | ❌ **Not inspectable** | `name`, `slug` |
| `PriceTierFacet` | `price_tier_facets` | ❌ **Not managed** | ❌ **Not inspectable** | `name`, `slug` |
| `AttributeFacet` | `attributes` | ❌ **Not managed** | ❌ **Not inspectable** | `name`, `slug`, `category_id` (FK to categories) |

### 1.2 Fields Serialized to Admin vs. Fields Available in Model

#### Category — Serialized in `_serialize_taxonomy()` / `_serialize_category()`
- **Serialized:** `id`, `name`, `slug`, `is_active`, `is_leaf`, `sort_order`, `parent_id`
- **Available but not surfaced in list view:** `normalized_name`, parent relationship (name of parent), children count, content count, item count

#### Brand — Serialized in `_serialize_taxonomy()` / `_serialize_brand()`
- **Serialized:** `id`, `name`, `slug`, `industry`, `is_active`, `is_featured`, `sort_order`
- **Available but not surfaced in list view:** `normalized_name`, content count, item count, cross-domain presence indicator

#### Topic — Serialized in `_serialize_taxonomy()` / `_serialize_topic()`
- **Serialized:** `id`, `name`, `slug`, `is_active`, `is_featured`, `sort_order`
- **Available but not surfaced in list view:** `normalized_name`, content count

#### Section — Serialized in `_serialize_taxonomy()` / `_serialize_section()`
- **Serialized:** `id`, `name`, `slug`, `description`, `is_active`, `sort_order`
- **Available but not surfaced in list view:** `allowed_filters` (JSON field, entirely invisible in list), content count

### 1.3 Critical Observation: Two Serializer Systems
Two parallel serializer functions exist per entity: `_serialize_taxonomy()` (for HTML row rendering) and `_serialize_brand()` / `_serialize_category()` etc. (for JSON API). The HTML row serializer strips out several fields (`slug`, `industry`, `is_featured`) present in the JSON serializer. This creates a **data visibility split** where the same entity shows different information depending on access path.

---

## 2. Taxonomy Relationship Mapping

### 2.1 Complete Relationship Graph

```
┌─────────────────────────────────────────────────────────┐
│                   TAXONOMY LAYER                         │
│                                                          │
│  Category ──── parent_id ────▶ Category (self-ref)      │
│  AttributeFacet ── category_id ──▶ Category             │
└─────────────────────────────────────────────────────────┘
           │                   │         │          │
           │                   │         │          │
     content_brands      content_topics  content_attributes
           │                   │         │
           ▼                   ▼         ▼
┌──────────────────────────────────────────────────────────┐
│                     CONTENT                              │
│  Content.category_id ──▶ Category                        │
│  Content.section_id  ──▶ Section                         │
│  Content.gender_id   ──▶ GenderFacet      [scalar FK]   │
│  Content.intent_id   ──▶ IntentFacet      [scalar FK]   │
│  Content.price_tier_id ▶ PriceTierFacet  [scalar FK]   │
│  Content.source_id   ──▶ Source           [scalar FK]   │
└──────────────────────────────────────────────────────────┘
           │ content_items (bridge table)
           ▼
┌──────────────────────────────────────────────────────────┐
│                       ITEM                               │
│  Item.brand_id    ──▶ Brand                             │
│  Item.category_id ──▶ Category                          │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Direct Relationships (Active)

| From | To | Via | Type |
|---|---|---|---|
| `Brand` | `Content` | `content_brands` | M2M association table |
| `Brand` | `Item` | `Item.brand_id` | 1-to-many FK |
| `Category` | `Content` | `Content.category_id` | 1-to-many FK |
| `Category` | `Item` | `Item.category_id` | 1-to-many FK |
| `Topic` | `Content` | `content_topics` | M2M association table |
| `Section` | `Content` | `Content.section_id` | 1-to-many FK |
| `AttributeFacet` | `Content` | `content_attributes` | M2M association table |
| `GenderFacet` | `Content` | `Content.gender_id` | 1-to-many FK |
| `IntentFacet` | `Content` | `Content.intent_id` | 1-to-many FK |
| `PriceTierFacet` | `Content` | `Content.price_tier_id` | 1-to-many FK |
| `Source` | `Content` | `Content.source_id` | 1-to-many FK |
| `AttributeFacet` | `Category` | `AttributeFacet.category_id` | Belongs-to FK |
| `Category` | `Category` | `Category.parent_id` | Self-referential |

### 2.3 Indirect Relationships (Derivable, Not Surfaced)

| Indirect Relationship | Derivable Via | Administrative Value |
|---|---|---|
| Brand ↔ Category | Items sharing both | Which categories a brand competes in |
| Brand ↔ Topic | `content_brands` + `content_topics` (same content_id) | Topic affinity per brand |
| Brand ↔ Section | `content_brands` + `Content.section_id` | Section presence per brand |
| Topic ↔ Category | `content_topics` + `Content.category_id` | Category coverage per topic |
| Topic ↔ Brand | `content_topics` + `content_brands` (same content_id) | Co-tagged brand/topic pairs |
| Section ↔ Category | `Content.section_id` + `Content.category_id` | Category distribution per section |
| Category ↔ Content ↔ Item | `content_items` + Item.category_id | Items in category linked to content in same category |
| Brand ↔ Content ↔ Item | `content_items` bridge | Cross-domain brand coherence check |
| AttributeFacet ↔ Category | `AttributeFacet.category_id` | Attribute scope per category |

### 2.4 Commented-Out / Deactivated Relationships

The `relationships.py` file contains a commented-out `item_topics` table:

```python
# item_topics = db.Table(
#     "item_topics",
#     db.Column("item_id", ...),
#     db.Column("topic_id", ...),
# )
```

This means **Topics are not connected to Items** — only to Content. This is an architectural boundary worth surfacing: Topics classify editorial content but not products. This distinction is invisible in the current admin UI.

---

## 3. Taxonomy Coverage Analysis

### 3.1 Coverage Gaps by Entity

#### Category Coverage
- Content: **Required** (`category_id` is `nullable=False`) — no gap possible by schema
- Items: **Required** (`item.category_id` appears required) — need to verify nullability
- **Gap:** Leaf categories with **zero content** and **zero items** exist as structural orphans

#### Brand Coverage
- Content: **Optional** (M2M, content may have 0 brands) — gap exists
- Items: **Optional** (`Item.brand_id` nullable by default) — gap exists
- **Gap:** Items without a brand, content without a brand

#### Topic Coverage
- Content: **Optional** (M2M, content may have 0 topics) — gap exists
- Items: **Not connected** (no `item_topics` table) — by design, not a gap
- **Gap:** Content without any topics represents the largest classification gap in the system

#### Section Coverage
- Content: **Required** (`section_id` is `nullable=False`) — no gap by schema
- Items: **Not connected** — by design

#### Facet Coverage (GenderFacet, IntentFacet, PriceTierFacet)
- All three are **optional FKs** on Content (`nullable=True` by default for FK columns)
- **No admin visibility exists for these facets at all**
- Content records may be entirely unclassified across all three facets
- **This is the largest invisible coverage gap in the system**

#### AttributeFacet Coverage
- Content: **Optional** (M2M) — content may have 0 attributes
- Items: **Not connected** — attributes are content-only
- `AttributeFacet.category_id` is **nullable** — some attributes are uncategorized

#### Source Coverage
- Content: **Optional** (`source_id` nullable) — content may have no source
- **Gap:** Content without a source (ingestion origin unknown)

### 3.2 Unused Taxonomy Risk Areas

| Risk | Detection Query |
|---|---|
| Topic with 0 content | `content_topics` count = 0 |
| Brand with 0 content AND 0 items | `content_brands` count = 0 AND `Item.brand_id` count = 0 |
| Category (leaf) with 0 content AND 0 items | FK count = 0 on both |
| AttributeFacet with 0 content | `content_attributes` count = 0 |
| AttributeFacet with no category assigned | `category_id IS NULL` |
| Section with 0 content | FK count = 0 |
| Inactive Brand with active items/content | Status mismatch |
| Inactive Category with active content/items | Status mismatch |

---

## 4. Taxonomy Health Visibility

### 4.1 Current Health Visibility: None

The current admin system has **zero health visibility**. There is no:
- Orphan detection
- Unused entity surfacing
- Coverage rate display
- Status mismatch alerting
- Duplicate candidate detection

### 4.2 Recommended Health Signals — By Entity

#### For All Entities (Universal Health Signals)
- **Orphan status:** Used in zero linked records
- **Status-usage mismatch:** Is inactive but still has active linked records
- **Last-used indicator:** Most recent content/item published that uses this taxonomy

#### Category-Specific
- **Empty leaf:** `is_leaf=True` but 0 items and 0 content
- **Parent with no children:** `is_leaf=False` but `children` count = 0
- **Hierarchy depth:** Currently only 2 levels shown (parent/leaf), but depth is not displayed
- **Category coherence:** Leaf category has items in it but no content, or vice versa

#### Brand-Specific
- **Content-only brand:** Has content associations but no items (editorial brand, no product catalog)
- **Item-only brand:** Has items but no content (product catalog gap — no editorial coverage)
- **Cross-domain balance:** Ratio of content count to item count
- **Inactive-but-linked:** `is_active=False` but still referenced by active content or items

#### Topic-Specific
- **Unused topic:** `content_topics` count = 0
- **Single-use topic:** Used by exactly 1 content record (may be a duplicate or low-value topic)
- **Featured but inactive:** `is_featured=True` but `is_active=False` (configuration conflict)
- **Category spread:** Topics that only appear in 1 category vs. those appearing across many categories

#### Section-Specific
- **Empty section:** 0 content records
- **`allowed_filters` not configured:** JSON field is NULL (section has no filter rules defined)
- **Single-category section:** All content in section belongs to 1 category (possibly misconfigured)

#### AttributeFacet-Specific
- **Uncategorized attribute:** `category_id IS NULL`
- **Unused attribute:** `content_attributes` count = 0
- **Category mismatch:** Attribute belongs to Category A but is used on content classified under Category B

---

## 5. Admin List View Improvements

### 5.1 Current List View State — What Each Row Shows

The `_serialize_taxonomy()` function is the data source for all list rows. Currently:
- **Category rows:** `name`, `status` (active/inactive), `type` (Leaf/Parent)
- **Brand rows:** `name`, `status`, `featured`
- **Topic rows:** `name`, `status`, `featured`
- **Section rows:** `name`, `status`, `description`

No usage counts, no relationship indicators, no coverage metrics.

### 5.2 Recommended Additions Per Entity

#### Category List View
| Column to Add | Data Source | Value |
|---|---|---|
| Content Count | `COUNT(Content) WHERE category_id = id` | Classifies usage |
| Item Count | `COUNT(Item) WHERE category_id = id` | Classifies usage |
| Parent Name | `Category.parent.name` (already loaded in inspect) | Hierarchy context |
| Children Count | `COUNT(Category) WHERE parent_id = id` | Structure visibility |
| Health Badge | Derived: 0 content + 0 items → "Empty" warning | Orphan detection |

#### Brand List View
| Column to Add | Data Source | Value |
|---|---|---|
| Content Count | `COUNT(content_brands) WHERE brand_id = id` | Cross-domain presence |
| Item Count | `COUNT(Item) WHERE brand_id = id` | Cross-domain presence |
| Domain Presence | Derived: content-only / item-only / both | Brand gap detection |
| Industry | Already in `_serialize_brand()`, not shown in row | Filter context |

#### Topic List View
| Column to Add | Data Source | Value |
|---|---|---|
| Content Count | `COUNT(content_topics) WHERE topic_id = id` | Usage indicator |
| Category Spread | `COUNT(DISTINCT Content.category_id)` via topic join | Topic breadth |
| Health Badge | 0 content → "Unused" | Orphan detection |

#### Section List View
| Column to Add | Data Source | Value |
|---|---|---|
| Content Count | `COUNT(Content) WHERE section_id = id` | Usage indicator |
| Filter Config | `allowed_filters IS NULL` → "Not Configured" badge | Configuration gap |
| Category Count | `COUNT(DISTINCT Content.category_id)` via section | Breadth visibility |

### 5.3 List View Filter Recommendations

All four list views currently support only text search. Recommended filter additions:

| Entity | Recommended Filters |
|---|---|
| Category | Status (active/inactive), Type (Leaf/Parent), Empty (no content/items) |
| Brand | Status, Industry, Featured, Domain (content-only / item-only / both) |
| Topic | Status, Featured, Empty (unused), Category filter |
| Section | Status, Filter Config (configured / not configured) |

---

## 6. Inspect / Detail View Improvements

### 6.1 Current Inspect State — What Is Already Shown

The `_get_taxonomy_related_metadata()` function already computes:

**Category inspect:** content count, item count, child categories count, avg variants per item, image coverage %, items without content count, top 5 content by views

**Brand inspect:** content count, item count, average price, image coverage %, top 5 clicked items (custom rendered table), top 5 content by views

**Topic inspect:** content count, related categories count, related brands count, top 5 content by views

**Section inspect:** content count, category count, related brands count, top 5 content by views

This is already a strong foundation. The gaps below are additions that would complete the picture.

### 6.2 Recommended Additions Per Entity

#### Category Inspect — Missing
- **Parent chain:** Show the full ancestor path (e.g., Electronics > Laptops), not just immediate parent name
- **Sibling count:** How many categories share the same parent
- **Content type breakdown:** Of N content items in this category, how many are articles / videos / posts
- **Engagement summary:** Total view_count, like_count, share_count across all content in category
- **Facet coverage:** % of content in this category that has gender / intent / price_tier set
- **Featured brand list:** Top brands appearing in content under this category

#### Brand Inspect — Missing
- **Content type breakdown:** Articles vs. videos vs. posts featuring this brand
- **Category distribution:** Which categories the brand's items appear in
- **Topic affinity:** Topics most co-tagged with this brand's content
- **Section presence:** Which sections feature this brand's content
- **Engagement totals:** Total views / likes / shares across all branded content
- **Item vs. Content coverage ratio:** "Brand has X items but only Y content pieces" signal

#### Topic Inspect — Missing
- **Featured brand list:** Top brands co-appearing in this topic's content
- **Section distribution:** Which sections this topic's content appears in
- **Content type breakdown:** Articles vs. videos vs. posts
- **Engagement totals:** Total views / likes / shares for this topic
- **Trend signal:** Content count in last 30 days vs. prior 30 days (using `published_at`)

#### Section Inspect — Missing
- **`allowed_filters` rendered:** The JSON field is shown as raw JSON string; it should be rendered as a readable list
- **Content type breakdown:** Articles vs. videos vs. posts in this section
- **Engagement totals:** Total views / likes across section
- **Topic distribution:** Top N topics appearing in this section
- **Brand distribution:** Top N brands appearing in section content
- **Facet coverage:** % of content with gender / intent / price_tier assigned

---

## 7. Taxonomy Analytics Opportunities

All analytics below are derivable from **existing data with no new columns**.

### 7.1 Brand Analytics
| Metric | Description | Derivable From |
|---|---|---|
| Brand content distribution | Content count per brand, sorted | `content_brands` |
| Brand item distribution | Item count per brand, sorted | `Item.brand_id` |
| Cross-domain brand penetration | Brands present in both content and items | Join both |
| Brand industry distribution | Count brands grouped by `industry` | `Brand.industry` |
| Orphan brand rate | Brands with 0 content and 0 items | Union count |
| Brand engagement rank | Total content views per brand | `content_brands` + `Content.view_count` |
| Featured brand utilization | Featured brands with 0 content | `Brand.is_featured` filter |

### 7.2 Category Analytics
| Metric | Description | Derivable From |
|---|---|---|
| Category item distribution | Item count per category | `Item.category_id` |
| Category content distribution | Content count per category | `Content.category_id` |
| Category cross-domain balance | Categories with both content and items vs. only one | JOIN both |
| Empty leaf categories | Leaf categories with 0 items and 0 content | Dual zero count |
| Category depth distribution | Count categories at each parent/leaf level | `is_leaf`, `parent_id` |
| Engagement by category | Sum of view_count per category | `Content.category_id` + views |

### 7.3 Topic Analytics
| Metric | Description | Derivable From |
|---|---|---|
| Topic usage distribution | Content count per topic | `content_topics` |
| Topic category spread | Distinct category count per topic | `content_topics` + `Content.category_id` |
| Topic brand co-occurrence | Brands most co-tagged with each topic | `content_topics` + `content_brands` |
| Unused topic rate | Topics with 0 content | `content_topics` count = 0 |
| Featured topic utilization | Featured topics with low usage | `Topic.is_featured` + count |

### 7.4 Section Analytics
| Metric | Description | Derivable From |
|---|---|---|
| Section content distribution | Content count per section | `Content.section_id` |
| Section brand distribution | Brands per section | `content_brands` + section join |
| Empty section detection | Sections with 0 content | Count = 0 |
| Section filter configuration rate | Sections with `allowed_filters` set | IS NOT NULL check |

### 7.5 Facet Coverage Analytics (Highest Current Gap)
| Metric | Description | Derivable From |
|---|---|---|
| Gender facet coverage | % content with `gender_id` set | NULL check |
| Intent facet coverage | % content with `intent_id` set | NULL check |
| Price tier facet coverage | % content with `price_tier_id` set | NULL check |
| Attribute coverage | % content with 1+ attribute | `content_attributes` count |
| Facet distribution by category | Which categories have most/least facet coverage | FK joins |
| Triple-classified content | Content with all 3 facets set | AND NOT NULL |
| Unclassified content | Content with 0 facets set | ALL NULL |

### 7.6 Cross-Domain Analytics
| Metric | Description | Derivable From |
|---|---|---|
| Content-Item linkage rate | % items that appear in `content_items` | `content_items` count |
| Category coherence | Items in Category A linked to content also in Category A | Cross-join check |
| Brand coherence | Items with Brand A linked to content also tagged with Brand A | Cross-join check |
| Topic-to-product funnel | Content topics driving item link clicks | `content_items` + `content_topics` + `Item.click_count` |

---

## 8. Visualization Opportunities

### 8.1 Taxonomy Overview Dashboard (New Page or Section)

Recommended location: A new **"Taxonomy Health"** tab or dashboard widget accessible from the Taxonomy Management page header.

#### KPI Cards (Top of Page)
| Card | Value | Threshold Signal |
|---|---|---|
| Total Active Brands | Count of `Brand WHERE is_active=True` | — |
| Total Active Categories | Count of `Category WHERE is_active=True` | — |
| Total Active Topics | Count of `Topic WHERE is_active=True` | — |
| Orphaned Taxonomy Entities | Sum of all unused brands + topics + attributes | Red if > 0 |
| Facet Coverage Rate | % content with all 3 facets set | Red if < 50% |
| Cross-Domain Brands | Brands with both content and items | — |

#### Distribution Charts
| Chart | Type | Content |
|---|---|---|
| Brand by Domain Presence | Donut | Content-only / Item-only / Both / None |
| Category Usage | Bar chart | Top N categories by content + item count |
| Topic Usage | Horizontal bar | Top N topics by content count |
| Facet Coverage Breakdown | Stacked bar | Gender / Intent / PriceTier coverage % per category |
| Industry Distribution | Donut | Brand count grouped by `industry` |

#### Health Summary Table
A compact table listing taxonomy entities with health flags:
- Name | Type | Status | Usage Count | Health Signal (OK / Unused / Orphan / Mismatch)

### 8.2 Per-Entity List View Enhancements

#### Usage Indicator Badge
Add a colored count badge next to each row:
- `0` → Red (unused / orphan risk)
- `1–5` → Yellow (low usage)
- `5+` → Green (healthy usage)

This badge should be computed during the rows query via a subquery or joined aggregate.

#### Coverage Progress Bar (Category and Section rows)
A mini progress bar showing facet coverage % for the content in that category/section.

### 8.3 Inspect View Visualizations

#### Category Inspect
- Engagement summary row (views / likes / shares / saves)
- Content type mini-donut (articles / videos / posts)
- Top brands in category — pill tags

#### Brand Inspect
- Engagement bar: content views total
- Domain presence indicator: "Content: 12 pieces | Items: 34 products"
- Category distribution: simple list of categories brand's items appear in

#### Topic Inspect
- Trend mini chart: content count per month for last 6 months (using `Content.published_at`)
- Brand co-occurrence: top 5 co-tagged brands (pill tags)

#### Section Inspect
- Facet coverage summary: gender X% / intent X% / price_tier X% shown as progress bars
- `allowed_filters` rendered as readable tags, not raw JSON

---

## 9. Existing Data Utilization Score

### 9.1 Underutilized Fields

| Field | Location | Current Use | Potential Use |
|---|---|---|---|
| `Brand.industry` | `Brand` model | Available in JSON API, not shown in list rows | Industry filter, brand grouping, industry distribution chart |
| `Brand.normalized_name` | `Brand` model | Not surfaced anywhere in admin | Duplicate detection (brands with same normalized name) |
| `Topic.normalized_name` | `Topic` model | Not surfaced anywhere in admin | Duplicate detection |
| `Category.normalized_name` | `Category` model | Not surfaced anywhere in admin | Duplicate detection |
| `Section.allowed_filters` | `Section` model | Shown as raw JSON in inspect | Should be rendered as tags; sections without it need alert |
| `Content.ingestion_origin` | `Content` model | Not used in any taxonomy inspect | Source/origin analysis per taxonomy entity |
| `Content.object_type` | `Content` model | Not broken down in any inspect view | Content type breakdown per taxonomy entity |
| `Content.view_count`, `like_count`, `share_count`, `save_count` | `Content` model | Only used for sorting (top 5 content), not aggregated | Engagement totals per taxonomy entity |
| `Item.click_count` | `Item` model | Used in brand inspect top clicked items | Should be used in category inspect too |

### 9.2 Underutilized Relationships

| Relationship | Status | Gap |
|---|---|---|
| `GenderFacet` ↔ `Content` | Exists in model, 0 admin visibility | Entire facet dimension invisible to admins |
| `IntentFacet` ↔ `Content` | Exists in model, 0 admin visibility | Entire facet dimension invisible to admins |
| `PriceTierFacet` ↔ `Content` | Exists in model, 0 admin visibility | Entire facet dimension invisible to admins |
| `AttributeFacet` ↔ `Category` | FK exists, never queried in admin | Attribute-to-category mapping invisible |
| `AttributeFacet` ↔ `Content` | M2M exists, never inspected | No coverage metric exists |
| `content_items` bridge | Used only in category inspect | Brand inspect does not use it; no cross-domain analysis |
| `Source` → `Content` | Inspect exists but Source has no list/CRUD | Source management is a dead-end; can't create or list sources |
| `Category` self-referential | Parent shown in inspect, children count shown | Full hierarchy tree never rendered |

### 9.3 Hidden Operational Value

1. **Brand coherence check** (via `content_items`): When a content piece is tagged with Brand A via `content_brands` and also links to an item via `content_items`, does that item also have Brand A set? If not, it's a data consistency signal. This is computable but never surfaced.

2. **Category coherence check**: Does content in Category A link to items that are also in Category A? Cross-category linkages could indicate miscategorization or valid cross-category editorial coverage.

3. **Topic trend detection**: Content topics can be tracked over time by grouping `content_topics` joins on `Content.published_at`. Rising and falling topic usage is available but never shown.

4. **Facet-based editorial gaps**: Which categories have the highest rate of content with no intent or gender facet? These are editorial classification gaps the admin cannot currently see.

5. **Source authority × taxonomy quality**: `Source.authority_score` exists; combining it with taxonomy assignments could surface "which categories have the highest-authority source coverage" — entirely derivable from existing data.

### 9.4 Utilization Score Summary

| Dimension | Score | Observation |
|---|---|---|
| **Entity Coverage** | 4/8 managed | Three facets + AttributeFacet have 0 admin management |
| **Field Utilization** | ~45% | `normalized_name`, `allowed_filters`, `industry`, `object_type`, engagement aggregates all underused |
| **Relationship Utilization** | ~40% | Facet FKs, `content_items` cross-domain, `AttributeFacet.category_id` all underused |
| **Analytics Coverage** | ~15% | Only top-5 content lists; no aggregates, distributions, or health signals |
| **Health Visibility** | 0% | Zero orphan detection, zero coverage metrics in list views |

---

## 10. Implementation Roadmap

### Phase 1 — Quick Wins & Visibility (Effort: Low, Value: High)

These changes require minimal backend work and deliver immediate operational value.

#### 1.1 Add Usage Counts to List View Serializers
**Target:** `_serialize_taxonomy()` in `taxonomy.py`

For each entity, add a subquery count to the serializer using `func.count()`. This requires one additional query per entity per page load (or a joined aggregate). Expose:
- `content_count` for all entities
- `item_count` for Brand and Category
- `children_count` for Category
- `usage_count = 0` health flag

**Impact:** Admins immediately see which taxonomy entities are in use vs. orphaned.

#### 1.2 Add "Orphan" Health Badge to List Rows
**Target:** `_rows.html` template / `_serialize_taxonomy()` response

Add a `health` key to the serialized row with values: `"ok"` / `"unused"` / `"inactive-linked"`. Render as a badge in the table row. Derivable from counts computed in 1.1.

**Impact:** Orphan detection becomes visible at a glance without opening inspect.

#### 1.3 Surface `industry` and `featured` in Brand List Rows
**Target:** `_serialize_taxonomy()` for brands

`_serialize_brand()` already includes `industry` and `is_featured`. The `_serialize_taxonomy()` (used for HTML rows) does not include `industry` — only `featured`. Add `industry` to the HTML row serializer.

**Impact:** Industry grouping becomes visible in list; no additional queries.

#### 1.4 Surface `allowed_filters` Configuration Status in Section Rows
**Target:** `_serialize_taxonomy()` for sections

Add a `has_filter_config` boolean derived from `Section.allowed_filters is not None`. Show as a badge in section rows: "Configured" / "Not Configured".

**Impact:** Admins immediately see which sections have no filter rules defined.

#### 1.5 Add Content Type Breakdown to Inspect Endpoints
**Target:** `_get_taxonomy_related_metadata()` in `taxonomy.py`

Add to all four entity types:
```python
# Group content by object_type for this taxonomy entity
type_breakdown = db.session.execute(
    select(Content.object_type, func.count()).group_by(Content.object_type)
    .where(Content.category_id == entity.id)  # adapt per entity type
).all()
```
Returns articles/videos/posts split.

**Impact:** Zero additional schema changes; significant editorial insight in inspect view.

#### 1.6 Add Engagement Totals to Inspect Endpoints
**Target:** `_get_taxonomy_related_metadata()`

For each entity type, add aggregate sums of `view_count`, `like_count`, `share_count` across linked content. This is a single query per entity using `func.sum()`.

**Impact:** Admins can rank categories/brands by engagement, not just content count.

---

### Phase 2 — Taxonomy Management Enhancements (Effort: Medium, Value: High)

#### 2.1 Add Admin Management for `AttributeFacet`
**Target:** New tab in `taxonomy.html` + new routes in `taxonomy.py`

Add a fifth tab "Attributes" to the taxonomy page. Implement:
- `GET /admin/taxonomy/attributes/rows` — paginated list
- `POST /admin/taxonomy/attributes` — create
- `PATCH /admin/taxonomy/attributes/<id>` — update (name, category assignment)
- `DELETE /admin/taxonomy/attributes/<id>` — delete
- `GET /admin/taxonomy/attributes/<id>/inspect` — inspect with content count, category, usage

The `AttributeFacet.category_id` FK means attributes can be scoped to categories — this should be a dropdown in the create form.

**Impact:** The only currently-used facet type (via `content_attributes` M2M) with zero admin management gets full CRUD.

#### 2.2 Add Admin Read-Only Views for `GenderFacet`, `IntentFacet`, `PriceTierFacet`
**Target:** New tabs or sub-section in taxonomy management

These three facets use `get_or_create` patterns — they are auto-created by ingestion pipelines. Admins need read-only visibility:
- List view with content count per facet value
- Inspect with top content, category distribution

Full CRUD is optional (or risky without pipeline coordination). Read-only + inspect is the minimum viable requirement.

**Impact:** Three entire dimensions of content classification become visible for the first time.

#### 2.3 Add Source Management List View
**Target:** New tab or dedicated page

`Source` currently has an inspect endpoint but no list or CRUD. Add:
- `GET /admin/taxonomy/sources/rows` — paginated source list with article count, authority score
- The inspect endpoint already exists and is sophisticated

**Impact:** Source management is currently headless (no way to view all sources, find unused ones, or review authority scores in bulk).

#### 2.4 Add Duplicate Candidate Detection
**Target:** New backend endpoint, surfaced in list views

Use `normalized_name` (already indexed on Brand, Topic, Category) to detect near-duplicate taxonomy entries. Implement:
- `GET /admin/taxonomy/brands/duplicates` — return brands grouped by normalized_name with count > 1
- Same for Topics and Categories

Surface as a warning banner on the respective list tab when duplicates are detected.

**Impact:** Prevents taxonomy pollution without any schema changes.

#### 2.5 Add List View Filters
**Target:** `taxonomy.html` filter toolbar + JS controller search params

Add filter dropdowns to each tab:
- Category: status, leaf/parent, empty/used
- Brand: status, industry, featured, domain presence (content/item/both)
- Topic: status, featured, empty/used
- Section: status, filter config status

Pass as query params to the `/rows` endpoints and apply in backend `stmt.where()` clauses.

**Impact:** Admins can isolate problem areas (e.g., "show me all unused topics") in one click.

---

### Phase 3 — Analytics & Coverage Intelligence (Effort: Medium, Value: Very High)

#### 3.1 Add Facet Coverage Analytics Endpoint
**Target:** New endpoint `GET /admin/taxonomy/analytics/facet-coverage`

Returns:
```json
{
  "gender_coverage": 0.72,
  "intent_coverage": 0.65,
  "price_tier_coverage": 0.58,
  "attribute_coverage": 0.41,
  "all_facets_coverage": 0.33,
  "no_facets_coverage": 0.15
}
```

All values are `COUNT(Content WHERE field IS NOT NULL) / COUNT(Content)`.

**Impact:** First-ever visibility into the 4 facet dimensions. Reveals the true classification completeness of the content corpus.

#### 3.2 Add Cross-Domain Brand Presence Endpoint
**Target:** New endpoint `GET /admin/taxonomy/analytics/brands/presence`

Returns brands grouped by:
- `both` — brand_id in `content_brands` AND in `Item.brand_id`
- `content_only` — brand_id in `content_brands` only
- `item_only` — brand_id in `Item.brand_id` only
- `none` — brand_id in neither

**Impact:** Reveals editorial/catalog gaps for each brand. Brand with items but no content = editorial gap. Brand with content but no items = catalog gap.

#### 3.3 Add Category Coverage Dashboard Data
**Target:** New endpoint `GET /admin/taxonomy/analytics/categories/coverage`

Returns per-category:
- content count, item count, topic count (distinct topics via content in category)
- facet coverage % (gender, intent, price_tier)
- engagement totals (view_count sum)

**Impact:** Category-level coverage matrix surfaces which categories are well-classified vs. neglected.

#### 3.4 Add Taxonomy Health Summary Endpoint
**Target:** New endpoint `GET /admin/taxonomy/analytics/health`

Returns:
```json
{
  "orphaned_brands": 3,
  "orphaned_topics": 12,
  "orphaned_attributes": 5,
  "inactive_linked_brands": 2,
  "empty_leaf_categories": 8,
  "unconfigured_sections": 1,
  "duplicate_brand_candidates": 4,
  "duplicate_topic_candidates": 7
}
```

**Impact:** Single-call health snapshot. Can power a dashboard widget on the Taxonomy Management page header.

---

### Phase 4 — Advanced Taxonomy Insights (Effort: High, Value: High)

#### 4.1 Cross-Domain Coherence Checker
Implement logic to detect:
- Content linked to Item via `content_items` where `Content.brand_id != Item.brand_id` (via association tables)
- Content in Category A linked to Item in Category B (possible miscategorization)

Surface as a "Coherence Issues" section in the taxonomy health dashboard.

#### 4.2 Topic Trend Analytics
Group `content_topics` + `Content.published_at` by month to show topic usage trends over the last 6–12 months. Expose per topic in the inspect view as a sparkline-style data series.

**Impact:** Admins can identify rising topics (invest in coverage) and declining topics (consider deprecation).

#### 4.3 Attribute-to-Category Scoping Enforcement UI
The `AttributeFacet.category_id` FK already allows attributes to be scoped to a category. Build admin UI to:
- Show which attributes are scoped vs. global
- Detect attributes used on content outside their assigned category
- Allow bulk re-scoping

#### 4.4 Taxonomy Merge Tool (Brand/Topic Deduplication)
For duplicate candidates detected in Phase 2:
- Allow admin to select two entries and merge them
- Reassign all `content_brands` / `content_topics` from source to target
- Delete the source after reassignment

This is the highest-effort item but resolves taxonomy pollution that accumulates over time.

#### 4.5 Section `allowed_filters` Configuration UI
Currently `allowed_filters` is a raw JSON column with no UI. Build a structured UI to manage it:
- Display current filter keys as editable tags
- Allow adding/removing filter keys from a predefined list
- Save as JSON

---

## Priority Matrix Summary

| Item | Phase | Effort | Value | Priority |
|---|---|---|---|---|
| Usage counts in list rows (1.1) | 1 | Low | High | **P1** |
| Orphan health badge (1.2) | 1 | Low | High | **P1** |
| Engagement totals in inspect (1.6) | 1 | Low | High | **P1** |
| Content type breakdown in inspect (1.5) | 1 | Low | Medium | **P1** |
| Surface `industry` in brand rows (1.3) | 1 | Very Low | Medium | **P1** |
| Surface filter config in section rows (1.4) | 1 | Very Low | Medium | **P1** |
| AttributeFacet admin management (2.1) | 2 | Medium | High | **P2** |
| Facet read-only views (2.2) | 2 | Medium | High | **P2** |
| Source management list (2.3) | 2 | Low | Medium | **P2** |
| Duplicate candidate detection (2.4) | 2 | Medium | High | **P2** |
| List view filters (2.5) | 2 | Medium | Medium | **P2** |
| Facet coverage analytics (3.1) | 3 | Medium | Very High | **P3** |
| Cross-domain brand presence (3.2) | 3 | Medium | High | **P3** |
| Category coverage dashboard (3.3) | 3 | Medium | High | **P3** |
| Taxonomy health summary endpoint (3.4) | 3 | Medium | High | **P3** |
| Cross-domain coherence checker (4.1) | 4 | High | High | **P4** |
| Topic trend analytics (4.2) | 4 | High | Medium | **P4** |
| Attribute scoping enforcement (4.3) | 4 | High | Medium | **P4** |
| Taxonomy merge tool (4.4) | 4 | Very High | High | **P4** |
| Section `allowed_filters` UI (4.5) | 4 | High | Medium | **P4** |

---

*Analysis based on: `app/admin/taxonomy.py`, `app/domains/taxonomy/models.py`, `app/domains/relationships.py`, `app/domains/content/models/content.py`, `app/web/templates/admin/taxonomy/taxonomy.html`, `app/web/static/js/admin/pages/taxonomy.js`*
