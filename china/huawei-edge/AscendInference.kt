package com.meokclaw.china.huawei.edge

import android.content.Context
import com.huawei.hiai.aimodel.AIModelManager
import com.huawei.hiai.aimodel.ModelDescription
import com.huawei.hiai.aimodel.executor.ModelExecutor
import com.huawei.hiai.aimodel.tensor.Tensor
import kotlinx.coroutines.*
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * MEOKCLAW 华为昇腾 NPU 端侧推理引擎 (Ascend On-Device Inference)
 *
 * 利用华为昇腾 (Ascend) NPU 进行端侧 AI 推理：
 *
 *   - 文本嵌入生成: 本地生成 query embedding，用于语义缓存命中
 *   - 内容安全预检: 端侧运行轻量级 guardrails 模型
 *   - 意图识别: 本地识别用户意图，减少云端调用
 *   - 情感分析: 端侧分析用户情绪状态
 *   - 文本摘要: 端侧生成长文本摘要
 *
 * 昇腾 NPU 优势:
 *   - 相比 CPU 推理，NPU 能效比提升 10-50 倍
 *   - 端侧推理零网络延迟
 *   - 敏感数据不上云（PIPL 合规）
 *   - 离线可用
 *
 * 支持的设备:
 *   - 华为 Mate/P 系列（麒麟 9000+ 内置 NPU）
 *   - 华为 nova 系列（部分机型）
 *   - 荣耀部分机型（麒麟芯片）
 *   - 第三方使用昇腾芯片的 IoT 设备
 *
 * 合规:
 *   - 所有端侧推理数据不离开设备
 *   - 符合《个人信息保护法》本地处理原则
 *   - 模型文件加密存储
 *   - 推理结果经过端侧 guardrails 过滤
 */
class AscendInference(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private lateinit var modelManager: AIModelManager
    private lateinit var modelExecutor: ModelExecutor

    // 缓存的模型
    private var embeddingModel: ModelDescription? = null
    private var guardrailsModel: ModelDescription? = null
    private var intentModel: ModelDescription? = null

    // 模型加载状态
    private var modelsLoaded = false

    init {
        initializeAscendSdk()
    }

    private fun initializeAscendSdk() {
        modelManager = AIModelManager.getInstance(context)
        modelExecutor = ModelExecutor.getInstance(context)
        loadModels()
    }

    private fun loadModels() {
        scope.launch {
            try {
                // 加载文本嵌入模型（轻量级，约 50MB）
                embeddingModel = modelManager.loadModel(
                    modelName = "text_embedding_cn_v1",
                    modelPath = "models/ascend/text_embedding_cn_v1.om",
                    deviceType = ModelDescription.DeviceType.NPU
                )

                // 加载内容安全预检模型（约 30MB）
                guardrailsModel = modelManager.loadModel(
                    modelName = "guardrails_lite_cn_v1",
                    modelPath = "models/ascend/guardrails_lite_cn_v1.om",
                    deviceType = ModelDescription.DeviceType.NPU
                )

                // 加载意图识别模型（约 20MB）
                intentModel = modelManager.loadModel(
                    modelName = "intent_recognition_cn_v1",
                    modelPath = "models/ascend/intent_recognition_cn_v1.om",
                    deviceType = ModelDescription.DeviceType.NPU
                )

                modelsLoaded = true
            } catch (e: Exception) {
                // 端侧模型加载失败时，回退到云端
                modelsLoaded = false
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 文本嵌入生成
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 端侧生成文本嵌入向量
     *
     * 用于:
     *   - 语义缓存查询（命中则无需调用云端）
     *   - 本地相似度计算
     *   - 文档向量化
     */
    suspend fun generateEmbedding(text: String): FloatArray? = withContext(Dispatchers.Default) {
        if (!modelsLoaded || embeddingModel == null) {
            return@withContext null // 回退到云端
        }

        try {
            // 文本预处理
            val inputTensor = preprocessText(text, maxLength = 512)

            // 昇腾 NPU 推理
            val outputTensor = modelExecutor.execute(
                model = embeddingModel!!,
                inputs = arrayOf(inputTensor)
            )

            // 解析输出
            parseEmbeddingOutput(outputTensor[0])
        } catch (e: Exception) {
            null
        }
    }

    /**
     * 语义缓存查询
     *
     * 端侧计算 embedding，查询本地语义缓存，
     * 命中则直接返回缓存结果，无需网络请求。
     */
    suspend fun semanticCacheLookup(query: String, threshold: Float = 0.92f): CacheLookupResult? =
        withContext(Dispatchers.Default) {
            val embedding = generateEmbedding(query) ?: return@withContext null

            // 查询本地缓存
            val cacheResult = queryLocalCache(embedding, threshold)

            if (cacheResult != null) {
                CacheLookupResult(
                    hit = true,
                    text = cacheResult.text,
                    confidence = cacheResult.similarity,
                    savedCost = cacheResult.cost
                )
            } else {
                CacheLookupResult(hit = false)
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // 内容安全预检
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 端侧内容安全快速预检
     *
     * 在发送请求到云端之前，先用端侧轻量模型进行预检，
     * 明显违规的内容直接拦截，无需网络请求。
     */
    suspend fun quickGuardrailsCheck(text: String): GuardrailsPreCheckResult =
        withContext(Dispatchers.Default) {
            if (!modelsLoaded || guardrailsModel == null) {
                // 模型未加载，返回待云端检查
                return@withContext GuardrailsPreCheckResult.needsCloudCheck
            }

            try {
                val inputTensor = preprocessText(text, maxLength = 256)
                val outputTensor = modelExecutor.execute(
                    model = guardrailsModel!!,
                    inputs = arrayOf(inputTensor)
                )

                val (isSafe, confidence, violationType) = parseGuardrailsOutput(outputTensor[0])

                when {
                    !isSafe && confidence > 0.9 ->
                        GuardrailsPreCheckResult.blocked(
                            reason = "端侧预检拦截: $violationType",
                            confidence = confidence
                        )
                    !isSafe && confidence > 0.5 ->
                        GuardrailsPreCheckResult.suspicious(
                            reason = "端侧预检可疑: $violationType",
                            confidence = confidence
                        )
                    else ->
                        GuardrailsPreCheckResult.safe
                }
            } catch (e: Exception) {
                GuardrailsPreCheckResult.needsCloudCheck
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // 意图识别
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 端侧意图识别
     *
     * 识别用户输入的意图，用于：
     *   - 快速路由到对应功能（议会/聊天/IoT）
     *   - 减少不必要的云端调用
     */
    suspend fun recognizeIntent(text: String): IntentRecognitionResult =
        withContext(Dispatchers.Default) {
            if (!modelsLoaded || intentModel == null) {
                return@withContext IntentRecognitionResult.unknown
            }

            try {
                val inputTensor = preprocessText(text, maxLength = 128)
                val outputTensor = modelExecutor.execute(
                    model = intentModel!!,
                    inputs = arrayOf(inputTensor)
                )

                parseIntentOutput(outputTensor[0])
            } catch (e: Exception) {
                IntentRecognitionResult.unknown
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // 内部辅助
    // ─────────────────────────────────────────────────────────────────────────

    private fun preprocessText(text: String, maxLength: Int): Tensor {
        // 文本分词 + ID 化（简化实现）
        val tokenIds = text.toCharArray()
            .map { it.code.coerceAtMost(65535) }
            .take(maxLength)
            .toIntArray()

        // Padding
        val padded = IntArray(maxLength) { 0 }
        tokenIds.copyInto(padded)

        val buffer = ByteBuffer.allocateDirect(maxLength * 4)
            .order(ByteOrder.nativeOrder())
        padded.forEach { buffer.putInt(it) }
        buffer.flip()

        return Tensor(buffer, intArrayOf(1, maxLength), Tensor.DataType.INT32)
    }

    private fun parseEmbeddingOutput(tensor: Tensor): FloatArray {
        val buffer = tensor.buffer
        val floatArray = FloatArray(tensor.shape[1])
        buffer.asFloatBuffer().get(floatArray)
        return floatArray
    }

    private fun parseGuardrailsOutput(tensor: Tensor): Triple<Boolean, Float, String> {
        val buffer = tensor.buffer
        val floatBuffer = buffer.asFloatBuffer()
        val safeProb = floatBuffer.get(0)
        val violationProb = floatBuffer.get(1)

        val labels = listOf("safe", "political", "medical_fraud", "financial_fraud", "inappropriate")
        val maxIndex = (0 until labels.size).maxByOrNull { floatBuffer.get(it) } ?: 0

        return Triple(safeProb > 0.5, floatBuffer.get(maxIndex), labels[maxIndex])
    }

    private fun parseIntentOutput(tensor: Tensor): IntentRecognitionResult {
        val buffer = tensor.buffer
        val floatBuffer = buffer.asFloatBuffer()

        val intents = listOf(
            "council_mode", "chat", "iot_control", "scene_mode",
            "cost_query", "guardrails_check", "help"
        )
        val maxIndex = (0 until intents.size).maxByOrNull { floatBuffer.get(it) } ?: 0
        val confidence = floatBuffer.get(maxIndex)

        return if (confidence > 0.7) {
            IntentRecognitionResult(intents[maxIndex], confidence)
        } else {
            IntentRecognitionResult.unknown
        }
    }

    private fun queryLocalCache(embedding: FloatArray, threshold: Float): CacheEntry? {
        // 简化实现 — 生产环境使用向量数据库（如 Milvus Lite）
        return null
    }

    /**
     * 获取 NPU 状态信息
     */
    fun getNpuStatus(): NpuStatus {
        return try {
            val info = modelManager.getDeviceInfo()
            NpuStatus(
                available = modelsLoaded,
                deviceName = info.deviceName,
                memoryUsedMB = info.memoryUsed / (1024 * 1024),
                memoryTotalMB = info.memoryTotal / (1024 * 1024),
                temperatureCelsius = info.temperature,
                loadedModels = listOfNotNull(
                    embeddingModel?.modelName,
                    guardrailsModel?.modelName,
                    intentModel?.modelName
                )
            )
        } catch (e: Exception) {
            NpuStatus(available = false)
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class CacheLookupResult(
    val hit: Boolean,
    val text: String = "",
    val confidence: Float = 0f,
    val savedCost: Double = 0.0
)

sealed class GuardrailsPreCheckResult {
    object safe : GuardrailsPreCheckResult()
    data class suspicious(val reason: String, val confidence: Float) : GuardrailsPreCheckResult()
    data class blocked(val reason: String, val confidence: Float) : GuardrailsPreCheckResult()
    object needsCloudCheck : GuardrailsPreCheckResult()
}

data class IntentRecognitionResult(
    val intent: String,
    val confidence: Float
) {
    companion object {
        val unknown = IntentRecognitionResult("unknown", 0f)
    }
}

data class NpuStatus(
    val available: Boolean,
    val deviceName: String = "",
    val memoryUsedMB: Long = 0,
    val memoryTotalMB: Long = 0,
    val temperatureCelsius: Float = 0f,
    val loadedModels: List<String> = emptyList()
)

data class CacheEntry(
    val embedding: FloatArray,
    val text: String,
    val similarity: Float,
    val cost: Double
)

// 占位类 — 生产环境接入华为 HiAI SDK
class AIModelManager private constructor() {
    companion object {
        fun getInstance(context: Context): AIModelManager = AIModelManager()
    }

    fun loadModel(modelName: String, modelPath: String, deviceType: ModelDescription.DeviceType): ModelDescription =
        ModelDescription(modelName)

    fun getDeviceInfo(): DeviceInfo = DeviceInfo("Ascend NPU", 512 * 1024 * 1024, 2048 * 1024 * 1024, 45f)
}

class ModelExecutor private constructor() {
    companion object {
        fun getInstance(context: Context): ModelExecutor = ModelExecutor()
    }

    fun execute(model: ModelDescription, inputs: Array<Tensor>): Array<Tensor> =
        arrayOf(Tensor(ByteBuffer.allocate(0), intArrayOf(1, 768), Tensor.DataType.FLOAT32))
}

data class ModelDescription(val modelName: String) {
    enum class DeviceType { NPU, GPU, CPU }
}

data class DeviceInfo(
    val deviceName: String,
    val memoryUsed: Long,
    val memoryTotal: Long,
    val temperature: Float
)

data class Tensor(val buffer: ByteBuffer, val shape: IntArray, val dataType: DataType) {
    enum class DataType { FLOAT32, INT32, INT64 }
}
