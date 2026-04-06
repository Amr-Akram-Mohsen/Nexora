# app/routes/__init__.py
from flask import Blueprint
from app.helpers.context import get_global_context

# 1. Define the blueprint
bp = Blueprint('main', __name__, static_folder='../static')

# 2. Add your global context processor
@bp.app_context_processor
def inject_global_context():
    return get_global_context()

# 3. Import all the split files (must be at the bottom to avoid circular imports)
from . import auth, base, catalog, interactions, temp_fetch