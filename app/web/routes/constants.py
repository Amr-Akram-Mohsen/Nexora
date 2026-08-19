"""
Web routes template path constants.
"""
from pathlib import Path

_BASE_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

AUTH_TEMPLATES = str(_BASE_TEMPLATES / "auth")
PUBLIC_TEMPLATES = str(_BASE_TEMPLATES / "public")
