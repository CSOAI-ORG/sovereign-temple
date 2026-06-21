"""Backend i18n — Locale-aware message resolver for MEOKCLAW FastAPI.

Usage:
    from backend.i18n import get_message, format_currency
    msg = get_message("errors.guardrailsBlocked", locale="zh")
    price = format_currency(0.0025, locale="zh", currency="CNY")
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

# Load all message catalogs
_CATALOGS: Dict[str, Dict[str, Any]] = {}


def _load_catalogs():
    global _CATALOGS
    if _CATALOGS:
        return

    catalog_dir = os.path.join(os.path.dirname(__file__), "catalogs")
    for fname in os.listdir(catalog_dir):
        if fname.endswith(".json"):
            locale = fname.replace(".json", "")
            with open(os.path.join(catalog_dir, fname), "r", encoding="utf-8") as f:
                _CATALOGS[locale] = json.load(f)


def get_message(key: str, locale: str = "en", **kwargs) -> str:
    """Get a localized message by key, with fallback chain.

    Fallback: requested locale → base locale (zh-Hant → zh) → en
    """
    _load_catalogs()

    # Build fallback chain
    fallbacks = [locale]
    if "-" in locale:
        fallbacks.append(locale.split("-")[0])
    fallbacks.append("en")

    for loc in fallbacks:
        catalog = _CATALOGS.get(loc, {})
        value = _get_nested(catalog, key)
        if value is not None:
            try:
                return value.format(**kwargs)
            except (KeyError, IndexError):
                return value

    return key  # Return key itself as last resort


def _get_nested(d: Dict, key: str) -> Optional[Any]:
    parts = key.split(".")
    for part in parts:
        if isinstance(d, dict) and part in d:
            d = d[part]
        else:
            return None
    return d


def get_locale_from_request(accept_language: Optional[str] = "en") -> str:
    """Parse Accept-Language header and return best matching locale."""
    if not accept_language:
        return "en"

    # Simple parsing — production would use proper BCP47 negotiation
    supported = {"en", "zh", "zh-Hant", "ko", "ja", "es", "pt", "ar", "hi", "fr", "de", "ru", "id", "vi", "th"}

    for part in accept_language.split(","):
        lang = part.split(";")[0].strip()
        if lang in supported:
            return lang
        base = lang.split("-")[0]
        if base in supported:
            return base

    return "en"


# Re-export formatters
from .formatters import format_currency, format_number, format_date

__all__ = ["get_message", "get_locale_from_request", "format_currency", "format_number", "format_date"]
