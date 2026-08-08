"""
Validation module for ParsedProduct instances before database insertion.

Ensures products meet mandatory field criteria to prevent inserting incomplete or corrupt data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from app.integrations.commercial.schema import ParsedProduct

logger = logging.getLogger("commercial.validation")


@dataclass
class ValidationResult:
    """Result of ParsedProduct validation."""
    is_valid: bool
    is_partial: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_parsed_product(parsed: ParsedProduct) -> ValidationResult:
    """
    Validate a ParsedProduct instance before committing it to the database.

    Fatal errors block insertion; warnings are logged but permit insertion.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not parsed:
        return ValidationResult(is_valid=False, errors=["ParsedProduct is None"])

    # Mandatory checks
    if not parsed.name or not parsed.name.strip():
        errors.append("Product name is empty or missing")

    if not parsed.variants:
        errors.append("Product has no variants")
    else:
        has_any_price = any(v.price is not None for v in parsed.variants)
        if not has_any_price and (not parsed.store_link or parsed.store_link.price is None):
            errors.append("No price available on product or any variant")

    if not parsed.store_link:
        errors.append("Missing store_link object")
    else:
        if not parsed.store_link.store_slug:
            errors.append("store_link.store_slug is missing")
        if not parsed.store_link.original_url:
            errors.append("store_link.original_url is missing")

    # Non-fatal warning checks
    if not parsed.images:
        warnings.append("Product has no images")

    if not parsed.brand_name:
        warnings.append("Product brand name is missing")

    if not parsed.category_name:
        warnings.append("Product category name is missing")

    if not parsed.specifications:
        warnings.append("Product has no specifications")

    is_valid = len(errors) == 0
    is_partial = len(warnings) > 0

    if not is_valid:
        logger.warning("[Validation] Validation failed for '%s': %s", parsed.name, errors)
    elif is_partial:
        logger.info("[Validation] Validation passed with warnings for '%s': %s", parsed.name, warnings)

    return ValidationResult(
        is_valid=is_valid,
        is_partial=is_partial,
        errors=errors,
        warnings=warnings,
    )
