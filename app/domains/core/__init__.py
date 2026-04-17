from app.core.context import get_global_context
from .routes import bp
@bp.app_context_processor
def inject_global_context():
    return get_global_context()

