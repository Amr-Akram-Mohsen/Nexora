# Nexora Platform — Enhancement Plan

A comprehensive plan to evolve Nexora from a basic article + product listing site into a polished, monetisation-ready affiliate content platform.

---

## User Review Required

> [!IMPORTANT]
> This plan is large and intentionally modular. **You do NOT have to approve everything at once.** Tell me which phases you want to tackle first and I'll scope the work accordingly. I've flagged the items I believe are **highest impact** with ⭐.

> [!WARNING]
> Phase 1 (article full-content scraping) involves web scraping of third-party sites. This is a grey area legally — most sites allow it for personal/non-commercial reading, but caching and re-displaying their HTML on your own domain can violate terms of service. The recommended approach I describe below is the safest legal path.

---

## Phase 1 — Solve the Article Full-Content Problem ⭐

### The Problem
Your current article APIs (NewsAPI, GNews) only return **title + description + URL**. The `content` column in your `Article` model is always `NULL`. When a user opens an article page, they see a short description and a "Read Full Article" button that sends them away — which is bad for engagement and SEO.

### Recommended Solutions (pick one or combine)

#### Option A: Scrape Full Content at Ingest Time (Recommended) 
Add a new `content_scraper.py` that, after storing an article, fetches the source URL and extracts the main body text using a library like **`newspaper3k`** or **`trafilatura`**.

- **Pros**: Full content stored locally, fast page loads, great for SEO
- **Cons**: Some sites block scrapers; content may be copyrighted
- **Legal safety**: Display a short excerpt (first 2–3 paragraphs) and always link to source with proper attribution. Never remove the "Read Full Article" link.

#### Option B: Use RSS feeds that already include full content
Some of your existing RSS feeds (e.g., The Verge, TechCrunch, How-To Geek) actually include full `<content:encoded>` in their feed entries. Your `rss_fetcher.py` currently ignores this and only reads `summary`. **This is a quick free win.**

#### Option C: Switch to / add APIs that provide full content
- **Bing News Search API** (free tier: 1,000 calls/month) — provides richer snippets
- **Mediastack** (free: 500 req/month) — returns full content for some sources
- **Currents API** (free: 600 req/day) — provides full content

### Proposed Changes

#### [NEW] `app/scrapers/content_scraper.py`
- Uses `trafilatura` or `newspaper3k` to extract article body from URL
- Called after `store_article()` succeeds
- Stores result in `Article.content`
- Has a rate limit and retry logic
- Respects `robots.txt` via `urllib.robotparser`

#### [MODIFY] `app/scrapers/rss_fetcher.py`
- Extract `content:encoded` or `content` from feed entries when available
- Pass it through to `clean_article_data()` → `store_article()`

#### [MODIFY] `app/scrapers/cleaner.py`
- Accept and sanitise a `content` field (strip scripts, styles, iframes)
- Truncate at a safe maximum length (e.g., 15,000 chars)

#### [MODIFY] `app/scrapers/storer.py`
- Store `content` in the Article model when provided

#### [MODIFY] `app/templates/article-page.html`
- If `article.content` exists, render it instead of just the description
- Always keep the "Read Full Article" link to the source
- Add a "Source: [name]" attribution footer

---

## Phase 2 — Affiliate Disclosure & Product Embedding in Articles ⭐

This is what your friend was describing — it's called **FTC affiliate disclosure** and **native product embedding**.

### 2A: Global Affiliate Disclosure Banner

#### [NEW] `app/templates/partials/affiliate-disclosure.html`
A small, tasteful banner/label that appears:
- On every page with affiliate links (item pages, article pages with embedded products)
- Text: *"Some links on this page are affiliate links. We may earn a commission at no extra cost to you."*
- Links to your `/affiliate` (Affiliate Disclosure) page
- Styled as a subtle info bar — not a popup

#### [MODIFY] `app/templates/components/features/purchase-options.html`
- Add a small disclosure label above or below the "Where to Buy" section
- Example: `🔗 Affiliate link · We may earn a commission` with a tooltip explaining

### 2B: Embed Related Products Inside Article Pages ⭐

When a user reads an article about "iPhone 16 Pro Review", they should see the iPhone 16 Pro product card **inline within the article** — not just in a separate products page.

#### [NEW] `app/templates/components/features/inline-product-card.html`
- A compact product card designed for embedding inside article content
- Shows: image, name, price range, "View Deal" button (affiliate link)
- Has a small `Sponsored` or `Affiliate` label

#### [MODIFY] `app/templates/article-page.html`
- After the article content, render `linked_items` (already exists as a relationship in your model!) as inline product cards
- Section title: "Products mentioned in this article"
- Each card links to the item page or directly to the affiliate URL

#### [MODIFY] `app/routes/catalog.py` → `article_page()`
- Eagerly load `article.linked_items` with their variants, store links, and images
- Pass them to the template

---

## Phase 3 — Homepage & Card Redesign for Better Product Visibility ⭐

### The Problem
Products (items) are currently buried. The homepage shows a "hot deals" section with product cards, but they look like afterthoughts and don't highlight prices or affiliate CTAs.

### 3A: Redesigned Item Card

#### [MODIFY] `app/templates/components/cards/item-card.html`
- Show actual price prominently (currently it's hidden or poorly formatted)
- Show old price with strikethrough when there's a discount
- Add a "Best Price" or "View Deal" CTA button
- Show store logo badge (Amazon SA, Amazon AE, Noon, etc.)
- Remove hardcoded "4.7 rating" and "982 reviews" — these are fake and will hurt credibility

#### [MODIFY] `app/templates/components/cards/article-card.html`
- Remove hardcoded "5 min" read time — calculate it from content length or remove it
- Fix: `strftime` will crash if `published_at` is `None`

### 3B: Homepage Product Showcase

#### [MODIFY] `app/templates/index.html`
- Add a dedicated "Top Deals" section with a horizontal scrollable product carousel
- Add a "Recently Added" product section
- Interleave product cards within article sections (every 3rd or 4th card is a product) — this is the "merged" behavior your friend described

#### [MODIFY] `app/routes/base.py` → `home()`
- Load top deals (items with the biggest discount percentage)
- Load recently added products

### 3C: Deals/Products Dedicated Page

#### [NEW] `app/templates/deals-page.html`
- A full page for browsing products
- Filterable by category, brand, price range, store
- Sort by: price low-to-high, newest, most popular

#### [MODIFY] `app/routes/catalog.py`
- Add a `/deals` route that serves this page
- Reuse existing filter infrastructure from sections page

---

## Phase 4 — Backend Data Model Improvements

### 4A: Fix Hardcoded / Missing Data

| Issue | Location | Fix |
|-------|----------|-----|
| Hardcoded "4.7" rating and "982 reviews" | `item-card.html`, `item-page.html` | Either remove entirely or add a `rating` / `review_count` field to `Item` model and populate from Amazon PA-API |
| Hardcoded "5 min" read time | `article-card.html`, `article-page.html` | Calculate from `len(content)` using ~200 WPM formula, or remove |
| `Article.content` always NULL | `storer.py` | Populate via Phase 1 content scraper |
| `Article.image` column — what is this? | `models.py` line 223 | Appears to be a duplicate of `image_url`. Either remove it or clarify its purpose (local cached image path?) |

#### [MODIFY] `app/models.py`
- Add `read_time_minutes` computed property to Article: `max(1, len(self.content.split()) // 200)` if content exists
- Add optional `rating` and `review_count` to Item (populate from Amazon or leave NULL)
- Consider removing the unused `Article.image` column

### 4B: Noon / ArabClicks Integration Placeholder

You have `ARABCLICKS_PUBLISHER_ID` in config but no scraper for it.

#### [NEW] `app/scrapers/noon_arabclicks.py`
- Stub module for future ArabClicks deep-link generation
- ArabClicks provides an API to convert any Noon/Namshi/etc. URL into an affiliate link
- Would create `Store` records for Noon SA, Noon AE, Namshi, etc.
- Not fully implementable without the API key, but the structure should be ready

---

## Phase 5 — Frontend Polish & New Pages

### 5A: Missing Pages That Need Content

| Page | Current State | Enhancement |
|------|---------------|-------------|
| `/privacy` | Has content in `pages_content.py` but generic | Customize for Nexora / KSA-UAE audience |
| `/terms` | Has content but generic | Customize |
| `/affiliate` | Template exists, bare `{{ content }}` | **Needs full design** — this is a legal requirement for affiliate sites |
| `/login` | Bare `login.html` with just `{{ extends }}` | Needs a proper login form UI |
| `/register` | Bare template | Needs a proper registration form UI |

#### [MODIFY] `app/templates/affiliate.html`
- Full page with styled content explaining affiliate relationships
- List of affiliate partners (Amazon, ArabClicks/Noon)
- Designed to build trust

#### [MODIFY] `app/templates/login.html` & `register.html`
- Currently these are almost empty. They need proper form UIs using your existing design system.

### 5B: User Saved Items Page

Your `Save` model exists and works, but there's **no page to view saved items**.

#### [NEW] `app/templates/saved-items.html`
- Lists all saved articles and items for the logged-in user
- Grouped by type (Articles / Products)
- "Unsave" button on each card

#### [MODIFY] `app/routes/catalog.py` or `interactions.py`
- Add `/saved` route (login required)
- Query `Save` model for current user

### 5C: Product Comparison (Future / Optional)

For electronics especially, a compare feature is very valuable.

#### [NEW] `app/templates/compare-page.html`
- Side-by-side specification comparison for 2–3 items
- Already have `ItemSpecification` model — this is about display

---

## Phase 6 — Scraper & API Improvements

### 6A: Content Quality Improvements

#### [MODIFY] `app/scrapers/rss_fetcher.py`
- Extract `content:encoded` from RSS entries (many feeds include full content here)
- Some current feeds are dead or unreliable. Add fallback logic.

#### [MODIFY] `app/scrapers/cleaner.py`
- Add HTML sanitization for content field (allow safe tags like `<p>`, `<h2>`, `<ul>`, `<img>`, strip everything else)
- Add better duplicate detection (normalize URLs, strip tracking params)

### 6B: New Content Sources (Free)

| Source | What it provides | Cost |
|--------|-----------------|------|
| **Dev.to API** | Full content tech articles | Free, no key |
| **DEV Community RSS** | Tech tutorials with full content | Free RSS |
| **Hacker News API** | Tech discussion links | Free, no key |
| **Product Hunt API** | New product launches | Free tier |

### 6C: Article-to-Item Matcher Improvements

#### [MODIFY] `app/utils/matcher.py`
- Current matcher loads ALL items and ALL articles into memory — will not scale
- Add batch processing with pagination
- Add smarter matching using brand + category, not just title substring
- Add a `last_matched_at` timestamp to avoid re-processing

---

## Phase 7 — Code Quality & Cleanup

### Items to Fix

| Issue | File | Priority |
|-------|------|----------|
| `datetime.utcnow()` is deprecated in Python 3.12+ | Throughout (`models.py`, services) | Medium — switch to `datetime.now(timezone.utc)` |
| Duplicate `import secrets` | `auth.py` line 1 and line 45 | Low |
| `Article.image` vs `Article.image_url` — two columns for same purpose? | `models.py` | Medium — clarify or remove one |
| `item.full_specs` referenced in `catalog.py:118` but model has `full_details` | `catalog.py` line 118 | **Bug** — will crash |
| Social links still say "newtechme" | `config.py` SOCIAL_LINKS | Low — update to Nexora |
| Contact page has fake SF address | `pages_content.py` | Low — update |
| `search_service.py` is nearly empty (13 lines) | `services/` | Low — integrate into article_service or expand |
| `.env` file committed to git with real API keys | `.env` | **HIGH** — rotate all keys and add to `.gitignore` |

> [!CAUTION]
> **Your `.env` file contains real API keys and email credentials and appears to be committed to GitHub.** You should immediately:
> 1. Add `.env` to `.gitignore`
> 2. Rotate ALL keys (Google OAuth, NewsAPI, GNews, YouTube, Gmail app password)
> 3. Use `git filter-branch` or BFG to remove `.env` from git history

---

## Suggested Execution Order

I recommend tackling these in this priority:

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| 🔴 **Critical** | Phase 7 — `.env` security fix | 10 min | Prevents credential leak |
| ⭐ 1st | Phase 1 Option B — Extract RSS full content | 1–2 hrs | Immediate content improvement |
| ⭐ 2nd | Phase 2B — Embed products in articles | 2–3 hrs | Affiliate revenue enabler |
| ⭐ 3rd | Phase 2A — Affiliate disclosure labels | 1 hr | Legal compliance |
| ⭐ 4th | Phase 3A — Fix item cards (remove fake data, show real prices) | 2 hrs | Credibility |
| 5th | Phase 4A — Fix hardcoded data in templates | 1 hr | Quality |
| 6th | Phase 3B — Homepage product showcase | 2–3 hrs | Engagement |
| 7th | Phase 5B — Saved items page | 2 hrs | User feature |
| 8th | Phase 5A — Login/Register/Affiliate page design | 3–4 hrs | Completeness |
| 9th | Phase 1 Option A — Content scraper | 3–4 hrs | Deep content |
| 10th | Phase 3C — Deals page | 3–4 hrs | Product discovery |
| Later | Phase 6 — Scraper improvements | Ongoing | Data quality |
| Later | Phase 4B — Noon/ArabClicks | When you get the API key | Revenue source |
| Later | Phase 5C — Product comparison | 4–5 hrs | Power user feature |

---

## Open Questions

> [!IMPORTANT]
> 1. **Content scraping stance**: Do you want to scrape and store full article content locally (Option A), or just extract what RSS feeds already provide (Option B)? Option B is safer and faster to implement.
> 2. **The `Article.image` column**: Is this used for locally cached images? Can I remove it, or should I keep it alongside `image_url`?
> 3. **Fake ratings/reviews**: Should I remove the hardcoded "4.7 / 982 reviews" entirely, or do you have a plan to get real rating data (e.g., from Amazon API)?
> 4. **Which phases do you want to start with?** I recommend the execution order above, but you drive the priority.
> 5. **ArabClicks/Noon**: Do you have or plan to get an ArabClicks publisher account? This would significantly expand product coverage beyond Amazon.

---

## Verification Plan

### Automated Tests
- Run `flask seed-db` → `flask fetch-all` → verify articles now have `content` populated
- Run the app and visit article pages → verify full content renders
- Visit item pages → verify affiliate disclosure is visible
- Visit article pages with linked items → verify product cards appear inline

### Manual Verification
- Visual inspection of homepage with new product showcase
- Test affiliate link click tracking still works
- Verify no hardcoded fake data remains
- Check responsive layout on mobile viewport
