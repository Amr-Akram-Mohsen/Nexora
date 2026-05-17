# Nexora Log Analysis

## Issue 1 — NewsAPI: 100% `429 Too Many Requests` (All 15 Queries Failed)

### What the log shows
```
05:01:31  ERROR  [INTEGRATION][newsapi] ... Max retries exceeded ... (Caused by ResponseError('too many 429 error responses'))
05:01:46  ERROR  ... same on query 2
05:02:04  ERROR  ... same on query 3
16:43:45 → 16:49:35  ERROR  All 11 queries that actually ran produced 429
```

Both newsapi runs (05:00 and 16:42) produced **zero stored articles**. Every single request hit 429.

### Root cause
**You hit your daily 100-request NewsAPI limit before these runs.** The very first run at 05:00 (right after the DB migration fresh start) already had all 140 eligible queries in the pool, fired 15 of them in rapid succession, and the rate-limiter kicked in immediately. NewsAPI's free tier enforces:
- 100 requests/day (resets at UTC midnight)
- ~1 request/second rate limit

The queries are also **very long** (100+ characters with nested OR blocks + exploration modifiers + suffixes), which doesn't help — but the primary issue is you already exhausted the daily budget or hit the per-second rate limit.

Additionally line 292:
```
err=fetch_newsapi_query() got an unexpected keyword argument 'etag'
```
This is a **separate code bug** — the ingestion workflow is passing `etag` as a keyword argument to `fetch_newsapi_query()`, but that function doesn't accept `etag`. This causes ~half the queries to crash immediately without even hitting the API.

### Fixes needed

**Fix A — Remove `etag` kwarg being passed to NewsAPI/YouTube fetchers.**
In `ingestion.py`, the code that calls `self._process_query(...)` likely passes `etag` unconditionally. Add a guard so `etag` is only forwarded to RSS fetchers.

**Fix B — Query length reduction for NewsAPI.**
The queries are hitting NewsAPI's URL length limit OR are being scored too low because they're too complex. The `{category} (news OR launch OR release)` template for `smartphones` after boolean expansion becomes:
```
(Smartphones OR android phone OR flagship phone OR camera phone OR mobile phone) (news OR launch OR release) (launch OR announced OR release) underrated
```
That's 3 nested OR-blocks. The third block `(launch OR announced OR release)` is the intent_term — it duplicates the template's own `(news OR launch OR release)`. **The intent_term is being appended even though the template already contains intent signals.**

**Fix C — Add inter-request delay for NewsAPI.**
A 1-second `time.sleep(1)` between NewsAPI calls (in `fetch_newsapi_query` or in the ingestion loop) would prevent 429s from the per-second rate limit.

---

## Issue 2 — GNews: 100% `unexpected_response_shape` for Perfumes/Accessories

### What the log shows
```
16:53:07  WARNING  [INTEGRATION][gnews] skipped  reason=unexpected_response_shape
  query=(Niche and Artisanal OR niche fragrance OR artisan perfume OR indie scent OR niche perfume) ...
```
All 12 perfume queries and all 12 oud-oriental queries returned `unexpected_response_shape` and fetched 0 results.

Also in the first electronics run (queries 4-8):
```
05:12:41  WARNING  ... skipped  reason=unexpected_response_shape
  query=(cell phones OR android phone ...) (news OR launch OR release) (launch OR announced OR release)
```

### Root causes

**Cause A — Category name contains special characters.**
The category name `"Niche & Artisanal"` produces:
```
(Niche & Artisanal OR niche fragrance OR ...)
```
The `&` is **not a valid GNews query operator**. GNews treats this as malformed syntax → returns an unexpected shape (likely an error response body, not an `articles` array).

Similarly `"Oud & Oriental"` → `(Oud & Oriental OR oud fragrance OR ...)` — same issue.

**Cause B — Query too complex for GNews.**
GNews has a simpler query parser than NewsAPI. Three nested OR-blocks like:
```
(Niche & Artisanal OR niche fragrance OR ...) (news OR launch OR release) (launch OR announced OR release)
```
Exceed what GNews reliably processes. The first electronics run queries 4-8 also failed with `unexpected_response_shape` — these were the queries where the expansion OR-block was very long (5 terms).

**Cause C — GNews expansion blocks are too long.**
`SEARCH_KEYWORD_EXPANSIONS["niche-artisanal"]` = `"(niche fragrance OR artisan perfume OR indie scent OR niche perfume)"` — 4 synonyms. Combined with the category name that also goes into the OR block, GNews gets `(Niche & Artisanal OR niche fragrance OR artisan perfume OR indie scent OR niche perfume)` — 5 items in one OR group. GNews supports max ~3 reliable terms per OR group.

### Fixes needed

**Fix A — Strip special characters from category names before query building.**
In `build_query_variants()`, sanitize `category_name` for GNews:
```python
if source == "gnews":
    term = re.sub(r'[&]', 'and', term)  # & → "and"
    term = re.sub(r'[^\w\s\-]', '', term)  # strip other special chars
```

**Fix B — Limit GNews expansion to 2 synonyms.**
In `_MAX_EXPANDED_TERMS`, GNews is already capped at 4. But the OR-block inside each term already contains 4-5 items. Reduce GNews expansion: don't wrap in OR-block at all for GNews — just use the first synonym as a plain term appended separately (which is what non-boolean sources do). But GNews IS in `BOOLEAN_SUPPORTED_SOURCES`, so it wraps. Consider removing GNews from `BOOLEAN_SUPPORTED_SOURCES` or treating it as semi-boolean with max 2 OR terms.

**Fix C — Reduce OR-block size for GNews specifically.**
In `build_query_variants`, limit the expansion to 2 inner terms for GNews:
```python
if source == "gnews":
    inner = " OR ".join(expansion.strip("()").split(" OR ")[:2])
    expanded_terms.append(f"({term} OR {inner})")
```

---

## Issue 3 — YouTube: `403 Forbidden` (First Run) + `etag` Bug (Second Run)

### What the log shows
```
04:53:02  ERROR  [INTEGRATION][youtube] error  err=403 Client Error: Forbidden for url: ...
04:53:03  WARNING  [INTEGRATION][youtube] skipped  reason=quota_exceeded  error=youtube quota exceeded
```
Then at 16:00:
```
16:00:00  ERROR  [FETCH][youtube] error  query="Smartphones review"  err=fetch_youtube_query() got an unexpected keyword argument 'etag'
```

### Root causes

**Cause A — YouTube quota was already exhausted (403 = daily quota reached).**
The `RUN_BUDGET` you set to 1000 units means 10 searches. The first YouTube run at 04:52 hit the quota on the very first query. This means a previous manual test run already consumed the 10,000 unit daily budget. The 403 is YouTube's response when `quotaExceeded`.

The second run at 15:59 worked correctly (80 items stored) — the quota reset at UTC midnight between the two runs.

**Cause B — `etag` kwarg bug (same as NewsAPI).**
`fetch_youtube_query()` doesn't accept an `etag` argument, but the ingestion workflow passes it. Query 1 crashed immediately (2.2s, 0 fetched), queries 2-10 worked because the `etag` bug is intermittent (depends on whether the cooldown lookup returns an etag or not).

### Fixes needed
Same **Fix A** from Issue 1 — the `etag` kwarg should only be passed to RSS fetchers. For NewsAPI/YouTube/Reddit, strip it before calling.

---

## Issue 4 — RSS: Irrelevant Content Being Ingested

### What the log shows
```
04:48:40  INGEST  title="Coros watches get Apple Watch and Garmin-style Voice Control"  ← relevant
04:49:01  INGEST  title="How to watch the 2026 Eurovision Song Contest Grand Final"     ← irrelevant
04:49:06  INGEST  title="NYT Connections hints and answers for Saturday, May 16"        ← irrelevant
04:49:11  INGEST  title="NYT Strands hints and answers for Saturday, May 16"            ← irrelevant
04:49:16  INGEST  title="Quordle hints and answers for Saturday, May 16"                ← irrelevant
04:49:42  INGEST  title="I think therefore I am: cutting-edge AI used to 'revive'"    ← irrelevant
04:50:15  INGEST  title="It's time to ditch your takeout coffee habit"                 ← irrelevant
04:50:25  INGEST  title="How to watch Kyunki Saas Bhi Kabhi Bahu Thi 2"               ← irrelevant
04:50:30  INGEST  title="How to watch Tubi from anywhere"                              ← irrelevant
04:50:34  INGEST  title="How to watch Zee TV outside India"                            ← irrelevant
04:50:39  INGEST  title="How to watch Star Plus outside India"                         ← irrelevant
```
Roughly 50-60% of RSS content from TechRadar is off-topic (gaming guides, puzzle answers, streaming guides, EV articles, coffee makers).

### Root cause
**TechRadar's RSS feed is a general tech feed**, not a gadget/electronics-specific feed. The feed at `https://www.techradar.com/rss` returns ALL TechRadar articles regardless of category. There's no filtering applied — everything from the feed is ingested as-is.

Also **The Verge RSS returned `empty_feed`** (line 31) — the URL resolves but returns no articles, suggesting a bad feed URL.

### Fixes needed

**Fix A — Use category-specific TechRadar feeds.**
TechRadar has section-specific feeds:
- `https://www.techradar.com/phones/rss` (phones only)
- `https://www.techradar.com/laptops/rss`
- `https://www.techradar.com/tablets/rss`

Replace the general `/rss` with specific feeds.

**Fix B — Add a relevance filter in RSS ingestion.**
After fetching, filter items against a set of allowed taxonomy keywords. If title+description shares no overlap with any category keywords, skip it.

**Fix C — Fix The Verge feed URL.**
The correct Verge feed is `https://www.theverge.com/rss/index.xml` (already used, but returning status=200 with empty result). This is The Verge blocking feed scrapers. Replace with `https://www.theverge.com/tech/rss/index.xml` or remove and substitute with another feed.

---

## Issue 5 — Supabase DB Connection Failures (newsapi runs at 16:27, 16:33, 16:42)

### What the log shows
```
16:27:36  ERROR  ... (psycopg2.OperationalError) could not translate host name
  "aws-1-ap-southeast-2.pooler.supabase.com" to address: Name or service not known
16:33:59  ERROR  same
16:42:16  ERROR  same
```
Three consecutive newsapi runs failed immediately with DNS resolution failure. Then at 16:42:53 it worked again.

### Root cause
**Transient DNS/network failure on your machine or ISP**, not a code bug. The Supabase pooler hostname temporarily failed to resolve. This is an infrastructure issue (likely VPN, DNS caching, or brief ISP outage). The fourth attempt at 16:42:53 succeeded, confirming it was transient.

### Fix
Add a **DB connection retry with backoff** in `run_fetcher.py`. When a `psycopg2.OperationalError` occurs at the top level (before any query fires), retry after 30 seconds up to 3 times before giving up:
```python
for attempt in range(3):
    try:
        count = run_orchestrated_ingestion(...)
        break
    except OperationalError:
        if attempt < 2:
            time.sleep(30)
        else:
            raise
```

---

## Issue 6 — Scrape Logs and Route Logs Mixed with Ingestion Logs

### What the log shows
Lines 95-165 and 151-165 mix:
- `[SCRAPE]` enrichment lines
- `[ROUTE][/]` and `[ROUTE][/sections/news]` lines
- `[INGEST][rescrape]` lines

All interleaved in a single `nexora.log` file.

### Why this is a problem
- When debugging ingestion issues, you have to scroll through hundreds of scrape and route lines
- When monitoring route performance, you can't isolate it from ingestion noise
- Scraping is the slowest step (45-90s per article) and its logs dominate the file

### Fix — Separate log files per domain

In your logging configuration (likely `app/core/logging_config.py` or wherever `fileHandler` is set up), add separate file handlers using logger name prefixes:

```python
# ingestion.log — all [FETCH][*] and [INGEST][*] and [DISCOVERY] lines
# enrichment.log — all [SCRAPE] and [INGEST][rescrape] lines  
# routes.log — all [ROUTE][*] lines
# nexora.log — everything (keep as master log)
```

Use a filter per handler based on logger name or message prefix. The loggers are already namespaced by module (`app.application.content.workflows.ingestion`, `app.integrations.content.enrichment`, `app.web.routes.*`), so you can route by logger name:

```python
logging.config.dictConfig({
    "handlers": {
        "ingestion_file": {
            "class": "logging.FileHandler",
            "filename": "logs/ingestion.log",
            "filters": ["ingestion_filter"],
        },
        "enrichment_file": {
            "class": "logging.FileHandler", 
            "filename": "logs/enrichment.log",
            "filters": ["enrichment_filter"],
        },
        "routes_file": {
            "class": "logging.FileHandler",
            "filename": "logs/routes.log", 
            "filters": ["routes_filter"],
        },
    }
})
```

---

## Summary Table

| # | Issue | Severity | Root Cause | Fix |
|---|---|---|---|---|
| 1 | NewsAPI all 429 | 🔴 High | Daily quota exhausted + `etag` kwarg bug | Fix `etag` kwarg; add 1s delay; reduce query complexity |
| 2 | GNews all `unexpected_response_shape` for perfumes | 🔴 High | `&` in category name + OR-block too complex for GNews | Sanitize `&` in names; reduce GNews OR-block to 2 terms |
| 3 | YouTube 403 first run / `etag` second run | 🟡 Medium | Prior quota exhaustion + `etag` kwarg bug | Fix `etag` kwarg; don't manually exhaust quota before runs |
| 4 | RSS ingesting irrelevant content | 🟡 Medium | General TechRadar feed, no relevance filter | Use section-specific feeds; add keyword relevance filter |
| 5 | Supabase DNS failure x3 | 🟢 Low | Transient network issue | Add DB retry with backoff in `run_fetcher.py` |
| 6 | All logs mixed in one file | 🟢 Low | Single file handler | Add per-domain log file handlers |

---

## Priority Fix Order

1. **`etag` kwarg bug** — causes ~30-50% of NewsAPI and YouTube queries to crash silently (Issues 1, 3)
2. **GNews `&` sanitization** — causes 100% failure for all perfume/accessories categories (Issue 2)
3. **GNews OR-block size reduction** — causes `unexpected_response_shape` for complex queries (Issue 2)
4. **RSS feed specificity** — garbage in = garbage out; irrelevant content wastes scraping cycles (Issue 4)
5. **DB retry** — low priority, transient issue (Issue 5)
6. **Log separation** — quality of life improvement (Issue 6)
