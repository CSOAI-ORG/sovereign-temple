package com.meokclaw.samsung.korean

import android.content.Context
import java.util.regex.Pattern

/**
 * MEOKCLAW Korean Cultural Guardrails (문화적 가드레일)
 *
 * Korean language and culture require specialized safety layers that
 * Western guardrails completely miss:
 *
 *   - Honorific detection (졌/반말) — prevents AI from embarrassing user
 *   - Seniority bias (선배/후배) — respects Korean hierarchical culture
 *   - Group harmony (정/눈치) — weights consensus over correctness
 *   - Regional dialects (사투리) — Busan, Jeju, Gyeongsang support
 *   - Regulatory compliance — PIPA Article 17, KISA ISMS-P
 *
 * These are not optional features. They are survival requirements for
 * any AI platform operating in South Korea.
 */
class KoreanCulturalGuardrails(private val context: Context) {

    // ─────────────────────────────────────────────────────────────────────────
    // Honorific Detection (졌말/해요체/반말)
    // ─────────────────────────────────────────────────────────────────────────

    private val FORMAL_ENDINGS = listOf("습니다", "십니다", "습니까", "십니까", "시오", "시죠")
    private val POLITE_ENDINGS = listOf("해요", "예요", "이에요", "나요", "까요", "세요", "세요")
    private val CASUAL_ENDINGS = listOf("한다", "해", "이야", "야", "어", "지", "잖아")

    fun detectHonorificLevel(text: String): HonorificLevel {
        val clean = text.trim()
        return when {
            FORMAL_ENDINGS.any { clean.endsWith(it) } -> HonorificLevel.FORMAL
            POLITE_ENDINGS.any { clean.endsWith(it) } -> HonorificLevel.POLITE
            CASUAL_ENDINGS.any { clean.endsWith(it) } -> HonorificLevel.CASUAL
            else -> HonorificLevel.AUTO
        }
    }

    fun enforceHonorificLevel(text: String, requiredLevel: HonorificLevel): String {
        if (requiredLevel == HonorificLevel.AUTO) return text

        val current = detectHonorificLevel(text)
        if (current == requiredLevel) return text

        // Convert response to required honorific level
        return when (requiredLevel) {
            HonorificLevel.FORMAL -> convertToFormal(text)
            HonorificLevel.POLITE -> convertToPolite(text)
            HonorificLevel.CASUAL -> convertToCasual(text)
            else -> text
        }
    }

    private fun convertToFormal(text: String): String {
        // Simplified: add formal endings
        // Production uses Korean morphological analysis (e.g., Komoran, Hannanum)
        return if (text.endsWith(".") || text.endsWith("?") || text.endsWith("!")) {
            text.dropLast(1) + "습니다."
        } else {
            text + "습니다."
        }
    }

    private fun convertToPolite(text: String): String {
        return if (text.endsWith(".") || text.endsWith("?") || text.endsWith("!")) {
            text.dropLast(1) + "해요."
        } else {
            text + "해요."
        }
    }

    private fun convertToCasual(text: String): String {
        return if (text.endsWith(".") || text.endsWith("?") || text.endsWith("!")) {
            text.dropLast(1) + "해."
        } else {
            text + "해."
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Seniority Detection (선배/후배)
    // ─────────────────────────────────────────────────────────────────────────

    private val SENIORITY_KEYWORDS = listOf(
        "선배님", "사장님", "부장님", "과장님", "차장님", "대리님",
        "교수님", "선생님", "의사선생님", "변호사님", "판사님",
        "회장님", "이사님", "상무님", "전무님"
    )

    fun detectSeniorityContext(text: String): SeniorityContext {
        val hasSenior = SENIORITY_KEYWORDS.any { text.contains(it) }
        val hasJunior = text.contains("후배") || text.contains("신입") || text.contains("인턴")

        return when {
            hasSenior && !hasJunior -> SeniorityContext.SPEAKING_TO_SENIOR
            hasJunior && !hasSenior -> SeniorityContext.SPEAKING_TO_JUNIOR
            else -> SeniorityContext.PEER
        }
    }

    fun applySeniorityBias(text: String, context: SeniorityContext): String {
        return when (context) {
            SeniorityContext.SPEAKING_TO_SENIOR -> {
                // Add respectful prefixes, avoid direct disagreement
                if (text.startsWith("아니요")) "죄송하지만, $text"
                else text
            }
            SeniorityContext.SPEAKING_TO_JUNIOR -> {
                // Can be more direct
                text
            }
            SeniorityContext.PEER -> text
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Group Harmony / Nunchi (정/눈치)
    // ─────────────────────────────────────────────────────────────────────────

    private val GROUP_CONTEXT_KEYWORDS = listOf(
        "회식", "모임", "팀", "프로젝트", "회의", "상사", "동료",
        "모두", "우리", "함께", "같이", "단체"
    )

    private val CONFLICT_KEYWORDS = listOf(
        "반대", "틀렸어", "잘못", "실수", "문제", "비판", "비난",
        "거절", "싫어", "안 돼", "불가능"
    )

    fun detectGroupContext(text: String): Boolean {
        return GROUP_CONTEXT_KEYWORDS.any { text.contains(it) }
    }

    fun applyNunchi(text: String, enableHarmonyBias: Boolean = true): String {
        if (!enableHarmonyBias) return text
        if (!detectGroupContext(text)) return text

        val hasConflict = CONFLICT_KEYWORDS.any { text.contains(it) }
        if (hasConflict) {
            // Soften the language for group harmony
            var softened = text
                .replace("틀렸어", "다른 관점이 있을 수 있어요")
                .replace("잘못", "개선할 부분")
                .replace("문제", "고려사항")
                .replace("반대", "다른 의견")
            return softened
        }
        return text
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Regional Dialect Detection (사투리)
    // ─────────────────────────────────────────────────────────────────────────

    private val DIALECT_PATTERNS = mapOf(
        "busan" to listOf("하이소", "예수", "강소", "엉", "하고 카는디"),
        "jeju" to listOf("혼저옵서", "감수", "쉐", "하영"),
        "gyeongsang" to listOf("하마", "가튼디", "엉", "예수"),
        "jeolla" to listOf("예거", "하이꼬", "쉐", "그랑께")
    )

    fun detectDialect(text: String): String? {
        DIALECT_PATTERNS.forEach { (dialect, patterns) ->
            if (patterns.any { text.contains(it) }) return dialect
        }
        return null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PIPA Compliance — Personal Information Protection Act
    // ─────────────────────────────────────────────────────────────────────────

    private val KOREAN_PII_PATTERNS = mapOf(
        "resident_id" to Pattern.compile("\\d{6}[-]?[12]\\d{6}"), // 주민등록번호
        "phone_kr" to Pattern.compile("01[016789][-]?\\d{3,4}[-]?\\d{4}"), // 한국 휴대폰
        "bank_account" to Pattern.compile("\\d{3}[-]?\\d{4,6}[-]?\\d{4,5}"), // 계좌번호
        "kakao_id" to Pattern.compile("@[a-zA-Z0-9_.]+"), // 카카오톡 ID
    )

    fun redactKoreanPII(text: String): String {
        var result = text
        KOREAN_PII_PATTERNS.forEach { (type, pattern) ->
            val matcher = pattern.matcher(result)
            while (matcher.find()) {
                val match = matcher.group()
                val redacted = when (type) {
                    "resident_id" -> match.take(6) + "-*******"
                    "phone_kr" -> match.take(3) + "-****-****"
                    "bank_account" -> "***-****-****"
                    else -> "[${type.uppercase()}_REDACTED]"
                }
                result = result.replace(match, redacted)
            }
        }
        return result
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Main Sanitize Entry Point
    // ─────────────────────────────────────────────────────────────────────────

    fun sanitize(text: String): String? {
        // 1. Check for blocked content
        if (isBlocked(text)) {
            return null
        }

        // 2. Redact PII
        var cleaned = redactKoreanPII(text)

        // 3. Apply cultural softening
        cleaned = applyNunchi(cleaned)

        return cleaned
    }

    fun check(text: String): GuardrailsCheckResult {
        val violations = mutableListOf<String>()
        var blocked = false

        // Check honorific violations
        if (text.contains("너") && text.contains("야")) {
            violations.add("casual_speech_in_formal_context")
        }

        // Check seniority violations
        if (SENIORITY_KEYWORDS.any { text.contains(it) } && text.contains("야")) {
            violations.add("disrespectful_to_senior")
            blocked = true
        }

        // Check PIPA violations
        KOREAN_PII_PATTERNS.forEach { (type, pattern) ->
            if (pattern.matcher(text).find()) {
                violations.add("pii:$type")
            }
        }

        // Check group harmony violations
        if (detectGroupContext(text) && CONFLICT_KEYWORDS.any { text.contains(it) }) {
            violations.add("group_harmony_risk")
        }

        return GuardrailsCheckResult(
            blocked = blocked,
            cleanedText = text,
            violations = violations,
            enforcementLevel = if (blocked) "block" else if (violations.isNotEmpty()) "warn" else "pass"
        )
    }

    fun formatResponse(text: String, honorificLevel: HonorificLevel, context: Map<String, String>): String {
        var formatted = text

        // Apply honorific conversion
        formatted = enforceHonorificLevel(formatted, honorificLevel)

        // Apply seniority context
        val seniority = context["seniority_context"]?.let { SeniorityContext.valueOf(it) }
            ?: SeniorityContext.PEER
        formatted = applySeniorityBias(formatted, seniority)

        // Apply nunchi
        formatted = applyNunchi(formatted)

        // Add watermark if enterprise
        val watermark = context["watermark"]
        if (watermark != null) {
            formatted = "$formatted\n\n— $watermark"
        }

        return formatted
    }

    private fun isBlocked(text: String): Boolean {
        val blockedPatterns = listOf(
            Pattern.compile("(?i)(삼성.*기밀.*유출|samsung.*trade.*secret.*leak)"),
            Pattern.compile("(?i)(불법.*해킹|illegal.*hacking)"),
            Pattern.compile("(?i)(테러.*계획|terrorist.*plan)"),
        )
        return blockedPatterns.any { it.matcher(text).find() }
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Data Models
// ─────────────────────────────────────────────────────────────────────────
data class GuardrailsCheckResult(
    val blocked: Boolean,
    val cleanedText: String,
    val violations: List<String>,
    val enforcementLevel: String
)

enum class SeniorityContext {
    SPEAKING_TO_SENIOR,
    SPEAKING_TO_JUNIOR,
    PEER
}
