package com.meokclaw.china.baidu

import android.content.Context
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.concurrent.ConcurrentHashMap

/**
 * MEOKCLAW 千帆模型路由器 (Qianfan Router)
 *
 * 百度智能云千帆大模型平台的智能路由层：
 *   - 动态负载均衡：根据各模型实时延迟和成功率分配流量
 *   - 成本优化：优先使用性价比最高的模型
 *   - 故障转移：单点故障时自动切换备用模型
 *   - A/B 测试：支持新模型灰度发布
 *   - 合规路由：敏感任务强制路由到合规认证模型
 *
 * 千帆支持的模型（部分）：
 *   - ernie-4.5, ernie-4.5-turbo, ernie-lite
 *   - ernie-code, ernie-law, ernie-health, ernie-finance
 *   - 第三方: deepseek-v4, kimi-k2.6, qwen3, llama3, chatglm
 *
 * 合规要点:
 *   - 金融/医疗/法律任务强制使用行业认证模型
 *   - 所有路由决策记录审计日志
 *   - 敏感数据路由到境内部署实例
 */
class QianfanRouter(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val metrics = ConcurrentHashMap<String, ModelMetrics>()
    private val mutex = Mutex()
    private var routingConfig: RoutingConfig = RoutingConfig.DEFAULT

    // 千帆模型端点配置
    private val endpoints = mutableMapOf<String, QianfanEndpoint>()

    init {
        initializeEndpoints()
        startMetricsCleanup()
    }

    private fun initializeEndpoints() {
        endpoints["ernie-4.5"] = QianfanEndpoint(
            modelId = "ernie-4.5",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/ernie-4.5",
            region = "beijing",
            complianceLevel = ComplianceLevel.GENERAL,
            costPer1KTokens = 0.012
        )
        endpoints["ernie-4.5-turbo"] = QianfanEndpoint(
            modelId = "ernie-4.5-turbo",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/ernie-4.5-turbo",
            region = "beijing",
            complianceLevel = ComplianceLevel.GENERAL,
            costPer1KTokens = 0.008
        )
        endpoints["ernie-code"] = QianfanEndpoint(
            modelId = "ernie-code",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/ernie-code",
            region = "beijing",
            complianceLevel = ComplianceLevel.GENERAL,
            costPer1KTokens = 0.015
        )
        endpoints["ernie-law"] = QianfanEndpoint(
            modelId = "ernie-law",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/ernie-law",
            region = "beijing",
            complianceLevel = ComplianceLevel.REGULATED, // 法律行业需额外合规
            costPer1KTokens = 0.020
        )
        endpoints["ernie-health"] = QianfanEndpoint(
            modelId = "ernie-health",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/ernie-health",
            region = "beijing",
            complianceLevel = ComplianceLevel.REGULATED, // 医疗行业需额外合规
            costPer1KTokens = 0.020
        )
        endpoints["ernie-finance"] = QianfanEndpoint(
            modelId = "ernie-finance",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/ernie-finance",
            region = "shanghai", // 金融数据中心在上海
            complianceLevel = ComplianceLevel.REGULATED,
            costPer1KTokens = 0.018
        )
        endpoints["deepseek-v4"] = QianfanEndpoint(
            modelId = "deepseek-v4",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/deepseek-v4",
            region = "beijing",
            complianceLevel = ComplianceLevel.GENERAL,
            costPer1KTokens = 0.006
        )
        endpoints["qwen3"] = QianfanEndpoint(
            modelId = "qwen3",
            baseUrl = "https://qianfan.baidubce.com/v2/chat/qwen3",
            region = "hangzhou",
            complianceLevel = ComplianceLevel.GENERAL,
            costPer1KTokens = 0.010
        )
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 核心路由逻辑
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 智能路由 — 根据任务特征选择最优模型
     */
    suspend fun route(
        prompt: String,
        taskType: BaiduTaskType = BaiduTaskType.GENERAL,
        constraints: RoutingConstraints = RoutingConstraints()
    ): RoutingDecision = withContext(Dispatchers.IO) {
        val guardrails = ChinaCulturalGuardrails(context)

        // 1. 内容合规预检
        val safePrompt = guardrails.sanitize(prompt)
            ?: return@withContext RoutingDecision.blocked("内容未通过社会主义核心价值观审查")

        // 2. 合规级别筛选
        val requiredCompliance = when (taskType) {
            BaiduTaskType.LEGAL -> ComplianceLevel.REGULATED
            BaiduTaskType.MEDICAL -> ComplianceLevel.REGULATED
            BaiduTaskType.FINANCE -> ComplianceLevel.REGULATED
            else -> ComplianceLevel.GENERAL
        }

        val eligibleEndpoints = endpoints.values.filter { endpoint ->
            endpoint.complianceLevel.ordinal >= requiredCompliance.ordinal &&
                    (!constraints.requireLowLatency || endpoint.region == "beijing") &&
                    (!constraints.maxCostPer1K.let { max -> max == null || endpoint.costPer1KTokens <= max })
        }

        if (eligibleEndpoints.isEmpty()) {
            return@withContext RoutingDecision.error("无符合条件的模型端点")
        }

        // 3. 基于实时指标选择最优端点
        val scoredEndpoints = eligibleEndpoints.map { endpoint ->
            val metric = metrics[endpoint.modelId] ?: ModelMetrics()
            val score = calculateScore(endpoint, metric, constraints)
            endpoint to score
        }.sortedByDescending { it.second }

        val selected = scoredEndpoints.first().first
        val alternatives = scoredEndpoints.drop(1).take(2).map { it.first.modelId }

        // 4. 数据主权验证 — 确保敏感数据不出境
        if (!guardrails.validateDataSovereignty(safePrompt) && selected.region != "beijing") {
            // 强制路由到北京节点
            val beijingEndpoint = eligibleEndpoints.find { it.region == "beijing" }
                ?: return@withContext RoutingDecision.error("无境内合规节点可用")
            return@withContext RoutingDecision.success(
                endpoint = beijingEndpoint,
                prompt = safePrompt,
                reason = "数据主权要求 — 强制路由至北京节点",
                alternatives = alternatives
            )
        }

        RoutingDecision.success(
            endpoint = selected,
            prompt = safePrompt,
            reason = "综合评分最优: 延迟=${metrics[selected.modelId]?.avgLatencyMs ?: "N/A"}ms, 成功率=${metrics[selected.modelId]?.successRate ?: "N/A"}%",
            alternatives = alternatives
        )
    }

    /**
     * 批量路由 — 议会模式多模型并行调用
     */
    suspend fun routeForCouncil(
        prompt: String,
        modelCount: Int = 3,
        requireDiversity: Boolean = true
    ): List<RoutingDecision> = withContext(Dispatchers.IO) {
        val guardrails = ChinaCulturalGuardrails(context)
        val safePrompt = guardrails.sanitize(prompt)
            ?: return@withContext listOf(RoutingDecision.blocked("内容未通过审查"))

        val eligible = endpoints.values.filter {
            it.complianceLevel == ComplianceLevel.GENERAL ||
                    it.complianceLevel == ComplianceLevel.REGULATED
        }

        // 如果需要多样性，确保覆盖不同厂商
        val selected = if (requireDiversity) {
            val byVendor = eligible.groupBy { getVendor(it.modelId) }
            val picks = mutableListOf<QianfanEndpoint>()

            // 优先百度模型
            byVendor["baidu"]?.firstOrNull()?.let { picks.add(it) }
            // 然后其他国产模型
            byVendor["deepseek"]?.firstOrNull()?.let { picks.add(it) }
            byVendor["alibaba"]?.firstOrNull()?.let { picks.add(it) }

            picks.take(modelCount)
        } else {
            eligible.sortedByDescending {
                calculateScore(it, metrics[it.modelId] ?: ModelMetrics(), RoutingConstraints())
            }.take(modelCount)
        }

        selected.map {
            RoutingDecision.success(
                endpoint = it,
                prompt = safePrompt,
                reason = "议会模式路由",
                alternatives = emptyList()
            )
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 评分与指标
    // ─────────────────────────────────────────────────────────────────────────

    private fun calculateScore(
        endpoint: QianfanEndpoint,
        metric: ModelMetrics,
        constraints: RoutingConstraints
    ): Double {
        var score = 100.0

        // 延迟惩罚 (权重 30%)
        val latencyPenalty = (metric.avgLatencyMs / 1000.0).coerceAtMost(30.0)
        score -= latencyPenalty * 0.3

        // 成功率奖励 (权重 30%)
        score += (metric.successRate - 0.95).coerceAtLeast(0.0) * 300.0

        // 成本惩罚 (权重 20%)
        val costPenalty = endpoint.costPer1KTokens * 100
        score -= costPenalty * 0.2

        // 新鲜度奖励 (权重 10%) — 优先最近成功的
        val freshnessBonus = if (System.currentTimeMillis() - metric.lastSuccessTime < 60000) 5.0 else 0.0
        score += freshnessBonus

        // 合规加分 (权重 10%)
        if (endpoint.complianceLevel == ComplianceLevel.REGULATED) {
            score += 3.0
        }

        // 用户成本约束
        constraints.maxCostPer1K?.let { max ->
            if (endpoint.costPer1KTokens > max) score -= 50.0
        }

        return score.coerceAtLeast(0.0)
    }

    /**
     * 记录调用指标，用于后续路由优化
     */
    suspend fun recordMetrics(
        modelId: String,
        latencyMs: Int,
        success: Boolean,
        tokenCount: Int
    ) = mutex.withLock {
        val current = metrics[modelId] ?: ModelMetrics()
        val updated = current.copy(
            totalCalls = current.totalCalls + 1,
            successfulCalls = current.successfulCalls + if (success) 1 else 0,
            avgLatencyMs = (current.avgLatencyMs * current.totalCalls + latencyMs) / (current.totalCalls + 1),
            lastSuccessTime = if (success) System.currentTimeMillis() else current.lastSuccessTime,
            totalTokens = current.totalTokens + tokenCount
        )
        metrics[modelId] = updated
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 配置管理
    // ─────────────────────────────────────────────────────────────────────────

    fun updateRoutingConfig(config: RoutingConfig) {
        routingConfig = config
    }

    fun getCurrentMetrics(): Map<String, ModelMetrics> = metrics.toMap()

    private fun getVendor(modelId: String): String {
        return when {
            modelId.startsWith("ernie") -> "baidu"
            modelId.startsWith("deepseek") -> "deepseek"
            modelId.startsWith("qwen") -> "alibaba"
            modelId.startsWith("kimi") -> "moonshot"
            else -> "other"
        }
    }

    private fun startMetricsCleanup() {
        scope.launch {
            while (isActive) {
                delay(300_000) // 每 5 分钟清理过期指标
                val cutoff = System.currentTimeMillis() - 3_600_000 // 保留 1 小时
                metrics.entries.removeIf { it.value.lastSuccessTime < cutoff && it.value.totalCalls < 10 }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class RoutingDecision(
    val endpoint: QianfanEndpoint?,
    val prompt: String,
    val blocked: Boolean,
    val error: String?,
    val reason: String,
    val alternatives: List<String>
) {
    companion object {
        fun success(
            endpoint: QianfanEndpoint,
            prompt: String,
            reason: String,
            alternatives: List<String>
        ) = RoutingDecision(endpoint, prompt, false, null, reason, alternatives)

        fun blocked(reason: String) =
            RoutingDecision(null, "", true, reason, "blocked", emptyList())

        fun error(message: String) =
            RoutingDecision(null, "", false, message, "error", emptyList())
    }
}

data class QianfanEndpoint(
    val modelId: String,
    val baseUrl: String,
    val region: String, // beijing | shanghai | hangzhou | shenzhen
    val complianceLevel: ComplianceLevel,
    val costPer1KTokens: Double
)

data class ModelMetrics(
    val totalCalls: Int = 0,
    val successfulCalls: Int = 0,
    val avgLatencyMs: Int = 500,
    val lastSuccessTime: Long = 0,
    val totalTokens: Int = 0
) {
    val successRate: Double
        get() = if (totalCalls > 0) successfulCalls.toDouble() / totalCalls else 1.0
}

data class RoutingConstraints(
    val requireLowLatency: Boolean = false,
    val maxCostPer1K: Double? = null,
    val requireCompliance: ComplianceLevel = ComplianceLevel.GENERAL
)

data class RoutingConfig(
    val latencyWeight: Double = 0.3,
    val successRateWeight: Double = 0.3,
    val costWeight: Double = 0.2,
    val freshnessWeight: Double = 0.1,
    val complianceWeight: Double = 0.1
) {
    companion object {
        val DEFAULT = RoutingConfig()
    }
}

enum class ComplianceLevel {
    BASIC,      // 基础合规
    GENERAL,    // 一般合规（默认）
    REGULATED   // 受监管行业（金融/医疗/法律）
}
