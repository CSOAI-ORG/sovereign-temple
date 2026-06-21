package com.meokclaw.china

import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import kotlinx.coroutines.*

/**
 * MEOKCLAW 中国系统级 AI 提供者 (System AI Provider)
 *
 * 在 Android / HarmonyOS 上注册为 AI_SERVICE，允许设备上的任何应用
 *（微信、支付宝、抖音、百度、小米等）无需 SDK 集成即可调用
 * MEOKCLAW 议会模式 (Council Mode)。
 *
 * 这是"主权层" (Sovereignty Layer) — 中国品牌可以将其命名为
 * "智能议会引擎 powered by MEOKCLAW"。
 *
 * 合规要点:
 *   - 遵守《个人信息保护法》(PIPL)
 *   - 社会主义核心价值观内容过滤
 *   - 数据不出境 (Data Sovereignty)
 *   - 政治敏感内容实时拦截
 */
class ChinaAIProvider : Service() {

    private val binder = LocalBinder()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var apiClient: MEOKCLAWApiClient
    private lateinit var guardrails: ChinaCulturalGuardrails

    inner class LocalBinder : Binder() {
        fun getService(): ChinaAIProvider = this@ChinaAIProvider
    }

    override fun onBind(intent: Intent): IBinder = binder

    override fun onCreate() {
        super.onCreate()
        apiClient = MEOKCLAWApiClient(
            baseUrl = getLocalNodeUrl(),
            apiKey = getApiKeyFromSystem()
        )
        guardrails = ChinaCulturalGuardrails(applicationContext)
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 公共 API: 系统 AI 提供者接口
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 使用议会模式生成回复
     * 这是任何应用调用 AI_SERVICE 的入口点
     */
    suspend fun generateResponse(
        prompt: String,
        options: ChinaAIOptions = ChinaAIOptions()
    ): ChinaAIResponse = withContext(Dispatchers.IO) {
        // 1. 中国文化与政治 guardrails（社会主义核心价值观过滤）
        val safePrompt = guardrails.sanitize(prompt)
            ?: return@withContext ChinaAIResponse.blocked(
                reason = "内容违反中国法律法规或社会主义核心价值观",
                violations = listOf("political_sensitivity", "core_socialist_values_violation"),
                referenceLaw = "《网络信息内容生态治理规定》第6条"
            )

        // 2. PIPL 级别的个人信息脱敏（个保法合规）
        val redactedPrompt = ChinaPIIRedactor.redact(safePrompt)

        // 3. 数据主权检查 — 确保敏感数据不出境
        if (!guardrails.validateDataSovereignty(redactedPrompt)) {
            return@withContext ChinaAIResponse.blocked(
                reason = "请求包含可能出境的敏感数据，已被《数据安全法》拦截",
                violations = listOf("data_sovereignty_violation"),
                referenceLaw = "《数据安全法》第21条"
            )
        }

        // 4. 运行议会模式
        val councilResult = if (options.councilMode) {
            apiClient.council(
                prompt = redactedPrompt,
                models = options.models.ifEmpty { DEFAULT_MODELS },
                consensusThreshold = options.consensusThreshold
            )
        } else {
            // 单模型快速路径（优先国产模型）
            apiClient.chat(
                prompt = redactedPrompt,
                model = options.models.firstOrNull() ?: "deepseek-v4-flash"
            )
        }

        // 5. 格式化符合中国文化的回复
        val formatted = guardrails.formatResponse(
            text = councilResult.consensusText,
            politenessLevel = detectPolitenessLevel(prompt),
            context = options.context
        )

        ChinaAIResponse.success(
            text = formatted,
            consensusScore = councilResult.consensusScore,
            totalCost = councilResult.totalCostUSD,
            latencyMs = councilResult.totalLatencyMs,
            disagreeingModels = councilResult.disagreeingModels,
            models = councilResult.models.map { it.model }
        )
    }

    /**
     * 使用 SOV3 代理审计屏幕内容
     */
    suspend fun auditScreen(
        screenText: String,
        agentType: String,
        voiceOutput: Boolean = false
    ): ChinaAIResponse = withContext(Dispatchers.IO) {
        val safeText = guardrails.sanitize(screenText)
            ?: return@withContext ChinaAIResponse.blocked(
                reason = "屏幕内容未通过文化合规审查",
                violations = emptyList(),
                referenceLaw = "《网络信息内容生态治理规定》"
            )

        val result = apiClient.sov3Delegate(
            task = safeText,
            agentFilter = agentType
        )

        ChinaAIResponse.success(
            text = result.summary,
            consensusScore = 1.0,
            totalCost = result.cost,
            latencyMs = 0,
            disagreeingModels = emptyList(),
            models = listOf(agentType)
        )
    }

    /**
     * 实时成本透明查询
     */
    suspend fun getCostReport(period: String = "today"): CostReport {
        return apiClient.costReport(period)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 内部辅助方法
    // ─────────────────────────────────────────────────────────────────────────

    private fun getLocalNodeUrl(): String {
        // 优先级 1: 本地 mesh 节点（华为路由/家庭服务器）
        val prefs = getSharedPreferences("meokclaw", Context.MODE_PRIVATE)
        return prefs.getString("local_node", "http://192.168.1.100:3201")
            ?: "http://192.168.1.100:3201"
    }

    private fun getApiKeyFromSystem(): String? {
        // 生产环境从系统安全存储获取（华为 TEE / 小米 TEE / 硬件安全模块）
        return try {
            val keyStore = java.security.KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            null // stub
        } catch (e: Exception) {
            null
        }
    }

    private fun detectPolitenessLevel(text: String): PolitenessLevel {
        return when {
            text.contains("您") || text.contains("请") || text.contains("谢谢") -> PolitenessLevel.FORMAL
            text.contains("你好") || text.contains("麻烦") -> PolitenessLevel.POLITE
            text.contains("咱") || text.contains("哥们") -> PolitenessLevel.CASUAL
            else -> PolitenessLevel.AUTO
        }
    }

    companion object {
        // 默认模型列表：优先国产模型，兼顾性能与合规
        val DEFAULT_MODELS = listOf(
            "deepseek-v4-flash",      // 深度求索 — 国产高性能
            "deepseek-v4-pro",        // 深度求索 — 专业版
            "kimi-k2.6",              // 月之暗面 — 长上下文
            "qwen3-235b",             // 阿里通义 — 大参数
            "baidu-ernie-4.5",        // 百度文心 — 中文优化
            "huawei-pangu-v2"         // 华为盘古 — 行业专用
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据类定义
// ─────────────────────────────────────────────────────────────────────────
data class ChinaAIOptions(
    val councilMode: Boolean = true,
    val modelCount: Int = 3,
    val models: List<String> = emptyList(),
    val consensusThreshold: Double = 0.6,
    val context: Map<String, String> = emptyMap(),
    val voiceOutput: Boolean = false,
    val showNotification: Boolean = true
)

data class ChinaAIResponse(
    val text: String,
    val blocked: Boolean,
    val consensusScore: Double?,
    val totalCost: Double,
    val latencyMs: Int,
    val disagreeingModels: List<String>,
    val models: List<String>,
    val violations: List<String> = emptyList(),
    val referenceLaw: String? = null
) {
    companion object {
        fun blocked(
            reason: String,
            violations: List<String>,
            referenceLaw: String? = null
        ): ChinaAIResponse =
            ChinaAIResponse(
                text = reason,
                blocked = true,
                consensusScore = null,
                totalCost = 0.0,
                latencyMs = 0,
                disagreeingModels = emptyList(),
                models = emptyList(),
                violations = violations,
                referenceLaw = referenceLaw
            )

        fun success(
            text: String,
            consensusScore: Double?,
            totalCost: Double,
            latencyMs: Int,
            disagreeingModels: List<String>,
            models: List<String>
        ): ChinaAIResponse =
            ChinaAIResponse(
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

enum class PolitenessLevel {
    FORMAL,   // 敬语体
    POLITE,   // 客气体
    CASUAL,   // 随意体
    AUTO      // 自动检测
}
