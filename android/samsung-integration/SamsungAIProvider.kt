package com.meokclaw.samsung

import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import kotlinx.coroutines.*

/**
 * MEOKCLAW System AI Provider for Samsung Galaxy devices.
 *
 * Registers as Android 15 AI_SERVICE, allowing ANY app on the device
 * (KakaoTalk, Naver, Samsung Notes, third-party apps) to invoke
 * MEOKCLAW council mode without SDK integration.
 *
 * This is the "sovereignty layer" — Samsung can brand it as
 * "Galaxy AI Council powered by MEOKCLAW."
 */
class SamsungAIProvider : Service() {

    private val binder = LocalBinder()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var apiClient: MEOKCLAWApiClient
    private lateinit var guardrails: KoreanCulturalGuardrails

    inner class LocalBinder : Binder() {
        fun getService(): SamsungAIProvider = this@SamsungAIProvider
    }

    override fun onBind(intent: Intent): IBinder = binder

    override fun onCreate() {
        super.onCreate()
        apiClient = MEOKCLAWApiClient(
            baseUrl = getLocalNodeUrl(),
            apiKey = getApiKeyFromKnox()
        )
        guardrails = KoreanCulturalGuardrails(applicationContext)
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Public API: System AI Provider Interface
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Generate a response using council mode.
     * This is the entry point for any app calling AI_SERVICE.
     */
    suspend fun generateResponse(
        prompt: String,
        options: AIOptions = AIOptions()
    ): AIResponse = withContext(Dispatchers.IO) {
        // 1. Korean cultural guardrails
        val safePrompt = guardrails.sanitize(prompt)
            ?: return@withContext AIResponse.blocked(
                reason = "Cultural guardrails blocked this request",
                violations = listOf("honorific_mismatch", "seniority_conflict")
            )

        // 2. Knox-level PII redaction
        val redactedPrompt = KnoxPIIRedactor.redact(safePrompt)

        // 3. Run council
        val councilResult = if (options.councilMode) {
            apiClient.council(
                prompt = redactedPrompt,
                models = options.models.ifEmpty { DEFAULT_MODELS },
                consensusThreshold = options.consensusThreshold
            )
        } else {
            // Single-model fast path
            apiClient.chat(prompt = redactedPrompt, model = options.models.firstOrNull() ?: "deepseek-v4-flash")
        }

        // 4. Format culturally appropriate response
        val formatted = guardrails.formatResponse(
            text = councilResult.consensusText,
            honorificLevel = detectHonorificLevel(prompt),
            context = options.context
        )

        AIResponse.success(
            text = formatted,
            consensusScore = councilResult.consensusScore,
            totalCost = councilResult.totalCostUSD,
            latencyMs = councilResult.totalLatencyMs,
            disagreeingModels = councilResult.disagreeingModels,
            models = councilResult.models.map { it.model }
        )
    }

    /**
     * Audit screen content using SOV3 agent delegation.
     */
    suspend fun auditScreen(
        screenText: String,
        agentType: String,
        voiceOutput: Boolean = false
    ): AIResponse = withContext(Dispatchers.IO) {
        val safeText = guardrails.sanitize(screenText)
            ?: return@withContext AIResponse.blocked(
                reason = "Screen content failed cultural guardrails",
                violations = emptyList()
            )

        val result = apiClient.sov3Delegate(
            task = safeText,
            agentFilter = agentType
        )

        AIResponse.success(
            text = result.summary,
            consensusScore = 1.0,
            totalCost = result.cost,
            latencyMs = 0,
            disagreeingModels = emptyList(),
            models = listOf(agentType)
        )
    }

    /**
     * Real-time cost transparency query.
     */
    suspend fun getCostReport(period: String = "today"): CostReport {
        return apiClient.costReport(period)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Internal Helpers
    // ─────────────────────────────────────────────────────────────────────────

    private fun getLocalNodeUrl(): String {
        // Priority 1: Local mesh node (Samsung SmartThings Hub or home server)
        val prefs = getSharedPreferences("meokclaw", Context.MODE_PRIVATE)
        return prefs.getString("local_node", "http://192.168.1.100:3201")
            ?: "http://192.168.1.100:3201"
    }

    private fun getApiKeyFromKnox(): String? {
        // In production, retrieve from Samsung Knox Keystore
        // Knox Keystore provides hardware-backed key storage
        return try {
            val knoxKey = android.security.keystore.KeyStore.getInstance("AndroidKeyStore")
            knoxKey.load(null)
            // Retrieve MEOKCLAW_API_KEY entry
            null // stub
        } catch (e: Exception) {
            null
        }
    }

    private fun detectHonorificLevel(text: String): HonorificLevel {
        return when {
            text.contains("합니다") || text.contains("세요") -> HonorificLevel.FORMAL
            text.contains("해요") || text.contains("세요") -> HonorificLevel.POLITE
            text.contains("한다") || text.contains("해") -> HonorificLevel.CASUAL
            else -> HonorificLevel.AUTO
        }
    }

    companion object {
        val DEFAULT_MODELS = listOf(
            "deepseek-v4-flash",
            "deepseek-v4-pro",
            "kimi-k2.6",
            "samsung-gauss-v1"
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Data Classes
// ─────────────────────────────────────────────────────────────────────────
data class AIOptions(
    val councilMode: Boolean = true,
    val modelCount: Int = 3,
    val models: List<String> = emptyList(),
    val consensusThreshold: Double = 0.6,
    val context: Map<String, String> = emptyMap(),
    val voiceOutput: Boolean = false,
    val showNotification: Boolean = true
)

data class AIResponse(
    val text: String,
    val blocked: Boolean,
    val consensusScore: Double?,
    val totalCost: Double,
    val latencyMs: Int,
    val disagreeingModels: List<String>,
    val models: List<String>,
    val violations: List<String> = emptyList()
) {
    companion object {
        fun blocked(reason: String, violations: List<String>): AIResponse =
            AIResponse(
                text = reason,
                blocked = true,
                consensusScore = null,
                totalCost = 0.0,
                latencyMs = 0,
                disagreeingModels = emptyList(),
                models = emptyList(),
                violations = violations
            )

        fun success(
            text: String,
            consensusScore: Double?,
            totalCost: Double,
            latencyMs: Int,
            disagreeingModels: List<String>,
            models: List<String>
        ): AIResponse =
            AIResponse(
                text = text,
                blocked = false,
                consensusScore = consensusScore,
                totalCost = totalCost,
                latencyMs = latencyMs,
                disagreeingModels = disagreeingModels,
                models = models
            )
    }
}

data class CostReport(
    val totalCost: Double,
    val queryCount: Int,
    val cacheSavings: Double,
    val topModel: String,
    val topModelCost: Double
)

enum class HonorificLevel {
    FORMAL,  // 존댓말 (합쇼체)
    POLITE,  // 해요체
    CASUAL,  // 반말 (해체)
    AUTO     // 자동 감지
}
