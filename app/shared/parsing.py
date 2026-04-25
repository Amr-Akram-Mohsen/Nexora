from app.shared.constants.core import TargetType
from app.domains.interaction.constants import INTERACTION_TYPE

def parse_target_type(value: str) -> str:
    if value not in (TargetType.ARTICLE, TargetType.ITEM):
        raise ValueError("Invalid target type")
    return value

def parse_interaction_type(value: str) -> str:
    if value not in (INTERACTION_TYPE.REACT, INTERACTION_TYPE.SAVE, INTERACTION_TYPE.COMMENT):
        raise ValueError("Invalid interaction type")
    return value

def safe_float(value, default=None):
    """Safely parse a float from a string; returns default if invalid."""
    try:
        return float(value) if value is not None and str(value).strip() else default
    except (ValueError, TypeError):
        return default
