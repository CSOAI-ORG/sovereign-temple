"""Formality level detector for CJK and other languages.

Provides heuristics to determine whether user input uses formal or
informal register, enabling polite API responses and guardrail tuning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FormalityLevel(Enum):
    """Discrete formality buckets."""
    FORMAL = "formal"
    INFORMAL = "informal"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FormalityResult:
    """Result of formality detection for a single locale."""
    locale: str
    level: FormalityLevel
    confidence: float  # 0.0–1.0
    triggers: list[str]


# ---------------------------------------------------------------------------
# Chinese (zh)
# ---------------------------------------------------------------------------

_CHINESE_FORMAL_MARKERS = [
    "您", "您好", "请", "谢谢", "对不起", "打扰", "贵公司", "阁下",
]
_CHINESE_INFORMAL_MARKERS = [
    "你", "你好", "干嘛", "呢", "吧", "啦", "哈", "哦",
]


def _detect_chinese(text: str) -> FormalityResult:
    """Detect formality in Chinese text.

    Formal register typically uses 您 (respectful "you")
    while informal uses 你 (casual "you").
    """
    formal_hits = [m for m in _CHINESE_FORMAL_MARKERS if m in text]
    informal_hits = [m for m in _CHINESE_INFORMAL_MARKERS if m in text]

    formal_score = len(formal_hits)
    informal_score = len(informal_hits)

    if formal_score > informal_score:
        level = FormalityLevel.FORMAL
        confidence = min(0.5 + (formal_score - informal_score) * 0.1, 0.95)
        triggers = formal_hits
    elif informal_score > formal_score:
        level = FormalityLevel.INFORMAL
        confidence = min(0.5 + (informal_score - formal_score) * 0.1, 0.95)
        triggers = informal_hits
    else:
        level = FormalityLevel.NEUTRAL
        confidence = 0.5
        triggers = []

    return FormalityResult(locale="zh", level=level, confidence=confidence, triggers=triggers)


# ---------------------------------------------------------------------------
# Korean (ko)
# ---------------------------------------------------------------------------

_KOREAN_FORMAL_ENDINGS = [
    "습니다", "ㅂ니다", "아요", "어요", "해요", "이에요", "예요",
    "시", "으시", "세요", "으세요", "ㄴ가요", "은가요",
]
_KOREAN_INFORMAL_ENDINGS = [
    "아", "어", "야", "이야", "지", "잖아", "거든", "ㄴ다", "는다",
]


def _detect_korean(text: str) -> FormalityResult:
    """Detect formality in Korean text.

    존댓말 (honorifics) vs 반말 (casual speech).
    """
    formal_hits = [e for e in _KOREAN_FORMAL_ENDINGS if e in text]
    informal_hits = [e for e in _KOREAN_INFORMAL_ENDINGS if e in text]

    # Endings are stronger signals than isolated words
    formal_score = len(formal_hits) * 2
    informal_score = len(informal_hits) * 2

    if formal_score > informal_score:
        level = FormalityLevel.FORMAL
        confidence = min(0.55 + (formal_score - informal_score) * 0.08, 0.95)
        triggers = formal_hits
    elif informal_score > formal_score:
        level = FormalityLevel.INFORMAL
        confidence = min(0.55 + (informal_score - formal_score) * 0.08, 0.95)
        triggers = informal_hits
    else:
        level = FormalityLevel.NEUTRAL
        confidence = 0.5
        triggers = []

    return FormalityResult(locale="ko", level=level, confidence=confidence, triggers=triggers)


# ---------------------------------------------------------------------------
# Japanese (ja)
# ---------------------------------------------------------------------------

_JAPANESE_FORMAL_MARKERS = [
    "です", "ます", "ました", "ません", "でしょう", "ましょう",
    "ございます", "いらっしゃい", "お", "拝見", "拝啓",
]
_JAPANESE_INFORMAL_MARKERS = [
    "だ", "である", "だった", "じゃない", "る", "た", "ちゃう",
    "だろ", "かも", "っす", "〜", "～",
]


def _detect_japanese(text: str) -> FormalityResult:
    """Detect formality in Japanese text.

    です/ます (desu/masu) form vs だ/る (da/ru) plain form.
    """
    formal_hits = [m for m in _JAPANESE_FORMAL_MARKERS if m in text]
    informal_hits = [m for m in _JAPANESE_INFORMAL_MARKERS if m in text]

    formal_score = len(formal_hits)
    informal_score = len(informal_hits)

    if formal_score > informal_score:
        level = FormalityLevel.FORMAL
        confidence = min(0.55 + (formal_score - informal_score) * 0.08, 0.95)
        triggers = formal_hits
    elif informal_score > formal_score:
        level = FormalityLevel.INFORMAL
        confidence = min(0.55 + (informal_score - formal_score) * 0.08, 0.95)
        triggers = informal_hits
    else:
        level = FormalityLevel.NEUTRAL
        confidence = 0.5
        triggers = []

    return FormalityResult(locale="ja", level=level, confidence=confidence, triggers=triggers)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_DETECTORS = {
    "zh": _detect_chinese,
    "ko": _detect_korean,
    "ja": _detect_japanese,
}


def detect_formality(text: str, locale: Optional[str] = None) -> FormalityResult:
    """Detect the formality level of *text*.

    If *locale* is provided, the appropriate language-specific detector
    is used.  Otherwise a lightweight script detection heuristic picks
    the detector automatically.

    Args:
        text: Input text to analyse.
        locale: Optional locale tag (e.g. ``zh-Hant``, ``ko-KR``).

    Returns:
        A :class:`FormalityResult` with the inferred level and confidence.
    """
    if not text:
        return FormalityResult(locale=locale or "unknown", level=FormalityLevel.UNKNOWN, confidence=0.0, triggers=[])

    # Auto-detect if locale not given
    if locale is None:
        if any("\u4e00" <= ch <= "\u9fff" for ch in text):
            locale = "zh"
        elif any("\uac00" <= ch <= "\ud7af" for ch in text):
            locale = "ko"
        elif any("\u3040" <= ch <= "\u309f" or "\u30a0" <= ch <= "\u30ff" for ch in text):
            locale = "ja"
        else:
            return FormalityResult(locale="unknown", level=FormalityLevel.UNKNOWN, confidence=0.0, triggers=[])

    base = locale.split("-")[0].split("_")[0].lower()
    detector = _DETECTORS.get(base)
    if detector is None:
        return FormalityResult(locale=locale, level=FormalityLevel.UNKNOWN, confidence=0.0, triggers=[])

    return detector(text)
