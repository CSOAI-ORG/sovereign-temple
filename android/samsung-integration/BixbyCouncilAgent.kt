package com.meokclaw.samsung.bixby

import android.app.Activity
import android.content.Intent
import com.samsung.android.sdk.bixby2.AppControl
import com.samsung.android.sdk.bixby2.Sbixby
import com.samsung.android.sdk.bixby2.action.ResponseCallback
import kotlinx.coroutines.*

/**
 * MEOKCLAW Bixby Council Agent — Bixby Capsule Integration
 *
 * Bixby is Samsung's deeply integrated voice assistant (firmware-level).
 * This agent registers MEOKCLAW as a Bixby Capsule, allowing:
 *
 *   "Hey Bixby, council mode"
 *   "Hey Bixby, what's the nunchi on this?"
 *   "Hey Bixby, audit this email"
 *   "Hey Bixby, ask MEOKCLAW about Samsung stock"
 *
 * Why unique: ChatGPT, Claude, Gemini cannot integrate with Bixby.
 * Samsung only opens Bixby to strategic partners. MEOKCLAW offers
 * Samsung a democratic alternative to Gemini that Samsung can brand.
 */
class BixbyCouncilAgent(private val context: android.content.Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val aiProvider = SamsungAIProvider()

    /**
     * Register all Bixby intents on initialization.
     */
    fun register() {
        Sbixby.initialize(context)

        // Register intent handlers
        Sbixby.getAgent().addAppAction("AskCouncil", ::handleAskCouncil)
        Sbixby.getAgent().addAppAction("AuditScreen", ::handleAuditScreen)
        Sbixby.getAgent().addAppAction("GuardrailsCheck", ::handleGuardrailsCheck)
        Sbixby.getAgent().addAppAction("CostReport", ::handleCostReport)
        Sbixby.getAgent().addAppAction("NunchiCheck", ::handleNunchiCheck)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Intent: AskCouncil
    // ─────────────────────────────────────────────────────────────────────────
    private fun handleAskCouncil(
        appControl: AppControl,
        responseCallback: ResponseCallback
    ) {
        val query = appControl.parameters["query"] as? String ?: ""
        val modelCount = (appControl.parameters["model_count"] as? Int) ?: 3
        val honorificMode = appControl.parameters["honorific"] as? String ?: "auto"

        scope.launch {
            try {
                // Detect Bixby voice context
                val voiceContext = detectVoiceContext(appControl)

                val options = AIOptions(
                    councilMode = true,
                    modelCount = modelCount,
                    voiceOutput = true,
                    context = mapOf(
                        "honorific" to honorificMode,
                        "voice_context" to voiceContext,
                        "bixby_session_id" to appControl.sessionId
                    )
                )

                val response = aiProvider.generateResponse(query, options)

                // Format Bixby-friendly response
                val bixbyResponse = formatBixbyResponse(response, honorificMode)

                responseCallback.onComplete(bixbyResponse)
            } catch (e: Exception) {
                responseCallback.onComplete(
                    BixbyResponse.error("죄송합니다. MEOKCLAW 카운슬 모드에 일시적인 문제가 발생했습니다.")
                )
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Intent: AuditScreen (Siri On-Screen Awareness equivalent)
    // ─────────────────────────────────────────────────────────────────────────
    private fun handleAuditScreen(
        appControl: AppControl,
        responseCallback: ResponseCallback
    ) {
        val agentType = appControl.parameters["agent_type"] as? String ?: "legal"

        scope.launch {
            try {
                // Capture current screen content via MediaProjection / Accessibility
                val screenText = captureScreenContent()

                val response = aiProvider.auditScreen(
                    screenText = screenText,
                    agentType = agentType,
                    voiceOutput = true
                )

                responseCallback.onComplete(
                    BixbyResponse.success(response.text)
                )
            } catch (e: Exception) {
                responseCallback.onComplete(
                    BixbyResponse.error("화면 분석 중 오류가 발생했습니다.")
                )
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Intent: NunchiCheck — Cultural consensus reading
    // ─────────────────────────────────────────────────────────────────────────
    private fun handleNunchiCheck(
        appControl: AppControl,
        responseCallback: ResponseCallback
    ) {
        val situation = appControl.parameters["situation"] as? String ?: ""

        scope.launch {
            try {
                val options = AIOptions(
                    councilMode = true,
                    modelCount = 5, // More models for nunchi = better reading
                    context = mapOf(
                        "nunchi_mode" to "true",
                        "group_harmony_bias" to "0.8",
                        "seniority_weight" to "0.7"
                    )
                )

                val response = aiProvider.generateResponse(
                    prompt = "이 상황에서 눈치있게 행동하려면 어떻게 해야 하나요: $situation",
                    options = options
                )

                // Add nunchi-specific preamble
                val nunchiText = "눈치 분석 결과: ${response.text}"

                responseCallback.onComplete(
                    BixbyResponse.success(nunchiText)
                )
            } catch (e: Exception) {
                responseCallback.onComplete(
                    BixbyResponse.error("눈치 분석 중 오류가 발생했습니다.")
                )
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Intent: GuardrailsCheck
    // ─────────────────────────────────────────────────────────────────────────
    private fun handleGuardrailsCheck(
        appControl: AppControl,
        responseCallback: ResponseCallback
    ) {
        val text = appControl.parameters["text"] as? String ?: ""

        scope.launch {
            try {
                val guardrails = KoreanCulturalGuardrails(context)
                val result = guardrails.check(text)

                val response = when {
                    result.blocked -> "🛡️ 차단됨: ${result.violations.joinToString(", ")}"
                    result.enforcementLevel == "redact" -> "⚠️ 정제됨: PII 정보가 삭제되었습니다."
                    else -> "✅ 안전합니다. 위반사항 없음."
                }

                responseCallback.onComplete(BixbyResponse.success(response))
            } catch (e: Exception) {
                responseCallback.onComplete(BixbyResponse.error("가드레일 검사 중 오류가 발생했습니다."))
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Intent: CostReport
    // ─────────────────────────────────────────────────────────────────────────
    private fun handleCostReport(
        appControl: AppControl,
        responseCallback: ResponseCallback
    ) {
        val period = appControl.parameters["period"] as? String ?: "today"

        scope.launch {
            try {
                val report = aiProvider.getCostReport(period)

                val response = when (period) {
                    "today" -> "오늘 AI 사용 비용은 $${String.format("%.4f", report.totalCost)}입니다. ${report.queryCount}회 질문, 캐시로 ${String.format("%.4f", report.cacheSavings)} 절약."
                    "week" -> "이번 주 AI 사용 비용은 $${String.format("%.4f", report.totalCost)}입니다."
                    else -> "$period 기간 동안 AI 사용 비용은 $${String.format("%.4f", report.totalCost)}입니다."
                }

                responseCallback.onComplete(BixbyResponse.success(response))
            } catch (e: Exception) {
                responseCallback.onComplete(BixbyResponse.error("비용 조회 중 오류가 발생했습니다."))
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────

    private fun detectVoiceContext(appControl: AppControl): String {
        return when {
            appControl.parameters.containsKey("group_chat") -> "group_chat"
            appControl.parameters.containsKey("business_meeting") -> "business"
            appControl.parameters.containsKey("family") -> "family"
            else -> "general"
        }
    }

    private fun formatBixbyResponse(response: AIResponse, honorificMode: String): BixbyResponse {
        val text = when {
            response.blocked -> "죄송합니다. 이 요청은 안전 정책에 의해 차단되었습니다."
            response.disagreeingModels.isNotEmpty() -> {
                val dissent = response.disagreeingModels.joinToString(", ")
                "${response.text} (참고: $dissent 모델이 이견을 제기했습니다. 비용: $${String.format("%.4f", response.totalCost)})"
            }
            else -> {
                when (honorificMode) {
                    "formal" -> "${response.text} (비용: $${String.format("%.4f", response.totalCost)}, 확신도: ${String.format("%.0f", (response.consensusScore ?: 0.0) * 100)}%)"
                    else -> response.text
                }
            }
        }
        return BixbyResponse.success(text)
    }

    private fun captureScreenContent(): String {
        // In production, uses MediaProjection API or AccessibilityService
        // to capture visible screen text
        return ""
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Bixby Response Models
// ─────────────────────────────────────────────────────────────────────────
data class BixbyResponse(
    val status: String,
    val speechText: String,
    val displayText: String? = null,
    val metadata: Map<String, Any> = emptyMap()
) {
    companion object {
        fun success(text: String): BixbyResponse = BixbyResponse(
            status = "success",
            speechText = text,
            displayText = text
        )

        fun error(message: String): BixbyResponse = BixbyResponse(
            status = "error",
            speechText = message,
            displayText = message
        )
    }
}
