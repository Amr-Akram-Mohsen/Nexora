from pathlib import Path

AUTH_TEMPLATES = str(Path(__file__).resolve().parent.parent.parent / "templates" / "auth")

from .user import bp as user_bp
