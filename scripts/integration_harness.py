"""
Integration harness for Nexora (CORE baseline).
- Runs inside Flask app context (uses app/core.create_app)
- Uses DiscoveryManager to build q_obj for news/youtube/reddit
- Picks an RSS feed for rss fetcher
- Calls integration fetchers named like `fetch_<name>_query` when present
- Produces envelope fixtures under tests/integration/fixtures/<module>/
- Performs minimal validation using app.shared.dto.ingestion.RawItemDTO
"""

import os
import time
import json
import hashlib
import importlib
import traceback
from datetime import datetime
from pathlib import Path
import argparse

# Flask app factory
from app.core import create_app
from app.integrations.discovery import DiscoveryManager
from app.integrations.exceptions import PipelineQuotaExceededError
from app.shared.dto.ingestion import RawItemDTO

# Default modules to exercise (adjustable via --modules)
DEFAULT_MODULES = [
    "app.integrations.content.gnews",
    "app.integrations.content.newsapi",
    "app.integrations.content.rss",
    "app.integrations.social.youtube",
    "app.integrations.social.reddit",
    "app.integrations.content.article_utils.extractor_clients",
]

SAMPLE_PARAMS = {"query": "technology", "region": "SA", "language": "en"}
EXCERPT_SIZE = 2048
MAX_SAMPLE_ITEMS = 8

def sha1_of(obj):
    try:
        s = json.dumps(obj, default=lambda o: str(o), sort_keys=True)
    except Exception:
        s = repr(obj)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def mask_params(params):
    out = {}
    for k, v in (params or {}).items():
        kl = k.lower()
        if any(s in kl for s in ("key", "secret", "token", "password")):
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out

def find_fetch_fn(module):
    # prefer explicit fetch_<name>_query if present
    short = module.__name__.split(".")[-1]
    candidates = [
        f"fetch_{short}_query",
        "fetch_query",
        "fetch",
        "search",
        "get_feed",
        "extract_with_apis",
        "run",
    ]
    for name in candidates:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    # fallback: first callable defined in module
    for name in dir(module):
        attr = getattr(module, name)
        if callable(attr) and getattr(attr, "__module__", "") == module.__name__:
            return attr
    return None

def items_to_plain(items):
    out = []
    for it in items:
        try:
            if hasattr(it, "model_dump"):
                out.append(it.model_dump())
            elif hasattr(it, "dict"):
                out.append(it.dict())
            elif isinstance(it, dict):
                out.append(it)
            else:
                # try __dict__ then str fallback
                out.append(getattr(it, "__dict__", str(it)))
        except Exception:
            out.append(str(it))
    return out

def minimal_validate_item(item):
    # Ensure at least platform, and one of external_id/url, and one of title/description/content/content_text
    reasons = []
    if not item.get("platform"):
        reasons.append("missing platform")
    if not (item.get("external_id") or item.get("url")):
        reasons.append("missing external_id and url")
    if not (item.get("title") or item.get("description") or item.get("content") or item.get("content_text")):
        reasons.append("missing title/description/content")
    return reasons

def pick_query_for_source(discovery, source_filter):
    try:
        registry = discovery.get_queries_by_section(source_filter=source_filter)
        for sec, cats in registry.items():
            for cat, queries in cats.items():
                if queries:
                    q = queries[0]
                    # add region/language defaults if absent
                    q.setdefault("region", SAMPLE_PARAMS["region"])
                    q.setdefault("language", SAMPLE_PARAMS["language"])
                    return q
    except Exception:
        pass
    # fallback
    return {"query": SAMPLE_PARAMS["query"], "region": SAMPLE_PARAMS["region"], "language": SAMPLE_PARAMS["language"]}

def pick_rss_feed(module):
    # try to read module.RSS_FEEDS
    feeds = getattr(module, "RSS_FEEDS", None)
    if not feeds:
        return None
    # prefer 'news' section
    for sec in ("news", "reviews"):
        if sec in feeds:
            for cat, urls in feeds[sec].items():
                if urls:
                    return urls[0]
    # fallback first available
    for sec, cats in feeds.items():
        for cat, urls in cats.items():
            if urls:
                return urls[0]
    return None

def run_one(module_name, out_dir, discovery, app, extra_urls=None):
    mod_res = {
        "integration": module_name,
        "ok": False,
        "items_count": 0,
        "items_sample": [],
        "validation_failures": [],
        "error": None,
        "meta": {},
        "params": {},
    }

    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        mod_res["error"] = {"type": "import_error", "message": str(e)}
        return mod_res

    # decide source_filter for discovery-based queries
    short = module_name.split(".")[-1]
    source_filter = short  # works for gnews, newsapi, youtube, reddit
    fn = find_fetch_fn(module)
    if not fn:
        mod_res["error"] = {"type": "no_callable", "message": f"No callable fetcher found in {module_name}"}
        return mod_res

    # construct q_obj
    q_obj = None
    if "rss" in module_name:
        feed = pick_rss_feed(module)
        if feed:
            q_obj = {"query": feed}
        else:
            q_obj = {"query": SAMPLE_PARAMS["query"]}
    elif "extractor_clients" in module_name:
        # extractor requires a URL - use provided extra_urls or skip
        if extra_urls:
            # will call extract_with_apis per URL below
            pass
        else:
            mod_res["error"] = {"type": "skipped", "message": "no sample URLs provided for extractor"}
            return mod_res
    else:
        q_obj = pick_query_for_source(discovery, source_filter)

    # maskable params
    params = {"region": q_obj.get("region"), "language": q_obj.get("language")}
    mod_res["params"] = mask_params(params)

    # run timing + call
    start = time.time()
    try:
        results = []
        if "extractor_clients" in module_name:
            # call extract_with_apis for each sample url
            for url in (extra_urls or []):
                res = fn(url)
                if res:
                    results.append(res)
        else:
            # typical signature: fn(q_obj, **params)
            try:
                res = fn(q_obj, **params)
            except TypeError:
                # try zero-arg or single-arg
                try:
                    res = fn(q_obj)
                except TypeError:
                    res = fn()
            results = res

        duration_ms = int((time.time() - start) * 1000)
        mod_res["meta"]["duration_ms"] = duration_ms

        # normalize results -> list
        if results is None:
            items = []
        elif isinstance(results, (list, tuple)):
            items = list(results)
        elif isinstance(results, dict):
            # try to find items container
            for key in ("items", "articles", "data", "results"):
                if key in results and isinstance(results[key], (list, tuple)):
                    items = list(results[key]); break
            else:
                items = [results]
        else:
            # single object
            items = [results]

        plain_items = items_to_plain(items)
        mod_res["items_count"] = len(plain_items)
        mod_res["items_sample"] = plain_items[:MAX_SAMPLE_ITEMS]
        mod_res["meta"]["sample_hash"] = sha1_of(mod_res["items_sample"])

        # minimal validation
        failures = []
        for idx, it in enumerate(plain_items):
            reasons = minimal_validate_item(it)
            if reasons:
                failures.append({"index": idx, "reasons": reasons, "title": it.get("title") if isinstance(it, dict) else str(it)[:100]})
        mod_res["validation_failures"] = failures

        mod_res["ok"] = True
        return mod_res

    except PipelineQuotaExceededError as e:
        mod_res["error"] = {"type": "quota_exceeded", "message": str(e)}
        mod_res["meta"]["duration_ms"] = int((time.time() - start) * 1000)
        return mod_res
    except Exception as e:
        mod_res["error"] = {"type": "call_error", "message": str(e), "trace": traceback.format_exc()}
        mod_res["meta"]["duration_ms"] = int((time.time() - start) * 1000)
        return mod_res

def write_fixture(out_dir, module_name, data):
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    sub = Path(out_dir) / module_name.replace(".", "/")
    sub.mkdir(parents=True, exist_ok=True)
    path = sub / f"{module_name.split('.')[-1]}-{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=lambda o: str(o))
    return str(path)

def main(args):
    fixtures_dir = Path(args.output)
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    modules = args.modules or DEFAULT_MODULES
    sample_urls = args.urls or []

    app = create_app()
    with app.app_context():
        discovery = DiscoveryManager()
        results = []
        for m in modules:
            # skip reddit if keys missing
            if "reddit" in m:
                if not (app.config.get("REDDIT_CLIENT_ID") and app.config.get("REDDIT_CLIENT_SECRET")):
                    print(f"[harness] skipping reddit ({m}) - credentials not present")
                    res = {"integration": m, "ok": False, "error": {"type": "skipped", "message": "no reddit credentials in config"}}
                    path = write_fixture(fixtures_dir, m, res)
                    print(f"  => fixture={path}")
                    results.append(res)
                    continue

            print(f"[harness] running {m} ...", flush=True)
            res = run_one(m, fixtures_dir, discovery, app, extra_urls=sample_urls)
            path = write_fixture(fixtures_dir, m, res)
            print(f"  => ok={res.get('ok')} items={res.get('items_count')} fixture={path}")
            if res.get("error"):
                print("   error:", res["error"].get("message"))
            results.append(res)

        # write summary
        summary_path = fixtures_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({"generated": len(results), "results": results}, f, indent=2, default=lambda o: str(o))
        print(f"[harness] summary written to {summary_path}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="tests/integration/fixtures", help="fixtures output dir")
    p.add_argument("--modules", nargs="*", help="integration modules (dot paths)")
    p.add_argument("--urls", nargs="*", help="sample article URLs (for extractor)")
    args = p.parse_args()
    main(args)