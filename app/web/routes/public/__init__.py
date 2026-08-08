from pathlib import Path

PUBLIC_TEMPLATES = str(Path(__file__).resolve().parent.parent.parent / "templates" / "public")

from .system import bp as system_bp
from .content import bp as content_bp
from .product import bp as item_bp
from .interaction import bp as interaction_bp
from .recommendation import bp as recommendation_bp
from .suggestions import bp as suggestions_bp
