"""i18n Translation Coverage Tests

Ensures every translation key has a value in every locale.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Set

import pytest

MESSAGES_DIR = os.path.join(os.path.dirname(__file__), "../../meokclaw-v2/messages")


def _load_messages(locale: str) -> Dict:
    path = os.path.join(MESSAGES_DIR, f"{locale}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _flatten(d: Dict, parent: str = "") -> Set[str]:
    keys = set()
    for k, v in d.items():
        full_key = f"{parent}.{k}" if parent else k
        if isinstance(v, dict):
            keys.update(_flatten(v, full_key))
        else:
            keys.add(full_key)
    return keys


LOCALES = ["en", "zh", "zh-Hant", "ko", "ja", "es", "pt", "ar", "hi", "fr", "de", "ru", "id", "vi", "th"]


class TestTranslationCoverage:
    def test_all_locales_have_same_keys(self):
        """Every locale must have the same keys as the English master."""
        en_keys = _flatten(_load_messages("en"))

        for locale in LOCALES:
            if locale == "en":
                continue
            locale_keys = _flatten(_load_messages(locale))
            missing = en_keys - locale_keys
            extra = locale_keys - en_keys
            assert not missing, f"{locale} missing keys: {missing}"
            assert not extra, f"{locale} has extra keys: {extra}"

    def test_no_empty_translations(self):
        """No translation value should be empty."""
        for locale in LOCALES:
            messages = _load_messages(locale)
            flat = _flatten(messages)
            # We can't easily check values with the flatten approach, so reload
            for key in flat:
                parts = key.split(".")
                d = messages
                for p in parts:
                    d = d[p]
                assert d and isinstance(d, str) and d.strip(), f"{locale}.{key} is empty"

    def test_rtl_locale_has_dir_rtl(self):
        """Arabic must be marked as RTL."""
        from meokclaw_v2.src.i18n.config import LOCALE_METADATA
        assert LOCALE_METADATA["ar"]["dir"] == "rtl"

    def test_chinese_font_family(self):
        """Chinese locales should use Chinese font family."""
        from meokclaw_v2.src.i18n.config import LOCALE_METADATA
        assert "chinese" in LOCALE_METADATA["zh"]["fontFamily"]
        assert "chinese" in LOCALE_METADATA["zh-Hant"]["fontFamily"]

    def test_currency_symbols(self):
        """Each locale should have the correct currency symbol."""
        from meokclaw_v2.src.i18n.config import LOCALE_METADATA
        assert LOCALE_METADATA["zh"]["currencySymbol"] == "¥"
        assert LOCALE_METADATA["ko"]["currencySymbol"] == "₩"
        assert LOCALE_METADATA["ja"]["currencySymbol"] == "¥"
        assert LOCALE_METADATA["ar"]["currencySymbol"] == "﷼"
        assert LOCALE_METADATA["hi"]["currencySymbol"] == "₹"
