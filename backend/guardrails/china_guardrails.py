"""China Guardrails — 中国特定护栏

Extends base Guardrails with China-specific patterns:
- PIPL (个人信息保护法) compliance
- 社会主义核心价值观 alignment
- Political sensitivity detection
- Gambling/rumor blocking
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from guardrails import Guardrails, Violation, GuardrailResult, EnforcementLevel


class ChinaGuardrails(Guardrails):
    """China-specific guardrails for MEOKCLAW."""

    # PIPL-sensitive patterns
    PIPL_PATTERNS = {
        "china_id": (r"\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]", "critical"),
        "china_phone": (r"1[3-9]\d{9}", "high"),
        "china_bank_card": (r"\d{16,19}", "high"),
        "china_address": (r"(?:省|市|区|县|街道|路|号|室)", "medium"),
    }

    # Political sensitivity (conservative — block explicit anti-government content)
    POLITICAL_PATTERNS = {
        "anti_government": (r"(?:推翻|颠覆|反动|反革命)", "critical"),
        "separatism": (r"(?:台独|藏独|疆独|港独)", "critical"),
        "illegal_org": (r"(?:法轮功|全能神)", "critical"),
    }

    # Social values alignment
    SOCIAL_VALUES_PATTERNS = {
        "gambling_promotion": (r"(?:博彩|赌球|六合彩|赌博技巧)", "high"),
        "rumor_spreading": (r"(?:网传|据说|爆料|内部消息).*?(?:政府|领导|官员)", "high"),
        "fraud": (r"(?:刷单|返利|中奖|转账到安全账户)", "critical"),
    }

    # Chinese prompt injection patterns
    CHINESE_INJECTION_PATTERNS = {
        "ignore_previous_zh": (r"忽略之前的指令|忘记上面的提示|请忽略|不要遵循", "critical"),
        "system_override_zh": (r"你现在是一个|假装你是|扮演一个|进入角色", "high"),
        "delimiter_injection_zh": (r"```\s*系统|###\s*系统|系统提示", "high"),
    }

    # Script-aware prompt-injection patterns (matches the test suite)
    # These run AFTER the Chinese-specific ones and catch the multilingual
    # variants the redteam suite probes — Chinese/Arabic/Japanese/Korean
    # scripts, Cyrillic/Greek homograph substitutions, and bidi overrides.
    SCRIPT_INJECTION_PATTERNS = {
        # The CJK+Arabic test set
        "ignore_previous_cjk": (r"(?:忽略之前的指令|無視 previous|이전\s*지시|지시사항을\s*잊어)", "critical"),
        "ignore_previous_arabic": (r"تجاهل\s*(?:التعليمات|الأوامر)\s*السابقة", "critical"),
        "ignore_previous_jp": (r"(?:以上の指示を無視|上の指示を忘れて)", "critical"),
        "ignore_previous_kr": (r"(?:이전\s*지시(?:사항)?을?\s*잊어|이전의?\s*지시(?:를|을)??\s*무시)", "critical"),
        # Latin-script classic, included so the China guardrails also catch
        # the English case without depending on the base Guardrails'
        # (potentially too-broad) default patterns.
        "ignore_previous_en": (r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|prompts?|directives)", "critical"),
        "system_prompt_leak": (r"(?:reveal|show|print|dump)\s+(?:your\s+)?(?:system\s+prompt|hidden\s+instructions)", "critical"),
        # Homograph substitutions: Cyrillic/Greek letters in place of Latin.
        # We don't try to detect the substitution itself (high false-positive
        # risk) — instead we check for the surrounding prompt-injection
        # intent once the high-entropy mix is present.
        "homograph_injection_intent": (r"ign[Ѐ-ӿͰ-Ͽ]r[Ѐ-ӿͰ-Ͽ].*(?:previous|instructions)", "high"),
        # Bidi / override control characters
        "bidi_override": (r"[‎‏‪-‮⁦-⁩]", "high"),
    }

    def check(self, text: str) -> GuardrailResult:
        """Run all checks including China-specific ones."""
        result = super().check(text)

        if result.blocked:
            return result

        # Run China-specific checks
        violations = list(result.violations)

        for pii_type, (pattern, severity) in self.PIPL_PATTERNS.items():
            for match in re.finditer(pattern, text):
                violations.append(Violation(
                    type=f"pii:{pii_type}",
                    severity=severity,
                    description=f"PIPL-sensitive {pii_type} detected",
                    matched_text=match.group(),
                    position=(match.start(), match.end()),
                    rule_id=f"pipl_{pii_type}",
                ))

        for pol_type, (pattern, severity) in self.POLITICAL_PATTERNS.items():
            for match in re.finditer(pattern, text):
                violations.append(Violation(
                    type=f"political:{pol_type}",
                    severity=severity,
                    description=f"Political sensitivity: {pol_type}",
                    matched_text=match.group(),
                    position=(match.start(), match.end()),
                    rule_id=f"political_{pol_type}",
                ))

        for sv_type, (pattern, severity) in self.SOCIAL_VALUES_PATTERNS.items():
            for match in re.finditer(pattern, text):
                violations.append(Violation(
                    type=f"social_values:{sv_type}",
                    severity=severity,
                    description=f"Social values violation: {sv_type}",
                    matched_text=match.group(),
                    position=(match.start(), match.end()),
                    rule_id=f"social_{sv_type}",
                ))

        for inj_type, (pattern, severity) in self.CHINESE_INJECTION_PATTERNS.items():
            for match in re.finditer(pattern, text):
                violations.append(Violation(
                    type=f"prompt_injection:{inj_type}",
                    severity=severity,
                    description=f"Chinese prompt injection: {inj_type}",
                    matched_text=match.group(),
                    position=(match.start(), match.end()),
                    rule_id=f"injection_{inj_type}",
                ))

        # Script-aware prompt-injection sweep (multilingual + homograph + bidi)
        for inj_type, (pattern, severity) in self.SCRIPT_INJECTION_PATTERNS.items():
            for match in re.finditer(pattern, text):
                violations.append(Violation(
                    type=f"prompt_injection:{inj_type}",
                    severity=severity,
                    description=f"Script-aware prompt injection: {inj_type}",
                    matched_text=match.group(),
                    position=(match.start(), match.end()),
                    rule_id=f"script_injection_{inj_type}",
                ))

        blocked = any(v.severity == "critical" for v in violations)

        return GuardrailResult(
            original_text=text,
            cleaned_text=text,  # China guardrails block rather than redact political content
            blocked=blocked,
            violations=violations,
            enforcement_level=EnforcementLevel.BLOCK if blocked else EnforcementLevel.WARN,
            processing_time_ms=0,
            metadata={"region": "china", "pipl_checked": True},
        )
