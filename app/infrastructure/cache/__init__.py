from app.core.extensions import cache

_ITERABLE_FILTER_TYPES = (list, tuple, set)

def memoize(timeout=300):
    """
    Decorator to cache the result of a function with arguments.
    Use this for domain services and application workflows.
    """
    return cache.memoize(timeout=timeout)

def cached(timeout=300, key_prefix='view'):
    """
    Decorator to cache a function without arguments or a whole view.
    """
    return cache.cached(timeout=timeout, key_prefix=key_prefix)

def get(key):
    """Retrieve a value from the cache."""
    return cache.get(key)

def set(key, value, timeout=300):
    """Store a value in the cache."""
    return cache.set(key, value, timeout=timeout)

def delete(key):
    """Remove a value from the cache."""
    return cache.delete(key)

def clear():
    """Clear the entire cache."""
    return cache.clear()


def delete_memoized(fn, *args, **kwargs):
    """Invalidate a single memoized function result (optionally scoped by args)."""
    return cache.delete_memoized(fn, *args, **kwargs)


def normalize_filters(filters):
    """Return a stable tuple representation for cache keys and memoized args."""
    if not filters:
        return ()

    normalized = []
    for key, value in sorted(filters.items()):
        if value is None or value == "":
            continue
        if isinstance(value, _ITERABLE_FILTER_TYPES):
            values = tuple(sorted(str(v).strip() for v in value if str(v).strip()))
            if values:
                normalized.append((key, values))
        else:
            normalized.append((key, str(value).strip()))

    return tuple(normalized)


def filters_from_normalized(normalized):
    """Rebuild a filter dict from normalize_filters output."""
    return {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in normalized
    }
