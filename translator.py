#!/usr/bin/env python3
"""
Language & Translation - Jarvis can translate in real-time
"""

import requests
from typing import Optional, Dict


class Translator:
    """Real-time translation using free APIs"""

    def __init__(self):
        self.cache = {}

    def detect_language(self, text: str) -> str:
        """Detect language of text"""
        # Simple heuristic detection
        import re

        # Check for common patterns
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh"
        if re.search(r"[\u0600-\u06ff]", text):
            return "ar"
        if re.search(r"[\u0400-\u04ff]", text):
            return "ru"
        if re.search(r"[\u0900-\u097f]", text):
            return "hi"
        if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
            return "ja"
        if re.search(r"[\uac00-\ud7af]", text):
            return "ko"

        # Check for common English words
        english_words = ["the", "is", "are", "and", "or", "but", "hello", "good", "bad"]
        words = text.lower().split()
        english_count = sum(1 for w in words if w in english_words)

        if english_count > len(words) * 0.2:
            return "en"

        return "unknown"

    def translate(
        self, text: str, to_lang: str = "en", from_lang: Optional[str] = None
    ) -> str:
        """Translate text"""
        if not from_lang:
            from_lang = self.detect_language(text)

        if from_lang == to_lang:
            return text

        # Check cache
        key = f"{text[:30]}:{from_lang}:{to_lang}"
        if key in self.cache:
            return self.cache[key]

        try:
            # Use LibreTranslate (free, self-hostable)
            # Fallback to Google Translate web scraping
            url = f"https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": from_lang,
                "tl": to_lang,
                "dt": "t",
                "q": text,
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and data[0]:
                    translated = "".join([item[0] for item in data[0] if item[0]])
                    self.cache[key] = translated
                    return translated
        except:
            pass

        return text

    def translate_to_english(self, text: str) -> str:
        """Translate to English"""
        lang = self.detect_language(text)
        if lang == "en":
            return text
        return self.translate(text, "en", lang)

    def translate_from_english(self, text: str, target_lang: str) -> str:
        """Translate from English"""
        return self.translate(text, target_lang, "en")


# Global instance
_translator = None


def get_translator() -> Translator:
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator


# Quick translation commands
def quick_translate(text: str) -> str:
    """Handle translation requests"""
    translator = get_translator()
    lang = translator.detect_language(text)

    if lang == "en":
        # User speaking English, might want translation OUT
        return None

    # Translate to English
    translated = translator.translate_to_english(text)
    return f"Sir, you said: {translated}"


def translate_phrase(phrase: str, target: str) -> str:
    """Translate phrase to target language"""
    translator = get_translator()
    result = translator.translate_from_english(phrase, target)
    return result


if __name__ == "__main__":
    t = Translator()
    print("Language detection test:")
    print(f"  'Hello world' -> {t.detect_language('Hello world')}")
    print(f"  '你好世界' -> {t.detect_language('你好世界')}")
    print(f"  'Bonjour monde' -> {t.detect_language('Bonjour monde')}")
