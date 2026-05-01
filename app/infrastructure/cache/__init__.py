from app.core.extensions import cache

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
