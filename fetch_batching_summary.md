# Controlled Fetch Execution — Implementation Walkthrough

## What Changed & Why

### Problem recap
Every fetch command (`fetch-newsapi`, `fetch-gnews`, `fetch-youtube`, `fetch-rss`) was
generating the **full** query universe from the taxonomy on every execution (~100+ queries),
logging nothing until all queries finished, and stopping entirely on the first unexpected error.

### Solution approach
Three focused, minimal changes layered on top of each other:

1. **Centralised limits** — one place to read/change batch sizes  
2. **Taxonomy-group cursor** — round-robin through `electronics → perfumes → accessories`
   so coverage spreads across runs instead of exhausting everything at once  
3. **Progressive logging** — a `[FETCH]` progress line after every single query

---

## Files Changed

### `app/shared/constants/core.py` *(enhanced)*
Added two constants classes:

```python
class FetchLimits:
    NEWSAPI: int = 7    # ~7 API calls / run
    GNEWS:   int = 7    # ~7 API calls / run
    RSS:     int = 8    # 8 feeds / run
    YOUTUBE: int = 10   # 10 queries = 1 000 quota units / run
    REDDIT:  int = 10   # 10 queries / run

class YouTubeQuota:
    UNITS_PER_SEARCH: int = 100
    DAILY_BUDGET:     int = 10_000
    RUN_BUDGET:       int = 1_000   # hard per-run cap
```

> **To change a limit** — edit only this file. Every fetch command picks it up automatically.

---

### `app/shared/utils/batch_state.py` *(new)*
Lightweight JSON-file cursor. Stored at `instance/cache/batch_state/<source>_batch.json`.

**How it works:**

| Run | Active group   | Cursor after run |
|-----|---------------|-----------------|
| 1   | `electronics` | → `perfumes`    |
| 2   | `perfumes`    | → `accessories` |
| 3   | `accessories` | → `electronics` |
| 4   | `electronics` | …               |

- No external dependencies — pure stdlib `json` + `pathlib`
- Survives process restarts
- Falls back gracefully if the file is corrupt or unreadable
- Can be reset manually: `BatchState("newsapi").reset()`

---

### `app/shared/utils/logging.py` *(enhanced)*
Three new helpers appended:

| Helper | Output |
|--------|--------|
| `log_fetch_query_start` | `[FETCH][newsapi] start  query="AI news"  group=electronics` |
| `log_fetch_progress` | `[FETCH][newsapi] progress  query="AI news"  completed=3/7  stored=5  group=electronics` |
| `log_fetch_query_error` | `[FETCH][newsapi] error  query="AI news"  type=RequestException  message=…` |

---

### `app/application/content/ingestion_workflow.py` *(rewritten)*
All existing behaviour is preserved; the additions are:

1. **Group filtering** (lines ~85-110)  
   After building `flat_tasks`, filters to only tasks whose `category` slug
   matches the `BatchState.current_group()` value.  Falls back to full task list
   if a group yields zero queries (e.g. "perfumes" for some sources).

2. **`log_fetch_query_start`** called *before* each query.

3. **`_process_query()` extracted** — one query runs fully isolated.
   Any unexpected exception is caught, logged via `log_fetch_query_error`,
   and the loop continues to the next query.  
   `PipelineFatalError` and `PipelineQuotaExceededError` still bubble up and stop the run.

4. **`log_fetch_progress`** called *after* every query with `completed=X/Y` and
   the number of items stored by that query.

5. **Cursor advanced** at the end of every successful run via `batch_state.advance()`.

---

### `app/application/content/ingestion/services.py` *(enhanced)*
`YouTubeQuotaService` now tracks **per-run unit consumption**:

```python
class YouTubeQuotaService(QuotaPort):
    def __init__(self):
        self._units_used = 0           # resets each run (instance per run)

    def can_call(self):
        # global quota check AND run-budget check
        remaining = YouTubeQuota.RUN_BUDGET - self._units_used
        return remaining >= YouTubeQuota.UNITS_PER_SEARCH

    def record_call(self):
        self._units_used += YouTubeQuota.UNITS_PER_SEARCH
```

Default: 10 calls × 100 units = **1 000 units / run** (10 % of daily budget).

---

### `app/jobs/tasks/content/articles.py` *(updated)*
- `run_newsapi_fetch(limit=FetchLimits.NEWSAPI, …)` — default 7
- `run_gnews_fetch(limit=FetchLimits.GNEWS, …)` — default 7
- `run_rss_fetch(limit=FetchLimits.RSS, …)` — default 8
- Log prefix changed to `[FETCH][source]` for consistency

### `app/jobs/tasks/content/videos.py` *(updated)*
- `run_youtube_fetch(limit=FetchLimits.YOUTUBE)` — default 10

### `app/jobs/tasks/content/posts.py` *(updated)*
- `run_reddit_fetch(limit=FetchLimits.REDDIT)` — default 10

### `app/jobs/tasks/content/all_contents.py` *(updated)*
- Mode banner now shows per-source defaults when `limit=None`
- `limit=None` → each source uses its own `FetchLimits` default
- `limit=N` → overrides all sources (useful for smoke tests)

---

## Log Output — Before vs After

### Before
```
[Runner] Starting NewsAPI  should_scrape=False
[Runner] NewsAPI done  stored=47
```

### After
```
[FETCH][newsapi] run started  limit=7  should_scrape=False
[FETCH][newsapi] batch group=electronics  group_queries=12  total_available=98
[FETCH][newsapi] run started  tasks=7  group=electronics  limit=7
[FETCH][newsapi] start  query="Smartphones AND news"  group=electronics
[INTEGRATION][newsapi] start  query="Smartphones AND news"
[INTEGRATION][newsapi] success  items=15  query="Smartphones AND news"
[FETCH][newsapi] stored  title="Apple iPhone 17 launch…"
[FETCH][newsapi] stored  title="Samsung Galaxy S25 review…"
[FETCH][newsapi] progress  query="Smartphones AND news"  completed=1/7  stored=3  group=electronics
[FETCH][newsapi] start  query="Samsung AND news"  group=electronics
…
[FETCH][newsapi] progress  query="Cameras AND news"  completed=7/7  stored=2  group=electronics
[BATCH][newsapi] cursor advanced  next_group=perfumes
[FETCH][newsapi] run complete  completed=7/7  total_stored=18  group=electronics
[FETCH][newsapi] run done  total_stored=18
```

---

## Tuning

| What | Where | How |
|------|-------|-----|
| Change batch size | `app/shared/constants/core.py` | Edit `FetchLimits.NEWSAPI` etc. |
| Change YouTube run budget | `app/shared/constants/core.py` | Edit `YouTubeQuota.RUN_BUDGET` |
| One-off override | Call site / CLI | `run_newsapi_fetch(limit=3)` |
| Disable batching | Call site | `run_newsapi_fetch(limit=None)` |
| Reset group cursor | Python shell | `BatchState("newsapi").reset()` |
| Check cursor state | `instance/cache/batch_state/` | Inspect `<source>_batch.json` |

---

## Constraints Respected

- ✅ No Celery, no queues, no distributed workers
- ✅ Existing command names unchanged
- ✅ All existing `run_orchestrated_ingestion()` call-sites still work
- ✅ `PipelineFatalError` / `PipelineQuotaExceededError` still propagate correctly
- ✅ DB rollback on per-query failure (loop continues)
- ✅ Batch cursor state survives restarts (JSON file)
- ✅ Pure stdlib for batch state — zero new dependencies
