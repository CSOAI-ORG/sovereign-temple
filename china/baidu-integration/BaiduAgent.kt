package com.meokclaw.china.baidu

import android.content.Context
import com.baidu.ai.auth.OAuthManager
import com.baidu.ai.ernie.ErnieBotClient
import com.baidu.ai.qianfan.QianfanClient
import kotlinx.coroutines.*
import org.json.JSONObject

/**
 * MEOKCLAW 百度 AI 代理适配器 (Baidu AI Agent Adapter)
 *
 * 深度集成百度文心一言 (Ernie Bot) 和千帆大模型平台：
 *   - 文心一言 4.5: 中文理解与生成标杆
 *   - 千帆模型路由: 根据场景自动选择最佳百度模型
 *   - 百度知识增强: 接入百度搜索实时信息
 *   - 百度 UNIT: 对话理解与技能管理
 *
 * 为什么独特: 百度在中文 NLP 领域积累深厚，Ernie 系列模型
 * 在中文成语、古诗词、行业术语上表现优异。MEOKCLAW 通过
 * 议会模式将百度模型与 DeepSeek、Kimi 等并列决策，
 * 获得更全面、更本土化的中文回复。
 *
 * 合规:
 *   - 百度云平台通过等保三级认证
 *   - 数据存储在中国大陆境内
 *   - 符合《生成式人工智能服务管理暂行办法》
 */
class BaiduAgent(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var ernieClient: ErnieBotClient
    private lateinit var qianfanClient: QianfanClient
    private lateinit var oAuthManager: OAuthManager
    private val guardrails: ChinaCulturalGuardrails = ChinaCulturalGuardrails(context)

    // 百度 API 凭证（生产环境从华为 TEE / Android Keystore 获取）
    private val baiduApiKey: String by lazy {
        context.getSharedPreferences("meokclaw_baidu", Context.MODE_PRIVATE)
            .getString("api_key", "") ?: ""
    }
    private val baiduSecretKey: String by lazy {
        context.getSharedPreferences("meokclaw_baidu", Context.MODE_PRIVATE)
            .getString("secret_key", "") ?: ""
    }

    init {
        initializeBaiduClients()
    }

    private fun initializeBaiduClients() {
        oAuthManager = OAuthManager(context, baiduApiKey, baiduSecretKey)
        ernieClient = ErnieBotClient(oAuthManager)
        qianfanClient = QianfanClient(oAuthManager)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 文心一言对话
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 调用文心一言生成回复
     * 自动应用中国文化 guardrails 和 PIPL 脱敏
     */
    suspend fun chatWithErnie(
        prompt: String,
        model: String = "ernie-4.5",
        options: BaiduChatOptions = BaiduChatOptions()
    ): BaiduChatResult = withContext(Dispatchers.IO) {
        // 1. Guardrails 检查
        val safePrompt = guardrails.sanitize(prompt)
            ?: return@withContext BaiduChatResult.blocked("内容未通过社会主义核心价值观审查")

        // 2. PIPL 脱敏
        val redactedPrompt = ChinaPIIRedactor.redact(safePrompt)

        try {
            val accessToken = oAuthManager.getAccessToken()

            val response = ernieClient.chat(
                model = model,
                messages = buildMessageHistory(redactedPrompt, options.history),
                temperature = options.temperature,
                topP = options.topP,
                maxOutputTokens = options.maxOutputTokens,
                accessToken = accessToken
            )

            // 3. 对百度输出进行 guardrails 复查
            val safeOutput = guardrails.sanitize(response.text)
                ?: return@withContext BaiduChatResult.blocked("模型输出包含不合规内容，已被拦截")

            BaiduChatResult.success(
                text = safeOutput,
                model = model,
                tokensUsed = response.usage?.totalTokens ?: 0,
                latencyMs = response.latencyMs,
                isSearchEnhanced = response.isSearchEnhanced
            )
        } catch (e: Exception) {
            BaiduChatResult.error("文心一言服务异常: ${e.message}")
        }
    }

    /**
     * 调用文心一言的函数调用能力 (Tool Use)
     * 支持百度地图、百度百科、百度翻译等工具
     */
    suspend fun chatWithTools(
        prompt: String,
        tools: List<BaiduTool> = DEFAULT_TOOLS,
        model: String = "ernie-4.5-turbo"
    ): BaiduToolResult = withContext(Dispatchers.IO) {
        val safePrompt = guardrails.sanitize(prompt)
            ?: return@withContext BaiduToolResult.blocked("内容未通过审查")

        try {
            val accessToken = oAuthManager.getAccessToken()
            val response = ernieClient.chatWithTools(
                model = model,
                messages = listOf(ErnieMessage("user", safePrompt)),
                tools = tools,
                accessToken = accessToken
            )

            BaiduToolResult.success(
                text = response.text,
                toolCalls = response.toolCalls,
                model = model
            )
        } catch (e: Exception) {
            BaiduToolResult.error("工具调用失败: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 千帆模型路由
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 千帆平台多模型路由
     * 根据任务类型自动选择最合适的百度系模型
     */
    suspend fun routeViaQianfan(
        prompt: String,
        taskType: BaiduTaskType = BaiduTaskType.GENERAL
    ): BaiduChatResult = withContext(Dispatchers.IO) {
        val safePrompt = guardrails.sanitize(prompt)
            ?: return@withContext BaiduChatResult.blocked("内容未通过审查")

        val model = selectModelForTask(taskType)

        try {
            val accessToken = oAuthManager.getAccessToken()
            val response = qianfanClient.chat(
                model = model,
                prompt = safePrompt,
                accessToken = accessToken
            )

            val safeOutput = guardrails.sanitize(response.text)
                ?: return@withContext BaiduChatResult.blocked("模型输出不合规")

            BaiduChatResult.success(
                text = safeOutput,
                model = model,
                tokensUsed = response.usage?.totalTokens ?: 0,
                latencyMs = response.latencyMs,
                isSearchEnhanced = false
            )
        } catch (e: Exception) {
            BaiduChatResult.error("千帆路由异常: ${e.message}")
        }
    }

    /**
     * 根据任务类型选择最优模型
     */
    private fun selectModelForTask(taskType: BaiduTaskType): String {
        return when (taskType) {
            BaiduTaskType.GENERAL -> "ernie-4.5"
            BaiduTaskType.CREATIVE -> "ernie-4.5-turbo"
            BaiduTaskType.CODE -> "ernie-code"
            BaiduTaskType.LEGAL -> "ernie-law"
            BaiduTaskType.MEDICAL -> "ernie-health"
            BaiduTaskType.FINANCE -> "ernie-finance"
            BaiduTaskType.EDUCATION -> "ernie-edu"
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 知识增强
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 百度搜索增强生成 (Search-Augmented Generation)
     * 将百度搜索实时结果融入回复
     */
    suspend fun searchAugmentedChat(
        query: String,
        searchDepth: Int = 5
    ): BaiduChatResult = withContext(Dispatchers.IO) {
        val safeQuery = guardrails.sanitize(query)
            ?: return@withContext BaiduChatResult.blocked("搜索查询未通过审查")

        try {
            // 先进行百度搜索
            val searchResults = ernieClient.searchBaidu(
                query = safeQuery,
                resultCount = searchDepth
            )

            // 构建增强提示
            val augmentedPrompt = buildString {
                appendLine("基于以下搜索结果回答问题：")
                searchResults.forEachIndexed { index, result ->
                    appendLine("[${index + 1}] ${result.title}: ${result.snippet}")
                }
                appendLine("\n用户问题：$safeQuery")
            }

            val response = ernieClient.chat(
                model = "ernie-4.5",
                messages = listOf(ErnieMessage("user", augmentedPrompt)),
                accessToken = oAuthManager.getAccessToken()
            )

            BaiduChatResult.success(
                text = response.text,
                model = "ernie-4.5-search",
                tokensUsed = response.usage?.totalTokens ?: 0,
                latencyMs = response.latencyMs,
                isSearchEnhanced = true,
                searchSources = searchResults.map { it.url }
            )
        } catch (e: Exception) {
            BaiduChatResult.error("搜索增强生成失败: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 内部辅助
    // ─────────────────────────────────────────────────────────────────────────

    private fun buildMessageHistory(
        currentPrompt: String,
        history: List<ErnieMessage>
    ): List<ErnieMessage> {
        val messages = mutableListOf<ErnieMessage>()
        messages.add(ErnieMessage("system", BAIDU_SYSTEM_PROMPT))
        messages.addAll(history.takeLast(10)) // 保留最近 10 轮
        messages.add(ErnieMessage("user", currentPrompt))
        return messages
    }

    companion object {
        // 百度系统提示词 — 强调中国文化和合规
        const val BAIDU_SYSTEM_PROMPT = """
            你是 MEOKCLAW 智能议会中的百度文心代表。
            你的职责是提供准确、客观、符合社会主义核心价值观的中文回复。
            
            原则：
            1. 坚持正确的政治方向，弘扬社会主义核心价值观
            2. 遵守中国法律法规，不生成违法违规内容
            3. 尊重中华优秀传统文化
            4. 在不确定时坦诚说明，不编造信息
            5. 使用规范现代汉语，适当运用成语和典故
            
            你与其他模型共同参与议会决策，你的独特优势是：
            - 深厚的中华文化底蕴
            - 实时搜索增强能力
            - 行业专用模型知识
        """.trimIndent()

        val DEFAULT_TOOLS = listOf(
            BaiduTool(name = "baidu_map", description = "百度地图查询"),
            BaiduTool(name = "baidu_baike", description = "百度百科查询"),
            BaiduTool(name = "baidu_translate", description = "百度翻译"),
            BaiduTool(name = "baidu_weather", description = "天气查询")
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class BaiduChatResult(
    val text: String,
    val model: String,
    val blocked: Boolean,
    val error: String?,
    val tokensUsed: Int,
    val latencyMs: Int,
    val isSearchEnhanced: Boolean,
    val searchSources: List<String> = emptyList()
) {
    companion object {
        fun success(
            text: String,
            model: String,
            tokensUsed: Int,
            latencyMs: Int,
            isSearchEnhanced: Boolean,
            searchSources: List<String> = emptyList()
        ) = BaiduChatResult(
            text = text, model = model, blocked = false, error = null,
            tokensUsed = tokensUsed, latencyMs = latencyMs,
            isSearchEnhanced = isSearchEnhanced, searchSources = searchSources
        )

        fun blocked(reason: String) = BaiduChatResult(
            text = reason, model = "", blocked = true, error = reason,
            tokensUsed = 0, latencyMs = 0, isSearchEnhanced = false
        )

        fun error(message: String) = BaiduChatResult(
            text = "", model = "", blocked = false, error = message,
            tokensUsed = 0, latencyMs = 0, isSearchEnhanced = false
        )
    }
}

data class BaiduToolResult(
    val text: String,
    val model: String,
    val blocked: Boolean,
    val error: String?,
    val toolCalls: List<ToolCall>
) {
    companion object {
        fun success(text: String, toolCalls: List<ToolCall>, model: String) =
            BaiduToolResult(text, model, false, null, toolCalls)

        fun blocked(reason: String) =
            BaiduToolResult("", "", true, reason, emptyList())

        fun error(message: String) =
            BaiduToolResult("", "", false, message, emptyList())
    }
}

data class BaiduChatOptions(
    val temperature: Double = 0.7,
    val topP: Double = 0.9,
    val maxOutputTokens: Int = 2048,
    val history: List<ErnieMessage> = emptyList()
)

data class ErnieMessage(val role: String, val content: String)
data class BaiduTool(val name: String, val description: String)
data class ToolCall(val name: String, val arguments: Map<String, String>)
data class SearchResult(val title: String, val snippet: String, val url: String)

enum class BaiduTaskType {
    GENERAL, CREATIVE, CODE, LEGAL, MEDICAL, FINANCE, EDUCATION
}

// 占位类 — 生产环境接入百度官方 SDK
class OAuthManager(context: Context, apiKey: String, secretKey: String) {
    suspend fun getAccessToken(): String = "stub_token"
}

class ErnieBotClient(private val oauth: OAuthManager) {
    suspend fun chat(
        model: String,
        messages: List<ErnieMessage>,
        temperature: Double = 0.7,
        topP: Double = 0.9,
        maxOutputTokens: Int = 2048,
        accessToken: String
    ): ErnieResponse = ErnieResponse("", null, 0, false)

    suspend fun chatWithTools(
        model: String,
        messages: List<ErnieMessage>,
        tools: List<BaiduTool>,
        accessToken: String
    ): ErnieToolResponse = ErnieToolResponse("", emptyList())

    suspend fun searchBaidu(query: String, resultCount: Int): List<SearchResult> = emptyList()
}

class QianfanClient(private val oauth: OAuthManager) {
    suspend fun chat(model: String, prompt: String, accessToken: String): ErnieResponse =
        ErnieResponse("", null, 0, false)
}

data class ErnieResponse(
    val text: String,
    val usage: TokenUsage?,
    val latencyMs: Int,
    val isSearchEnhanced: Boolean
)

data class ErnieToolResponse(val text: String, val toolCalls: List<ToolCall>)
data class TokenUsage(val totalTokens: Int)
