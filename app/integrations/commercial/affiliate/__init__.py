"""
Commercial Affiliate Workflow Package.
"""
from __future__ import annotations

from app.integrations.commercial.affiliate.admitad import generate_admitad_affiliate_url
from app.integrations.commercial.affiliate.workflow import generate_affiliate_links_for_store

__all__ = [
    "generate_admitad_affiliate_url",
    "generate_affiliate_links_for_store",
]
