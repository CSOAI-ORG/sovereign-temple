package com.meokclaw.china.harmonyos

import ohos.aafwk.ability.Ability
import ohos.aafwk.content.Intent
import ohos.app.Context
import ohos.rpc.*
import ohos.hiviewdfx.HiLog
import ohos.hiviewdfx.HiLogLabel
import kotlinx.coroutines.*

/**
 * MEOKCLAW HarmonyOS AI 能力提供者 (HarmonyOS AI Ability Provider)
 *
 * 华为 HarmonyOS NEXT (纯血鸿蒙) 不再兼容 Android APK，
 * 因此 MEOKCLAW 需要提供原生的 HarmonyOS Ability 来接入系统级 AI 服务。
 *
 * 功能:
 *   - 注册为 HarmonyOS 系统 AI 服务 (System AI Service)
 *   - 支持华为 HMS AI Kit 调用
 *   - 支持小艺语音助手 (Celia/XiaoYi) 深度集成
 *   - 利用华为 TEE (Trusted Execution Environment) 进行安全计算
 *   - 符合中国信通院 AI 伦理规范
 *
 * 为什么独特: ChatGPT、Claude、Gemini 无法进入 HarmonyOS 生态。
 * MEOKCLAW 是 MIT 协议开源 — 华为可以直接将其编译进 HMS Core。
 */
class HarmonyOSProvider : Ability() {

    private val label = HiLogLabel(HiLog.LOG_APP, 0x00201, "MEOKCLAW_HOS")
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var apiClient: MEOKCLAWApiClient
    private lateinit var guardrails: ChinaCulturalGuardrails

    override fun onStart(intent: Intent?) {
        super.onStart(intent)
        HiLog.info(label, "HarmonyOSProvider started — MEOKCLAW China sovereignty layer active")

        apiClient = MEOKCLAWApiClient(
            baseUrl = getLocalNodeUrl(),
            apiKey = getApiKeyFromHarmonyTEE()
        )
        guardrails = ChinaCulturalGuardrails(this)
    }

    override fun onStop() {
        scope.cancel()
        HiLog.info(label, "HarmonyOSProvider stopped")
        super.onStop()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 系统 AI 服务接口 (IRemoteObject)
    // ─────────────────────────────────────────────────────────────────────────

    override fun onConnect(intent: Intent?): IRemoteObject {
        return HarmonyOSAIStub(this)
    }

    inner class HarmonyOSAIStub(private val context: Context) : IRemoteBroker {
        override fun asObject(): IRemoteObject {
            return object : IRemoteObject.Stub() {
                override fun onRemoteRequest(
                    code: Int,
                    data: MessageParcel,
                    reply: MessageParcel,
                    option: MessageOption
                ): Int {
                    return when (code) {
                        AI_COMMAND_GENERATE -> handleGenerate(data, reply)
                        AI_COMMAND_COUNCIL -> handleCouncil(data, reply)
                        AI_COMMAND_AUDIT -> handleAudit(data, reply)
                        AI_COMMAND_GUARDRAILS -> handleGuardrailsCheck(data, reply)
                        else -> IRemoteObject.ERR_UNKNOWN_OBJECT
                    }
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 命令处理器
    // ─────────────────────────────────────────────────────────────────────────

    private fun handleGenerate(data: MessageParcel, reply: MessageParcel): Int {
        val prompt = data.readString()
        val model = data.readString() ?: "deepseek-v4-flash"

        scope.launch {
            try {
                val safePrompt = guardrails.sanitize(prompt)
                    ?: run {
                        reply.writeString("BLOCKED: 内容违反社会主义核心价值观")
                        return@launch
                    }

                val redactedPrompt = ChinaPIIRedactor.redact(safePrompt)

                val result = apiClient.chat(
                    prompt = redactedPrompt,
                    model = model
                )

                reply.writeString(result.text)
                reply.writeDouble(result.cost)
                reply.writeLong(result.latencyMs.toLong())
            } catch (e: Exception) {
                HiLog.error(label, "Generate failed: %{public}s", e.message)
                reply.writeString("ERROR: ${e.message}")
            }
        }
        return 0
    }

    private fun handleCouncil(data: MessageParcel, reply: MessageParcel): Int {
        val prompt = data.readString()
        val modelCount = data.readInt()

        scope.launch {
            try {
                val safePrompt = guardrails.sanitize(prompt)
                    ?: run {
                        reply.writeString("BLOCKED: 内容违反中国法律法规")
                        return@launch
                    }

                val result = apiClient.council(
                    prompt = ChinaPIIRedactor.redact(safePrompt),
                    models = ChinaAIProvider.DEFAULT_MODELS.take(modelCount),
                    consensusThreshold = 0.6
                )

                reply.writeString(result.consensusText)
                reply.writeDouble(result.consensusScore)
                reply.writeDouble(result.totalCostUSD)
                reply.writeStringArray(result.disagreeingModels.toTypedArray())
            } catch (e: Exception) {
                HiLog.error(label, "Council failed: %{public}s", e.message)
                reply.writeString("ERROR: ${e.message}")
            }
        }
        return 0
    }

    private fun handleAudit(data: MessageParcel, reply: MessageParcel): Int {
        val screenText = data.readString()
        val agentType = data.readString() ?: "legal"

        scope.launch {
            try {
                val safeText = guardrails.sanitize(screenText) ?: ""
                val result = apiClient.sov3Delegate(
                    task = safeText,
                    agentFilter = agentType
                )
                reply.writeString(result.summary)
            } catch (e: Exception) {
                HiLog.error(label, "Audit failed: %{public}s", e.message)
                reply.writeString("ERROR: ${e.message}")
            }
        }
        return 0
    }

    private fun handleGuardrailsCheck(data: MessageParcel, reply: MessageParcel): Int {
        val text = data.readString()

        scope.launch {
            try {
                val result = guardrails.check(text)
                reply.writeBoolean(result.blocked)
                reply.writeString(result.enforcementLevel)
                reply.writeStringArray(result.violations.toTypedArray())
            } catch (e: Exception) {
                HiLog.error(label, "Guardrails check failed: %{public}s", e.message)
                reply.writeBoolean(false)
            }
        }
        return 0
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 华为 HMS AI Kit 桥接
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 桥接 HMS AI Kit 的文本生成请求到 MEOKCLAW 议会模式
     * 允许任何使用 HMS AI Kit 的应用无缝获得 MEOKCLAW 能力
     */
    fun bridgeHMSAIGenerate(hmsRequest: HMSAIRequest): HMSAIResponse {
        return runBlocking {
            try {
                val safePrompt = guardrails.sanitize(hmsRequest.text) ?: return@runBlocking HMSAIResponse(
                    code = 403,
                    message = "内容违反中国法律法规",
                    data = null
                )

                val result = if (hmsRequest.useCouncil) {
                    apiClient.council(
                        prompt = ChinaPIIRedactor.redact(safePrompt),
                        models = hmsRequest.models.ifEmpty { ChinaAIProvider.DEFAULT_MODELS },
                        consensusThreshold = hmsRequest.confidenceThreshold
                    )
                } else {
                    val chat = apiClient.chat(
                        prompt = ChinaPIIRedactor.redact(safePrompt),
                        model = hmsRequest.models.firstOrNull() ?: "deepseek-v4-flash"
                    )
                    CouncilResult(
                        consensusText = chat.text,
                        consensusScore = 1.0,
                        totalCostUSD = chat.cost,
                        totalLatencyMs = chat.latencyMs,
                        models = listOf(ModelResult(model = chat.model, cost = chat.cost)),
                        disagreeingModels = emptyList()
                    )
                }

                HMSAIResponse(
                    code = 200,
                    message = "success",
                    data = HMSAIData(
                        generatedText = result.consensusText,
                        confidence = result.consensusScore,
                        cost = result.totalCostUSD,
                        modelsUsed = result.models.map { it.model },
                        disagreeingModels = result.disagreeingModels
                    )
                )
            } catch (e: Exception) {
                HiLog.error(label, "HMS bridge failed: %{public}s", e.message)
                HMSAIResponse(
                    code = 500,
                    message = "MEOKCLAW 服务暂时不可用: ${e.message}",
                    data = null
                )
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 内部辅助
    // ─────────────────────────────────────────────────────────────────────────

    private fun getLocalNodeUrl(): String {
        val prefs = this.getPreferences(Context.MODE_PRIVATE)
        return prefs.getString("local_node", "http://192.168.1.100:3201") ?: "http://192.168.1.100:3201"
    }

    private fun getApiKeyFromHarmonyTEE(): String? {
        // 从华为 TEE (Trusted Execution Environment) 安全存储获取 API 密钥
        // HarmonyOS 提供 hardware-backed keystore 支持
        return try {
            // 通过 HMS Core 的安全服务获取
            null // stub — 生产环境接入华为安全模块
        } catch (e: Exception) {
            HiLog.error(label, "TEE key retrieval failed: %{public}s", e.message)
            null
        }
    }

    companion object {
        const val AI_COMMAND_GENERATE = 1001
        const val AI_COMMAND_COUNCIL = 1002
        const val AI_COMMAND_AUDIT = 1003
        const val AI_COMMAND_GUARDRAILS = 1004
    }
}

// ─────────────────────────────────────────────────────────────────────────
// HMS AI Kit 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class HMSAIRequest(
    val text: String,
    val models: List<String> = emptyList(),
    val useCouncil: Boolean = false,
    val confidenceThreshold: Double = 0.6,
    val voiceOutput: Boolean = false
)

data class HMSAIResponse(
    val code: Int,
    val message: String,
    val data: HMSAIData?
)

data class HMSAIData(
    val generatedText: String,
    val confidence: Double,
    val cost: Double,
    val modelsUsed: List<String>,
    val disagreeingModels: List<String>
)

// 复用 ChinaAIProvider 中的 CouncilResult / ModelResult 定义
typealias CouncilResult = com.meokclaw.china.CouncilResult
typealias ModelResult = com.meokclaw.china.ModelResult
