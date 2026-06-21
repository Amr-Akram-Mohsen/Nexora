# Nexora Item Catalog — Architecture Analysis & Implementation Plan

> **Scope**: Item/Product domain — catalog management, admin visibility, variant architecture, pricing, affiliate links, image management, taxonomy, and analytics.
> **Constraint**: No AI/ML suggestions, no external platforms, no new catalog architectures. All recommendations derived strictly from existing data structures.

---

## 1. Item Data Inventory

### Item (`items` table)

| Field | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name` | String(200) | |
| `slug` | String(220) | Unique, indexed |
| `description` | Text | Nullable — currently only shown as Yes/No in inspect |
| `rating` | Float | External/aggregate rating |
| `review_count` | Integer | External review count |
| `item_type` | String(50) | "electronics", "perfumes", "accessories" — controls `structured_details` branching |
| `source_type` | String(50) | How it was ingested |
| `source_id` | FK → `sources` | Which source brought this item in |
| `category_id` | FK → `categories` | **Required** (not nullable) |
| `brand_id` | FK → `brands` | Nullable — items can exist without a brand |
| `created_at` | DateTime | Indexed |
| `like_count` | Integer | Denormalized counter |
| `dislike_count` | Integer | Denormalized counter |
| `share_count` | Integer | Denormalized counter |
| `save_count` | Integer | Denormalized counter |
| `comment_count` | Integer | Denormalized counter |
| `view_count` | Integer | Denormalized counter |
| `click_count` | Integer | Denormalized counter |
| `card_type` | Text | Default "item" |
| `searchable_attributes` | JSON | Content of this field is never surfaced in admin |
| `search_text` | Text | Full-text search support field |
| `search_vector` | TSVECTOR | GIN-indexed for PostgreSQL FTS |

**Computed Properties (Python layer)**

| Property | What it Does |
|---|---|
| `image_url` | First item image URL |
| `default_variant` | First variant with `is_default=True`, fallback first variant |
| `price` | Default variant price |
| `min_price` | Minimum price across all variants |
| `has_variants` | True if more than 1 variant |
| `store_links` | Active store links of the default variant only |
| `full_details` | Spec JSON grouped by category |
| `structured_details` | Item-type-aware spec hierarchy |
| `quick_details` | Flat key-value list for display |
| `variant_groups` | Attribute → sorted values map, priority-ordered |

---

### ItemVariant (`item_variants` table)

| Field | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `item_id` | FK → `items` CASCADE | |
| `title` | String(200) | Optional human title |
| `sku` | String(100) | Unique, nullable |
| `attributes` | JSON | Flexible attribute bag (color, storage, ram, size, volume…) |
| `is_default` | Boolean | |
| `price` | Numeric(10,2) | Indexed — variant-level price |
| `old_price` | Numeric(10,2) | Discount baseline — **never surfaced in admin** |
| `currency` | String(3) | |
| `created_at` | DateTime | **Never surfaced in admin** |

---

### ItemStoreLink (`item_store_links` table)

| Field | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `variant_id` | FK → `item_variants` CASCADE | |
| `store_id` | FK → `stores` CASCADE | |
| `external_item_id` | String(150) | External catalog ID |
| `original_url` | Text | Non-affiliate source URL |
| `program_name` | String(100) | Affiliate program name |
| `merchant_category` | String(255) | Store-side category — **never surfaced** |
| `commission_rate` | Numeric(5,2) | Commission % — shown in inspect but not list |
| `deeplink_generated_at` | DateTime | When affiliate deeplink was created — **never surfaced** |
| `last_synced_at` | DateTime | Last synchronization timestamp |
| `tracking_code` | String(255) | Affiliate tracking code — **never surfaced** |
| `network_metadata` | JSON | Arbitrary affiliate network data — only shown as raw blob |
| `affiliate_url` | Text | Active affiliate URL |
| `price` | Numeric(10,2) | Store-level price (may differ from variant price) |
| `old_price` | Numeric(10,2) | Store-level old price — **never surfaced** |
| `currency` | String(3) | |
| `availability` | String(32) | Indexed — stock status |
| `last_checked_at` | DateTime | Last availability check |
| `is_active` | Boolean | |
| `created_at` | DateTime | **Never surfaced** |

---

### ItemImage (`item_images` table)

| Field | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `item_id` | FK → `items` CASCADE | |
| `variant_id` | FK → `item_variants` CASCADE | **Nullable** — shared or variant-specific |
| `image_url` | Text | |
| `position` | Integer | Sort order |

> The dual nature (item-level vs variant-level) is the single most under-utilized image relationship in the whole system. The admin has zero visibility into which images belong to which variant.

---

### ItemSpecification (`item_specifications` table)

| Field | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `item_id` | FK → `items` | |
| `category` | String(100) | Spec group name |
| `spec_json` | JSON | Structured spec data |

---

### Store (`stores` table)

| Field | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name` | String(100) | |
| `slug` | String(100) | Unique |
| `website` | Text | |
| `country` | String(50) | **Never surfaced in admin** |
| `currency` | String(10) | **Never surfaced in admin** |
| `affiliate_network` | String(100) | |
| `network_slug` | String(100) | **Never surfaced** |
| `api_enabled` | Boolean | **Never surfaced** |
| `feed_enabled` | Boolean | **Never surfaced** |
| `logo_url` | Text | **Never surfaced** |
| `is_active` | Boolean | |
| `created_at` | DateTime | **Never surfaced** |

---

### Taxonomy

| Entity | Key Fields | Item Relationship |
|---|---|---|
| `Brand` | name, slug, industry, is_featured, is_active | `Item.brand_id` (nullable FK) |
| `Category` | name, slug, parent_id, is_leaf, is_active | `Item.category_id` (required FK) |
| `Source` | name, domain, authority_score, is_active | `Item.source_id` (nullable FK) |
| `Topic` | name, slug, is_featured | **No direct item link** (only content-level) |
| `GenderFacet` | name, slug | Content-only — no item link |
| `IntentFacet` | name, slug | Content-only — no item link |
| `PriceTierFacet` | name, slug | Content-only — no item link |
| `AttributeFacet` | name, slug, category_id | Content-only — no item link |

> The commented-out `item_topics` table in `relationships.py` (lines 21–27) is a notable **intentional gap** in the taxonomy — items cannot be tagged with topics.

---

## 2. Item Relationship Mapping

### Full Ecosystem Map

```
Item
├── Brand (nullable FK)                    ← taxonomy, direct
├── Category (required FK)                  ← taxonomy, direct, hierarchical
│   └── Category.parent (self-referential)  ← ancestry chain
├── Source (nullable FK)                    ← ingestion origin
├── ItemVariant[] (1:many, selectin)
│   ├── attributes (JSON)                   ← color, storage, ram, size, volume
│   ├── price / old_price / currency        ← variant-level pricing
│   ├── sku                                 ← catalog identity
│   ├── is_default                          ← primary display variant
│   ├── ItemStoreLink[] (1:many, selectin)  ← commercial layer
│   │   ├── Store (FK)                      ← merchant entity
│   │   ├── affiliate_url                   ← monetization
│   │   ├── price / old_price / currency    ← store-level pricing
│   │   ├── availability                    ← stock status
│   │   ├── commission_rate                 ← revenue metadata
│   │   ├── last_synced_at / last_checked_at ← freshness
│   │   ├── program_name / tracking_code    ← affiliate identity
│   │   └── network_metadata (JSON)         ← raw affiliate payload
│   └── ItemImage[] (variant images)        ← variant-specific visuals
├── ItemImage[] (item images, by position)  ← general product visuals
│   └── variant_id nullable                 ← shared or variant-bound
├── ItemSpecification[] (1:many)            ← structured specs by category
│   └── spec_json (JSON)                    ← typed by item_type
├── Content[] (M2M via content_items)       ← editorial cross-link
├── Reaction[] (polymorphic, noload)        ← engagement
├── Comment[] (polymorphic, noload)         ← engagement
└── View[] (polymorphic, noload)            ← engagement

Denormalized counters on Item:
  like_count, dislike_count, share_count,
  save_count, comment_count, view_count, click_count
```

### Indirect Relationships

| Derived Path | Admin Utility |
|---|---|
| Item → Variant → StoreLink → Store.country | Items available in specific geographies |
| Item → Variant → StoreLink → commission_rate | Revenue-weighted item ranking |
| Item → Variant.old_price vs Variant.price | Discount existence at variant level |
| Item → Variant → StoreLink.old_price vs StoreLink.price | Discount existence at store level |
| Item → Image[variant_id = NULL] | General/shared images |
| Item → Image[variant_id IS NOT NULL] | Variant-specific images |
| Item → Variant.created_at | Variant catalog age |
| Item → Specification.spec_json | Richness/completeness of structured data |
| Brand → Items → Variants → StoreLinkCount | Brand commercial coverage |
| Category → Items → Images | Image coverage rate per category |

### Missing Admin Visibility (confirmed from code)

- No image previews anywhere in the admin (list or inspect)
- No variant comparison table — variants only shown as a count
- No store-level discount visibility (StoreLink.old_price never shown)
- No variant-level discount visibility (ItemVariant.old_price never shown)
- No availability status per variant or store link
- No `last_synced_at` staleness indicator in the list view
- No image coverage breakdown (how many are item-level vs variant-level)
- No `searchable_attributes` JSON visibility
- No `merchant_category` shown anywhere
- No `deeplink_generated_at` or `tracking_code` visibility
- No `Store.country`, `Store.currency`, `Store.api_enabled`, `Store.feed_enabled` in store inspect
- No item thumbnail in the list view

---

## 3. Catalog Coverage Analysis

### Confirmed Coverage Gaps the Data Can Already Answer

These are computable from existing fields with zero schema changes:

| Gap | Query Basis |
|---|---|
| Items without a brand | `Item.brand_id IS NULL` |
| Items with no images | `LEFT JOIN item_images WHERE image_id IS NULL` |
| Items with only one image | `COUNT(item_images) = 1` |
| Items with no specifications | `LEFT JOIN item_specifications WHERE spec_id IS NULL` |
| Items with no description | `Item.description IS NULL OR description = ''` |
| Items with no variants | Impossible by FK design — all items have at least 1 variant |
| Variants without images (variant-specific) | `variant_id IS NULL` for all images of that item |
| Variants without a price | `ItemVariant.price IS NULL` |
| Variants without any store link | `LEFT JOIN item_store_links WHERE link_id IS NULL` |
| Variants with no active store link | `ALL store links have is_active = False` |
| Store links with stale `last_synced_at` | `last_synced_at < NOW() - INTERVAL '7 days'` |
| Store links with stale `last_checked_at` | `last_checked_at < NOW() - INTERVAL '24 hours'` |
| Store links with `availability` != 'InStock' | `availability NOT IN ('InStock', NULL)` |
| Items where `rating IS NULL` | `Item.rating IS NULL` |
| Items where `review_count IS NULL or 0` | `Item.review_count IS NULL OR review_count = 0` |
| Items with no linked content | `content_items` join returns empty |
| Items with no `searchable_attributes` | `Item.searchable_attributes IS NULL` |
| Store links where price differs significantly from variant price | Cross-compare `StoreLink.price` vs `ItemVariant.price` |
| Items with mismatched currency across store links | Variants with links in multiple currencies |

### Recommended Admin Surfaces

> [!IMPORTANT]
> These should all be derivable from a **single catalog health query** run once on page load and cached — not per-row N+1 queries.

**List View Filters to Add**
- `has_images` / `no_images` toggle
- `has_description` / `no_description` toggle
- `has_brand` / `no_brand` toggle
- `availability` filter (InStock / OutOfStock / Unknown)
- `stale_sync` toggle (last_synced > N days)
- `has_discount` filter (old_price > price exists on any link)

**Dashboard KPI Cards to Add**
- Total items in catalog
- % with images
- % with description
- % with brand assigned
- % with at least 1 active store link
- % with stale sync (> 7 days)
- % with at least 1 linked content piece
- Average variant count per item

---

## 4. Admin List View Improvements

### Current State (from `tables.py` and `items.py`)

The current item list table has **7 columns**:
`Name | Category / Brand | Price | Store Count | Click Count | Added | Actions`

This is a reasonable baseline but leaves significant operational value on the table.

### What Is Already Computed but Not Shown

The `_load_item_aggregates()` function already computes `min_price` and `store_count` efficiently via SQL subqueries. The `items_rows()` serialization for the HTML partial also computes these. No additional backend work is needed for most improvements below.

### Recommended Column Enhancements

| Column | Recommendation | Value |
|---|---|---|
| **Name** | Add compact thumbnail (first `image_url`) left of name | Quick visual identification |
| **Category / Brand** | Already good — no change needed | ✅ Well-designed |
| **Price** | Show price range if multiple variants (e.g. "49 – 299 USD") instead of min only | Shows catalog breadth |
| **Variants** | Add variant count badge next to price | Immediate multi-variant awareness |
| **Store Count** | Already shown — add color: 0=red, 1-2=amber, 3+=green | Status at a glance |
| **Sync Age** | New column: days since `last_synced_at` (max across all store links) | Operational freshness |
| **Image** | Small ✓/✗ or thumbnail — flag items with no images | Quality control |
| **Click Count** | Already shown | ✅ Good |
| **Added** | Already shown | ✅ Good |

### Sort Options to Add

Current sort options: `id`, `created_at`, `name`, `click_count`, `view_count`.

Recommended additions:
- `min_price` — sort by lowest available price
- `store_count` — sort by number of active store links
- `like_count`, `save_count` — sort by engagement signals
- `last_synced_at` — sort by stalest sync first (operational priority)

These are all indexed or computable at the aggregate level.

### Recommended New Filters

- **Has Images** (boolean) — critical for quality control
- **Has Description** (boolean)
- **Has Brand** (boolean)
- **Availability** (dropdown: InStock / OutOfStock / Unknown / Mixed)
- **Stale Sync** (checkbox: sync older than 7 days)
- **Discount Present** (checkbox: any store link has old_price set)
- **Item Type** — already in the template ✅

---

## 5. Inspect / Detail View Improvements

### Current State (from `build_item_inspect_data()` + `tables.py`)

The inspect page renders 4 sections via `get_inspect_table()`:

| Section | Fields |
|---|---|
| Product Core Mappings | id, name, category, brand, source, added, last synced |
| Variants & Availability | variants count, store count, price, variant groups |
| Performance Metrics | engagement score, views, likes, dislikes, comments, shares, saves, click count |
| Content & Quality | linked contents, description (Yes/No), rating, review count, images count, specs count |

Plus: `store_links` table, `distribution_history`, recent comments.

### What Works Well

- Engagement metrics are comprehensive and already computed ✅
- Store links table includes commission_rate (good) ✅
- Distribution history is surfaced ✅
- Recent comments appended dynamically ✅

### What Is Missing from the Inspect View

**Section: Variants & Availability — Critical Gaps**

The current section shows a *count* of variants and a *text summary* of variant groups. It does not show individual variants. This means an admin looking at a 10-variant phone cannot see which variants are priced, which have images, or which have active store links.

Recommended: Replace/supplement variant group text with a **Variant Summary Table** (see §6).

**Section: Content & Quality — Key Gaps**

- `description` shown as "Yes/No" — the actual description text is never shown. Consider showing the first 200 characters as a preview.
- `images count` shown as a number — no thumbnails, no breakdown of item-level vs variant-level images.
- `searchable_attributes` JSON is never shown — admins cannot verify what is being indexed.
- `rating` and `review_count` are surfaced ✅ — but origin (external vs platform) is unclear.

**Section: Store Links — Gaps**

The store links table shows `store_name`, `affiliate_network`, `program_name`, `affiliate_url`, `original_url`, `price`, `currency`, `availability`, `is_active`, `metadata`, `commission_rate`.

Missing from the table:
- `old_price` — discount visibility
- `last_synced_at` — freshness visibility (critical for operations)
- `last_checked_at` — availability check freshness
- `deeplink_generated_at` — when the affiliate URL was last generated
- `merchant_category` — how the store classifies this item
- `external_item_id` — the external catalog identifier

**New Section Recommended: Image Gallery**

Currently, the inspect page shows `images_count` as a number. No thumbnail grid exists anywhere.

A compact admin thumbnail strip (e.g. 5–8 thumbnails, 64×64 px each) with a badge showing variant association ("Shared" vs "Variant: Blue") would give immediate image quality visibility without a gallery-style browser.

**New Section Recommended: Specifications Preview**

`specs_count` is shown as a number. The `full_details` property already structures all spec JSON. A collapsible specification panel in the inspect view would surface this data for quality review without any backend changes.

### Recommended Inspect Section Order

```
1. Product Core Mappings         (existing — good)
2. Variants & Availability       (existing — needs variant table)
3. Store Links / Affiliate Data  (existing — add missing fields)
4. Images                        (new — thumbnail strip with variant labels)
5. Specifications                (new — collapsible spec viewer)
6. Performance Metrics           (existing — good)
7. Content & Quality             (existing — add description preview)
8. Distribution History          (existing — good)
9. Recent Comments               (existing — good)
```

---

## 6. Variant Management Visibility

### Current State

The inspect view shows variants as:
- `variants count`: a single integer
- `variant groups`: a single HTML string like **Color**: Blue, Red / **Storage**: 128GB, 256GB

Individual variant data is completely invisible to admins.

### Why This Is a Problem

For items with 5–20 variants (common for electronics), admins cannot determine:
- Which specific variants are priced vs unpriced
- Which variants have active store links
- Which variants have images
- Whether any variant is missing a SKU
- Price differences across variants
- Which variant is set as default

### Recommended: Variant Summary Table

A per-variant row table in the inspect view, computable from existing data:

| Variant | SKU | Attributes | Price | Old Price | Store Links | Images | Default |
|---|---|---|---|---|---|---|---|
| Blue / 128GB | SKU-001 | color: Blue, storage: 128GB | 49.99 USD | 69.99 | 2 active | 3 | ✓ |
| Blue / 256GB | SKU-002 | color: Blue, storage: 256GB | 79.99 USD | — | 1 active | 0 ⚠ | |
| Red / 128GB | SKU-003 | color: Red, storage: 128GB | 49.99 USD | — | 0 ⚠ | 2 | |

This table is fully derivable from `item.variants`, `v.store_links`, and `v.images` which are already loaded with `selectinload` in `build_item_inspect_data()`. No additional queries are needed.

**Warning badges** should be shown for:
- 0 images on a variant (⚠ Missing Images)
- 0 active store links on a variant (⚠ No Active Links)
- No price set on a variant (⚠ Unpriced)
- Missing SKU (⚠ No SKU)

### Recommended: Price Comparison

For items with multiple variants, show a price range summary:
- Min price across variants
- Max price across variants
- Number of variants with discounts (old_price > price)
- Number of unpriced variants

---

## 7. Image Visibility & Management

### Current State

Images are loaded with `selectinload` in the inspect query. The `image_url` cached property returns the first item image. Images are counted in the inspect panel.

**No image is ever shown visually in the admin interface.**

### Image Architecture Analysis

The `ItemImage` model has a nullable `variant_id`. This creates three image categories:

| Category | Condition | Admin Visibility |
|---|---|---|
| Shared item images | `variant_id IS NULL` | Counted only |
| Variant-specific images | `variant_id IS NOT NULL` | Counted only |
| Primary image | `position = 0, variant_id IS NULL` | Exposed via `image_url` property |

The `variant_images` relationship is defined on `ItemVariant` (back-populated from `ItemImage`). Variant-specific images are loaded via `selectinload(Item.images)` but are **not differentiated** in the inspect view.

### Recommended Improvements

**List View**
- Show a 40×40 px thumbnail of `item.image_url` at the start of each row
- Show a small "No Image" badge if `image_url` is None
- This requires zero backend change — `image_url` is already available

**Inspect View — Image Strip**
- Show thumbnails ordered by `position` (already the ORM default ordering)
- Label each thumbnail: "Shared" or "Variant: [display_name]"
- Highlight missing image coverage: e.g. "3 variants have no images"
- Total image count breakdown: "5 shared, 3 variant-specific"

**Image Coverage Summary (in Variants Table)**
Per variant row, show image count. Flag zero-image variants.

**List View Filter**
Add `?has_images=false` filter to quickly find uncovered items.

---

## 8. Pricing & Affiliate Intelligence

### Pricing Architecture

There are **three price layers** in the system:

| Layer | Model | Fields | Admin Visibility |
|---|---|---|---|
| Variant price | `ItemVariant` | `price`, `old_price`, `currency` | Variant price used in list (as min), old_price NEVER shown |
| Store link price | `ItemStoreLink` | `price`, `old_price`, `currency` | Store price shown in store links table, old_price NEVER shown |
| Minimum price (computed) | Admin aggregate | min across variant prices | Shown in list view |

The presence of `old_price` at both the variant level and the store link level means discount detection is already possible with zero schema changes.

### Discount Visibility Gaps

- **Variant-level discounts**: `ItemVariant.old_price > ItemVariant.price` — never shown anywhere
- **Store-level discounts**: `ItemStoreLink.old_price > ItemStoreLink.price` — never shown anywhere
- A simple "Has Discount" badge on items in the list view would provide immediate commercial visibility

### Sync Staleness

`ItemStoreLink` has both `last_synced_at` and `last_checked_at`. The inspect view already computes `last_synced` by taking `max(last_synced_dates)`. However:
- The list view does not show sync age at all
- No staleness threshold is enforced or highlighted
- No visual indicator exists for "last synced > 7 days ago"

Recommended: Add a sync age column or badge in the list view. Color-code: green (< 1 day), amber (1–7 days), red (> 7 days).

### Affiliate Coverage Gaps

- `commission_rate` is shown in the inspect store links table ✅
- `program_name` is shown ✅
- `deeplink_generated_at` — when the affiliate URL was actually created — is never shown. This is important for detecting links that may be stale at the deeplink level even if the data was recently synced.
- `tracking_code` — never surfaced, important for debugging affiliate attribution
- `merchant_category` — never surfaced; useful for cross-checking catalog categorization vs how the store classifies the item

### Availability Monitoring

`ItemStoreLink.availability` is indexed and populated. It is shown in the store links table in the inspect view. But:
- There is no list-view availability filter
- There is no availability summary per item in the list (e.g. "All in stock" vs "Some out of stock")
- There is no dashboard KPI for out-of-stock items

---

## 9. Analytics Opportunities

All of the following can be computed from existing tables with no schema changes.

### Catalog Health KPIs

| Metric | Derivation |
|---|---|
| Total items | `COUNT(items.id)` |
| Items with images | `COUNT DISTINCT item_id FROM item_images` |
| Items without images | Total - with images |
| Items without brand | `COUNT WHERE brand_id IS NULL` |
| Items without description | `COUNT WHERE description IS NULL` |
| Items with no active store link | Left join aggregate |
| Items with stale sync (>7d) | `MAX(last_synced_at) < NOW()-7d` |
| Avg variants per item | `AVG(variant count per item)` |
| Avg store links per item | `AVG(store link count per item)` |
| Items with discount present | Any variant or store link has old_price |
| Items with external rating | `COUNT WHERE rating IS NOT NULL` |
| Items with no linked content | Left join content_items |
| Avg engagement score | Aggregate engagement score |

### Distribution Analytics

| Metric | Derivation |
|---|---|
| Items by item_type | `GROUP BY item_type` |
| Items by category | `GROUP BY category_id` |
| Items by brand | `GROUP BY brand_id` |
| Items by source | `GROUP BY source_id` |
| Store link count by store | `GROUP BY store_id` |
| Store link count by affiliate network | `JOIN stores GROUP BY affiliate_network` |
| Commission rate distribution | `GROUP BY commission_rate ranges` |

### Engagement Analytics (from existing denormalized counters)

| Metric | Derivation |
|---|---|
| Top clicked items | `ORDER BY click_count DESC` |
| Top viewed items | `ORDER BY view_count DESC` |
| Top saved items | `ORDER BY save_count DESC` |
| Top liked items | `ORDER BY like_count DESC` |
| Most commented items | `ORDER BY comment_count DESC` |
| Engagement-to-click ratio | `(view_count + like_count) / click_count` |

### Sync Health Analytics

| Metric | Derivation |
|---|---|
| Links synced today | `last_synced_at >= TODAY` |
| Links synced this week | `last_synced_at >= WEEK_AGO` |
| Links never synced | `last_synced_at IS NULL` |
| Links with availability = OutOfStock | `availability = 'OutOfStock'` |
| Links by affiliate network | `JOIN stores GROUP BY affiliate_network` |

---

## 10. Visualization Opportunities

### Item Dashboard Page (recommended new section)

A catalog health summary at the top of `/admin/items` before the table:

```
┌─────────────┐ ┌──────────────┐ ┌─────────────────┐ ┌──────────────────┐
│ 1,284 items │ │ 94% with img │ │ 87% have links  │ │ 23 stale syncs   │
│   in catalog│ │              │ │                 │ │   (>7 days)      │
└─────────────┘ └──────────────┘ └─────────────────┘ └──────────────────┘
┌──────────────────────┐ ┌─────────────────────┐ ┌──────────────────────┐
│ 12 items unbranded   │ │ 48 items no desc.   │ │ 67 items no content  │
└──────────────────────┘ └─────────────────────┘ └──────────────────────┘
```

Each card should be **clickable** and apply the corresponding filter to the list below.

**Why**: Turns the item list page from a passive browse into an active operational tool.

### Catalog Completeness Score (per item, in list)

A simple completeness indicator (e.g., a progress bar or colored dot) per row:

```
● Green (complete): has image + brand + description + at least 1 active link + priced variants
● Amber (partial): 3 of 5 criteria met
● Red (incomplete): 0–2 of 5 criteria met
```

This score is **computable entirely from existing data** — it requires extending `_load_item_aggregates()` to also return image presence, description presence, brand presence, and active link count.

### Brand Distribution (Brand inspect page)

On the Brand detail page:
- Item count for this brand
- Image coverage % for brand's items
- Average price across brand's items
- Top 5 items by click count

### Category Distribution (Category inspect page)

On the Category detail page:
- Item count
- Image coverage %
- Average price range
- Variant coverage (average variants per item)
- Items with no linked content

### Store Inspect — Missing Data

The store inspect page (`build_store_inspect_data`) currently only shows:
`id, name, slug, website, status, affiliate_network, product_count`

Missing high-value fields:
- `country`, `currency` — geographic/commercial context
- `api_enabled`, `feed_enabled` — integration method visibility
- `logo_url` — visual identity
- Average commission rate across this store's links
- Number of out-of-stock links for this store
- Oldest `last_synced_at` link for this store (staleness)
- Total clicks attributed to this store

---

## 11. Catalog Health & Quality Visibility

### Recommended Review Queue

A dedicated "Catalog Health" filter state or tab with these pre-configured filters:

| Review Queue | Filter Condition | Priority |
|---|---|---|
| No Images | `images_count = 0` | High |
| Unbranded Items | `brand_id IS NULL` | High |
| No Description | `description IS NULL` | Medium |
| Stale Sync | `max(last_synced_at) > 7 days ago` | High |
| No Active Store Links | `active_link_count = 0` | High |
| Out of Stock | All links show OutOfStock | Medium |
| No Content Links | `linked_contents = 0` | Low |
| No External Rating | `rating IS NULL` | Low |

### Item-Level Health Badges in List View

Rather than adding many columns, small icon badges can communicate quality efficiently:

| Badge | Condition | Icon/Color |
|---|---|---|
| No Image | `image_url IS NULL` | 🖼 gray |
| No Brand | `brand_id IS NULL` | 🏷 amber |
| No Active Link | `store_count = 0` | 🔗 red |
| Stale Sync | sync > 7 days | 🕐 amber |
| Has Discount | any old_price present | 🏷 green |
| Out of Stock | all availability = OutOfStock | ⚠ red |

---

## 12. Existing Data Utilization Score

### By Model

| Model | Utilization | Assessment |
|---|---|---|
| `Item` (core fields) | High | name, slug, brand, category, source shown; counts shown |
| `Item` (searchable_attributes) | **Zero** | Never surfaced anywhere |
| `Item` (search_text/vector) | Zero in admin | Used for search only, not inspectable |
| `ItemVariant` (price, currency) | Partial | Used for min_price aggregate; individual variant prices invisible |
| `ItemVariant` (old_price) | **Zero** | Never shown anywhere |
| `ItemVariant` (sku) | **Zero** | Never shown in admin |
| `ItemVariant` (attributes) | Partial | Shown as summary text only |
| `ItemVariant` (created_at) | **Zero** | Never shown |
| `ItemStoreLink` (affiliate_url, price, currency) | High | Shown in inspect store links table |
| `ItemStoreLink` (old_price) | **Zero** | Never shown |
| `ItemStoreLink` (last_synced_at) | Partial | Only max shown in inspect; not in list |
| `ItemStoreLink` (last_checked_at) | **Zero** | Never shown |
| `ItemStoreLink` (deeplink_generated_at) | **Zero** | Never shown |
| `ItemStoreLink` (commission_rate) | Partial | Shown in inspect only |
| `ItemStoreLink` (merchant_category) | **Zero** | Never shown |
| `ItemStoreLink` (tracking_code) | **Zero** | Never shown |
| `ItemStoreLink` (network_metadata) | Partial | Shown as raw object |
| `ItemStoreLink` (availability) | Partial | Shown in inspect; not filterable in list |
| `ItemStoreLink` (external_item_id) | **Zero** | Never shown |
| `ItemImage` (variant_id) | **Zero** | Image breakdown never shown; thumbnails never shown |
| `ItemSpecification` (spec_json) | **Zero in admin** | Counted only; content never displayed |
| `Store` (country) | **Zero** | Never shown |
| `Store` (currency) | **Zero** | Never shown |
| `Store` (api_enabled/feed_enabled) | **Zero** | Never shown |
| `Store` (logo_url) | **Zero** | Never shown |
| `Store` (network_slug) | **Zero** | Never shown |

### Overall Assessment

The system has a very solid data model. The backend is well-engineered (SQL aggregates instead of N+1, selectin loading, proper indexes). The admin frontend is the bottleneck: **roughly 40–50% of stored item/variant/affiliate data is completely invisible to administrators.** The most critical gaps are image visibility, variant-level detail, discount/old_price visibility, and sync staleness.

---

## 13. Implementation Roadmap

### Phase 1 — Quick Wins (High Value, Low Effort)

These require minimal backend changes and zero schema migrations. Most are column additions to existing serializers or inspect data builders.

| # | Task | Files Affected | Effort |
|---|---|---|---|
| 1.1 | Add item thumbnail to list view | `items.py → items_rows()`, list template | XS |
| 1.2 | Add `last_synced_at` age badge to list view | `_load_item_aggregates()` + serializer | S |
| 1.3 | Show "No Image" badge in list | `items_rows()` serializer | XS |
| 1.4 | Add `has_images` + `no_brand` filters to `/admin/items/` | `list_items()` + `items_rows()` + `items.js` | S |
| 1.5 | Add `old_price` to store links table in inspect | `build_item_inspect_data()` + tables.py | XS |
| 1.6 | Add `last_synced_at` and `last_checked_at` to store links table | Same as above | XS |
| 1.7 | Add `availability` filter to item list | `list_items()` + `items_rows()` + JS | S |
| 1.8 | Add `merchant_category` and `external_item_id` to store links table | `build_item_inspect_data()` | XS |
| 1.9 | Add description preview (first 200 chars) to inspect Quality section | `build_item_inspect_data()` | XS |
| 1.10 | Add store country/currency/api_enabled to store inspect | `build_store_inspect_data()` + tables.py | XS |
| 1.11 | Sort options: add `min_price`, `store_count`, `like_count`, `last_synced_at` | `_ITEM_SORT_MAP` + JS | S |

---

### Phase 2 — Catalog Management Enhancements (Medium Effort)

These require moderate backend changes but no schema migrations.

| # | Task | Files Affected | Effort |
|---|---|---|---|
| 2.1 | **Variant Summary Table** in inspect — per-variant row with price, SKU, attributes, store links count, image count, default flag, and health badges | `build_item_inspect_data()`, `item_detail.html` template, `tables.py` | M |
| 2.2 | **Image Strip** in inspect — thumbnail grid with variant/shared label | `build_item_inspect_data()`, `item_detail.html` | M |
| 2.3 | **Specifications Panel** in inspect — collapsible structured spec viewer using `full_details` | `build_item_inspect_data()`, inspect template | M |
| 2.4 | **Catalog completeness score** per item in list — extend `_load_item_aggregates()` to return image, description, brand, active-link presence; compute score | `items.py`, list template | M |
| 2.5 | **Catalog health filters** as a "Review Queue" toolbar preset | `items.html`, `items.js` | S |
| 2.6 | **Price range display** (min–max) in list view where items have multiple variants | `_load_item_aggregates()` — add max_price | S |
| 2.7 | **Discount badge** in list — detect `old_price IS NOT NULL` across links or variants | `_load_item_aggregates()` | S |
| 2.8 | **Stale sync filter** — list items where `max(last_synced_at)` is older than threshold | `list_items()`, `items_rows()` | S |
| 2.9 | **Store inspect enhancements** — avg commission, out-of-stock count, oldest sync, click totals | `build_store_inspect_data()`, `providers.py` | M |

---

### Phase 3 — Analytics & Operational Intelligence (Medium-High Effort)

| # | Task | Files Affected | Effort |
|---|---|---|---|
| 3.1 | **Catalog Health Dashboard** — KPI cards at top of items page (total, image %, brand %, active link %, stale sync count) | New `admin/stats.py` function + `items.html` | M |
| 3.2 | **Brand page enrichment** — item count, avg price, top clicked items, image coverage % | `taxonomy.py`, brand inspect/detail | M |
| 3.3 | **Category page enrichment** — item count, avg variants per item, image coverage %, items without content | `taxonomy.py`, category inspect/detail | M |
| 3.4 | **Items by item_type distribution** — bar or summary table in dashboard overview | `stats.py` + overview template | S |
| 3.5 | **Sync health panel** — links synced today/this week/never, out-of-stock count, per-store breakdown | New endpoint in `items.py` or `providers.py` | M |
| 3.6 | **Affiliate coverage report** — which stores cover which categories, commission rate distribution | New report endpoint | M |
| 3.7 | **Top items by engagement** — clickthrough rate, save rate, like rate derived from counters | New section in item list or stats page | S |

---

### Phase 4 — Advanced Catalog Insights (Higher Effort, High Value)

| # | Task | Files Affected | Effort |
|---|---|---|---|
| 4.1 | **Catalog completeness score at scale** — background-computed completeness per item stored in a summary table for fast list rendering without per-row joins | New model/migration + background task | L |
| 4.2 | **Variant image gap detection** — identify variants that have no images while sibling variants do | New report query in `items.py` | M |
| 4.3 | **Price drift detection** — identify store links where `StoreLink.price` differs significantly from `ItemVariant.price` (e.g. > 20% difference) | New query + report view | M |
| 4.4 | **Item topic tagging** — re-enable the commented-out `item_topics` association table; tag items with relevant topics for cross-navigation | `relationships.py` + new UI | L |
| 4.5 | **`searchable_attributes` inspector** — show what is currently indexed for search for each item; allow admin to verify/override | Inspect template + `items.py` | M |
| 4.6 | **Affiliate network comparison per item** — for an item with multiple store links, show which affiliate network offers the best commission or lowest price | Inspect view, derived from store links | M |
| 4.7 | **Catalog delta report** — items added/removed/price-changed since last period | Requires `created_at` + price history or changelog | L |

---

## Open Questions

> [!IMPORTANT]
> **Image Architecture Clarification**: The `ItemImage.variant_id` is nullable, creating a shared/specific split. Are item images currently ever assigned to a specific variant intentionally, or is `variant_id` only set by the ingestion pipeline? This affects how prominently to surface the variant-image relationship in the inspect view.

> [!IMPORTANT]
> **Completeness Score Threshold**: For the per-item completeness badge, the 5-criteria model (image + brand + description + active link + priced variant) is a reasonable baseline. Should `specs_count > 0` be a sixth criterion? Or is that domain-specific (electronics always have specs; perfumes may not)?

> [!NOTE]
> **item_topics Commented Out**: The `item_topics` association table is commented out in `relationships.py`. Was this intentionally deferred? Enabling it would allow items to be cross-navigated via topics, which is a meaningful catalog enrichment opportunity.

> [!NOTE]
> **Discount Definition**: `old_price` exists at both variant and store-link level. Should discount badges be triggered by either, or only when the store-link `old_price` is set (which reflects an actual current promotion from the merchant)?

> [!NOTE]
> **Stale Sync Threshold**: The recommend default is 7 days. Is there a business-defined acceptable sync window? Some affiliate feeds update daily; others weekly. This affects which threshold to use for the "stale" badge.
