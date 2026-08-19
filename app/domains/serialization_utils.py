from typing import Dict, Any, Optional
from datetime import datetime

def compact_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively removes keys where the value is None, an empty string (""), or an empty list ([]).
    Kept values are returned in a new dictionary.
    """
    if not isinstance(d, dict):
        return d
        
    compacted = {}
    for k, v in d.items():
        if v is None or v == "" or v == []:
            continue
            
        if isinstance(v, dict):
            compacted_v = compact_dict(v)
            if compacted_v or v == {}:
                compacted[k] = compacted_v
        elif isinstance(v, list):
            compacted_list = [
                compact_dict(item) if isinstance(item, dict) else item
                for item in v
            ]
            if compacted_list:
                compacted[k] = compacted_list
        else:
            compacted[k] = v
            
    return compacted

def safe_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    """Safely gets an attribute from an object, returning default if obj is None or attr is missing/None."""
    if obj is None:
        return default
    
    if isinstance(obj, dict):
        val = obj.get(attr_name, default)
    else:
        val = getattr(obj, attr_name, default)
        
    return val if val is not None else default

def safe_float(obj: Any, attr_name: str, default: Optional[float] = None) -> Optional[float]:
    """Safely gets an attribute and converts it to float, handling None and type errors."""
    val = safe_attr(obj, attr_name)
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_isoformat(obj: Any, attr_name: str) -> Optional[str]:
    """Safely gets a datetime attribute and returns its ISO format string."""
    val = safe_attr(obj, attr_name)
    if not val:
        return None
    try:
        return val.isoformat()
    except AttributeError:
        return None


def serialize_model(m: Any) -> Optional[Dict[str, Any]]:
    """Serializes model name and slug cleanly."""
    if not m:
        return None
    return compact_dict({
        "name": getattr(m, "name", None),
        "slug": getattr(m, "slug", None),
    })

