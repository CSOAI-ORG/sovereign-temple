"""Locale formatters for numbers, dates, and currencies."""
from __future__ import annotations

from datetime import datetime
from typing import Optional


LOCALE_OVERRIDES = {
    "zh-Hant": "zh_TW",
    "zh": "zh_CN",
}


def format_currency(amount: float, locale: str, currency: str = "USD") -> str:
    """Format amount as localized currency string."""
    import locale as loc

    loc_str = LOCALE_OVERRIDES.get(locale, locale)
    try:
        loc.setlocale(loc.LC_ALL, f"{loc_str}.UTF-8")
    except loc.Error:
        pass

    # Custom formatting for currencies without locale support
    symbols = {
        "USD": "$", "CNY": "¥", "KRW": "₩", "JPY": "¥",
        "EUR": "€", "INR": "₹", "RUB": "₽", "IDR": "Rp",
        "VND": "₫", "THB": "฿", "SAR": "﷼",
    }
    symbol = symbols.get(currency, currency)

    if currency in ("JPY", "KRW", "VND", "IDR"):
        return f"{symbol}{int(amount):,}"

    return f"{symbol}{amount:,.4f}"


def format_number(n: float, locale: str = "en") -> str:
    """Format number with locale-appropriate grouping."""
    try:
        import locale as loc
        loc_str = LOCALE_OVERRIDES.get(locale, locale)
        loc.setlocale(loc.LC_ALL, f"{loc_str}.UTF-8")
        return f"{n:n}"
    except Exception:
        return f"{n:,.0f}" if n == int(n) else f"{n:,.4f}"


def format_date(d: datetime, locale: str = "en", fmt: Optional[str] = None) -> str:
    """Format date with locale-appropriate format."""
    if fmt:
        return d.strftime(fmt)

    # Locale-specific defaults
    formats = {
        "en": "%b %d, %Y %H:%M",
        "zh": "%Y年%m月%d日 %H:%M",
        "zh-Hant": "%Y年%m月%d日 %H:%M",
        "ko": "%Y년 %m월 %d일 %H:%M",
        "ja": "%Y年%m月%d日 %H:%M",
        "de": "%d.%m.%Y %H:%M",
        "fr": "%d/%m/%Y %H:%M",
    }
    return d.strftime(formats.get(locale, "%Y-%m-%d %H:%M"))
