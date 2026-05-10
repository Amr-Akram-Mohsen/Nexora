# Semantic UX & Taxonomy Analysis Report

This document provides a deep architectural and semantic refinement plan for the platform's display system, taxonomy presentation, metadata hierarchy, and badge strategy. It aims to reduce visual noise, clarify the hierarchy, and ensure semantic consistency across different polymorphic content types (Articles, Videos, Posts) while preserving their distinct identities.

---

## 1. Semantic Hierarchy

### Analysis & Problems
Currently, the templates heavily prioritize badges (Categories and Topics) in the `meta-top` areas, followed by the title, then a mix of `meta-bottom` info (Author, Source, Read Time, Views, Date).
- **Problem:** Cards and headers treat "Category" and "Topic" as equally weighted navigational markers, which flattens the hierarchy.
- **Why it matters:** Users don't distinguish between the "domain" of the content (Category) and the "subject" (Topic). It clutters the visual scanning path before the user even reads the title.

### Recommended Refinements
1. **Primary Information:** The Content Title and Content Type (Article/Video/Post). The user needs to know *what* it is and *what it's about*.
2. **Secondary Information:** The Category (Domain classification) and primary Contextual Metadata (Source/Author, Date).
3. **Tertiary Information:** Engagement metrics (Views, Upvotes) and Read Time.
4. **Contextual Information:** Topics, Intents, and Attributes. These should largely be relegated to filtering/discovery or placed below the fold/content description, rather than crowding the top.

**Implementation Priority:** High

---

## 2. Badge Strategy

### Analysis & Problems
In both cards (`cards/article.html`, `cards/video.html`) and detail pages (`page/article.html`, `page/video.html`), we see multiple badges injected into `meta-top` (`badge--category`, `badge--topic`, `platform-icon`). 
- **Problem:** Density is too high. A video card can display a Category badge, a Topic badge, and a Platform icon all above the title. 
- **Why it matters:** "Badge fatigue" causes users to ignore them entirely. Badges should be signals, not noise.

### Recommended Refinements
- **Maximum Recommended Badge Count:** 
  - **Cards:** 1 Badge (The Category or the most specific Topic) + 1 Type/Platform indicator.
  - **Detail Pages:** 2-3 Badges max (Category + 1-2 primary Topics).
- **Priority Ordering:** Content Type/Platform (often handled by icons) > Category > Topic.
- **When to Show:**
  - **Category:** Show on cards in mixed-category feeds. Do NOT show if the user is already on a Category listing page.
  - **Topic:** Best relegated to tags at the bottom of detail pages, or used strictly as filters. Remove from `meta-top` in cards.
  - **Section / Intent / Attributes:** DO NOT use as badges. Use them as filters or inline metadata.
  
**Implementation Priority:** High

---

## 3. Metadata Hierarchy

### Analysis & Problems
The `meta_bottom` block on cards mixes authorship (`source_name`, `channel_name`, `author`), metrics (`read_time_minutes`, `upvotes`), and temporal data (`published_at`). On detail pages, these are arranged as `meta-pill`s below the title.
- **Problem:** Visual prominence of metadata is not mapped to user intent. A Reddit post's author is less important than its upvotes, but a review article's source is highly important for credibility.

### Recommended Refinements
- **Above Title:** Only critical navigational badges (Category) and Type indicators.
- **Below Title (Detail Pages):** 
  - **Articles:** Source > Read Time > Date.
  - **Videos:** Channel > Views > Date.
  - **Posts:** Subreddit > Author > Upvotes > Date.
- **Footer (Cards):** Group by temporal/credibility vs. engagement. Left-align Source/Author and Date. Right-align Engagement (Views, Upvotes, Read Time).
- **Expandable/Sidebar (Detail Pages):** Linked products, attributes, and brand affiliations belong here, not in the primary header.

**Implementation Priority:** Medium

---

## 4. Section vs Intent Overlap

### Analysis & Problems
Looking at `taxonomy.py`:
- **Sections:** "Reviews", "Tutorials", "News"
- **Intents:** "Buying Guide", "Review", "News", "Tutorial"
- **Problem:** Direct semantic duplication. A piece of content could easily be in the "Reviews" section and tagged with the "Review" intent.
- **Why it matters:** This creates filtering ambiguity (does a user filter by Section or Intent?) and recommendation ambiguity. It also risks redundant badging/tagging if both are displayed.

### Recommended Refinements
- **Refined Semantic Roles:** 
  - **Sections** should represent the *editorial ecosystem* or department of the site (e.g., Editorial, Community, Market Trends).
  - **Intent** should represent the *user's consumption goal* (e.g., Buying Guide, Unboxing, How-To).
- **Action:** Remove "Reviews", "Tutorials", "News" from Sections. Consolidate them strictly into the `Intent` facet. Rename Sections to broader navigational pillars (e.g., "Editorial", "Community Hub", "Market Watch").

**Implementation Priority:** Critical

---

## 5. Taxonomy Display Strategy

### Recommended Refinements
- **Navigational (Categories):** Display as primary navigation links and top-level badges on mixed feeds.
- **Editorial (Sections, Intents):** Use as primary filters in listings. Do NOT display as badges on cards. Can be used as sub-headings or labels on detail pages (e.g., "A Buying Guide").
- **Descriptive (Topics, Brands):** Use for internal routing, "Related Content" algorithms, and sidebar tags on detail pages. Remove from card headers.
- **Commercial (Price Tier, Linked Items):** Display strictly in the detail page sidebar or a dedicated "Products in this video/article" widget. Never in card views.
- **Contextual (Attributes):** Use strictly for facet filtering in the catalog.

**Implementation Priority:** Medium

---

## 6. Visual Noise Reduction

### Analysis & Problems
- **Problem:** Redundant icons (e.g., showing a YouTube icon *and* a "Video" badge overlay on the image). 
- **Problem:** Showing topics on cards (`content.topics[:1]`) often truncates or pushes important metadata out of alignment.

### Recommended Refinements
- **Simplifications:**
  - Drop the Type badge overlay (`<div class="card__type-badge">`) if the platform icon (`platform-icon--youtube`) or source icon implies the type.
  - Remove all `badge--topic` elements from `meta_top` in `base.html` card extensions. 
- **Grouping:** Unify the "Type" and "Platform" into a single, elegant icon-based indicator. 
- **Progressive Disclosure:** Only show detailed metadata (Read Time, View Count) on hover for Desktop cards, or keep them strictly on detail pages.

**Implementation Priority:** High

---

## 7. Content-Type Differentiation

### Analysis & Problems
The platform successfully uses different card layouts (`article.html`, `video.html`, `post.html`), but the metadata cadence feels slightly homogenized.

### Recommended Refinements
- **Articles (Editorial):** Emphasize credibility. Use a sophisticated serif or distinct typography for the Source/Author. Ensure Read Time is prominent.
- **Videos (Media-Centric):** Emphasize visual impact. Maximize thumbnail size. Move all metadata below the title. Emphasize Channel Name and View Count. Strip out Dates on cards unless recent (< 7 days).
- **Posts (Conversational):** Emphasize community. Use the Subreddit as the primary "Category" equivalent (e.g., `r/hardware`). Highlight upvotes and comment counts dynamically.

**Implementation Priority:** Low

---

## 8. Layout Refinement Suggestions

### Recommended Refinements
- **Spacing & Alignment:** 
  - On cards, shift from a `flex-wrap` of multiple badges at the top to a clean, single-line breadcrumb format: `Category • Source`.
- **Badge Placement:** Move all badges inside the card image overlay (top-left) to free up whitespace above the title, creating a stronger Title-to-Image connection.
- **Truncation Strategies:** Do not truncate Category names; if they are too long, the taxonomy is flawed. Aggressively truncate post excerpts to exactly 2 lines to maintain a strict vertical rhythm in CSS Grids.
- **Mobile vs Desktop:** On mobile, hide all tertiary metadata (Dates, Read Times, Views) on cards to maximize vertical space for the Title and Thumbnail.

**Implementation Priority:** Medium

---

## 9. Related/Trending Systems

### Analysis & Problems
Sidebars and compact snippets (e.g., `content-utils.html` macro `content_snippet`) currently show Title, Image, and Date.

### Recommended Refinements
- **Minimum Viable Metadata:** In compact/sidebar views, the *only* things that matter are the Image, Title, and a singular trust/interest signal.
- **Removal:** Remove the Date. It is rarely the deciding factor for clicking a related link.
- **Addition:** Replace Date with the primary Intent (e.g., "Review") or Type (e.g., "Video"). Users click related content based on the format they want to consume next.

**Implementation Priority:** Low

---

## 10. Filtering & Discovery UX

### Analysis & Problems
The overlap of "Topics" (Gaming, Home Office), "Categories" (Laptops, Smartwatches), and "Brands" (Apple, Sony) creates a complex filter sidebar.
- **Problem:** If a user searches for "Apple", they might be interacting with a Brand facet, a Topic, or a search keyword. 

### Recommended Refinements
- **Coherent Hierarchy:** The left sidebar (`listing-page.html`) should strictly order filters by user mental models:
  1. Category (What is it?)
  2. Brand (Who makes it?)
  3. Intent (Why am I reading this?)
  4. Price/Attributes (Specifics)
- **Topics** should be removed from the sidebar filter entirely and used as "Pill Navigation" at the top of the feed (like YouTube's topic ribbons), as they represent lateral, cross-category discovery rather than vertical filtering.

**Implementation Priority:** Medium

---

## Suggested Implementation Order

1. **Phase 1: Semantic Cleanup (Backend/Config)**
   - Refactor `taxonomy.py` to eliminate Section/Intent overlap.
   - Re-map existing database entries to the new Intent facet if they were using Sections for "Reviews/Tutorials".
2. **Phase 2: Card De-cluttering (Frontend - Cards)**
   - Remove Topic badges from all `cards/*.html`.
   - Consolidate Type and Platform indicators.
   - Implement the Top/Bottom metadata realignment.
3. **Phase 3: Detail Page Refinement (Frontend - Pages)**
   - Clean up `meta-pill` density on `page/*.html`.
   - Move commercial/attribute metadata to sidebars or below-content areas.
4. **Phase 4: Discovery UX (Frontend - Listing)**
   - Update `listing-page.html` and `catalog-utils.html` to separate Topics (horizontal ribbons) from Categories/Brands (sidebar facets).
