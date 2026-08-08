"""
Admitad affiliate network deeplink generator for AliExpress product links.
"""
from __future__ import annotations

import logging
import urllib.parse
from typing import Optional

logger = logging.getLogger("commercial.affiliate.admitad")

# Default Admitad target / campaign URL prefix fallback
_DEFAULT_ADMITAD_BASE = "https://ad.admitad.com/g/"


def generate_admitad_affiliate_url(
    original_url: str,
    website_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    subid: Optional[str] = None,
) -> str:
    """
    Construct an Admitad affiliate deeplink from an original product URL.
    """
    if not original_url:
        return ""

    encoded_url = urllib.parse.quote(original_url, safe="")

    if campaign_id:
        base = f"https://ad.admitad.com/g/{campaign_id}/"
    else:
        # Generic fallback
        base = _DEFAULT_ADMITAD_BASE

    query_params = {"ulp": original_url}
    if subid:
        query_params["subid"] = subid

    affiliate_url = f"{base}?{urllib.parse.urlencode(query_params)}"
    logger.debug("[Admitad] Generated affiliate URL: %s", affiliate_url)
    return affiliate_url
