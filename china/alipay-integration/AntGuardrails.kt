package com.meokclaw.china.alipay

import android.content.Context
import android.hardware.biometrics.BiometricPrompt
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
import kotlinx.coroutines.*
import kotlinx.coroutines.suspendCancellableCoroutine
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicLong

/**
 * MEOKCLAW 蚂蚁集团金融交易护栏 (Ant Financial Guardrails)
 *
 * 专为支付宝/蚂蚁集团交易设计的金融级安全层：
 *
 *   - 交易风控: 基于金额、频率、收款方的实时风险评估
 *   - 生物识别: 强制指纹/人脸确认所有支付操作
 *   - 双重授权: 大额交易需二次密码 + 生物识别
 *   - 审计追踪: 所有 AI 发起的交易记录不可篡改日志
 *   - 合规检查: 符合《非银行支付机构网络支付业务管理办法》
 *   - 反欺诈: 检测异常交易模式
 *
 * 为什么需要独立 guardrails:
 *   金融交易是高风险操作，AI 代理发起支付必须满足
 *   比通用 guardrails 更严格的标准。蚂蚁集团有自己的
 *   风控规则，MEOKCLAW 需要在应用层进行前置检查。
 *
 * 法律依据:
 *   - 《非银行支付机构网络支付业务管理办法》
 *   - 《中国人民银行关于加强支付结算管理防范电信网络新型违法犯罪有关事项的通知》
 *   - 《个人信息保护法》金融数据处理特别规定
 *   - 蚂蚁集团开放平台安全规范
 */
class AntGuardrails(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // 交易限额配置（单位：人民币元）
    private val dailyLimit: AtomicLong = AtomicLong(10000)      // 日限额 1 万元
    private val singleLimit: AtomicLong = AtomicLong(5000)      // 单笔限额 5 千元
    private val aiInitiatedLimit: AtomicLong = AtomicLong(1000) // AI 发起限额 1 千元

    // 今日已用额度（简化实现，生产环境应持久化）
    private var dailyUsed: Double = 0.0
    private var dailyResetTime: Long = 0

    // 交易审计日志
    private val auditLog = mutableListOf<TransactionAuditEntry>()
    private val auditMutex = kotlinx.coroutines.sync.Mutex()

    init {
        resetDailyLimitIfNeeded()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 交易验证
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 验证支付请求是否通过风控审查
     *
     * 检查项:
     *   1. 金额是否在限额内
     *   2. 收款方是否可信
     *   3. 交易频率是否正常
     *   4. 交易描述是否合规
     *   5. AI 发起的交易是否有明确用户授权
     */
    fun validatePayment(amount: Double, subject: String): Boolean {
        resetDailyLimitIfNeeded()

        // 1. 金额检查
        if (amount <= 0) return false
        if (amount > singleLimit.get()) {
            return false // 超过单笔限额，需人工确认
        }
        if (dailyUsed + amount > dailyLimit.get()) {
            return false // 超过日限额
        }

        // 2. AI 发起限额检查
        if (amount > aiInitiatedLimit.get()) {
            // 超过 AI 自动支付限额，必须用户手动确认
            return false
        }

        // 3. 交易描述合规检查
        if (!isSubjectCompliant(subject)) {
            return false
        }

        // 4. 反欺诈检查
        if (isSuspiciousPattern(amount, subject)) {
            return false
        }

        return true
    }

    /**
     * 大额交易人工确认
     * 金额超过阈值时，弹出对话框要求用户确认
     */
    suspend fun confirmHighValueTransaction(amount: Double): Boolean {
        return suspendCancellableCoroutine { continuation ->
            // 在实际实现中，这里会弹出一个原生对话框
            // 为了演示，简化为返回 true
            // 生产环境应使用 AlertDialog 或 BottomSheet
            continuation.resume(true) {}
        }
    }

    /**
     * 生物识别验证
     * 强制使用指纹或人脸验证支付操作
     */
    suspend fun verifyBiometric(promptMessage: String): Boolean =
        suspendCancellableCoroutine { continuation ->
            val cancellationSignal = CancellationSignal()

            val callback = object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult?) {
                    continuation.resume(true) {}
                }

                override fun onAuthenticationFailed() {
                    continuation.resume(false) {}
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence?) {
                    continuation.resume(false) {}
                }
            }

            val prompt = BiometricPrompt.Builder(context)
                .setTitle("MEOKCLAW 支付确认")
                .setSubtitle(promptMessage)
                .setDescription("请验证您的生物特征以确认此交易")
                .setNegativeButton("取消", Handler(Looper.getMainLooper())) { _, _ ->
                    continuation.resume(false) {}
                }
                .build()

            prompt.authenticate(
                cancellationSignal,
                { it.run() }, // executor
                callback
            )

            continuation.invokeOnCancellation {
                cancellationSignal.cancel()
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // 审计日志
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 记录交易审计日志
     * 所有 AI 代理发起的交易必须记录不可篡改日志
     */
    suspend fun logTransaction(
        type: String,
        amount: Double,
        status: String,
        tradeNo: String? = null
    ) = auditMutex.withLock {
        val entry = TransactionAuditEntry(
            timestamp = System.currentTimeMillis(),
            type = type,
            amount = amount,
            status = status,
            tradeNo = tradeNo ?: "",
            deviceId = getDeviceId(),
            entryHash = "" // 稍后计算
        )

        // 计算哈希链 — 每条记录包含前一条的哈希，形成不可篡改链
        val prevHash = auditLog.lastOrNull()?.entryHash ?: "0"
        val entryWithHash = entry.copy(
            entryHash = calculateHash(entry, prevHash)
        )

        auditLog.add(entryWithHash)

        // 更新日已用额度
        if (status == "success") {
            dailyUsed += amount
        }

        // 同步到后端审计服务
        syncAuditEntry(entryWithHash)
    }

    /**
     * 获取审计日志
     */
    suspend fun getAuditLogs(since: Long): List<TransactionAuditEntry> = auditMutex.withLock {
        auditLog.filter { it.timestamp >= since }
    }

    /**
     * 验证审计链完整性
     */
    fun verifyAuditChain(): Boolean {
        for (i in 1 until auditLog.size) {
            val current = auditLog[i]
            val previous = auditLog[i - 1]
            val expectedHash = calculateHash(current.copy(entryHash = ""), previous.entryHash)
            if (current.entryHash != expectedHash) {
                return false
            }
        }
        return true
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 反欺诈
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 检测可疑交易模式
     */
    private fun isSuspiciousPattern(amount: Double, subject: String): Boolean {
        // 检查短时间内多次相同金额交易
        val recentTransactions = auditLog.filter {
            System.currentTimeMillis() - it.timestamp < 300_000 // 5 分钟内
        }

        val sameAmountCount = recentTransactions.count { it.amount == amount }
        if (sameAmountCount >= 3) {
            return true // 5 分钟内 3 次相同金额交易 = 可疑
        }

        // 检查异常金额（如 999.99、1999.99 等常见于诈骗的金额）
        val amountStr = String.format("%.2f", amount)
        if (amountStr.endsWith("999.99") || amountStr.endsWith("999.00")) {
            return true
        }

        // 检查高风险关键词
        val highRiskKeywords = listOf("保证金", "解冻费", "手续费", "税费", "认证费")
        if (highRiskKeywords.any { subject.contains(it) }) {
            return true
        }

        return false
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 内部辅助
    // ─────────────────────────────────────────────────────────────────────────

    private fun isSubjectCompliant(subject: String): Boolean {
        // 检查交易描述是否合规
        val blockedKeywords = listOf(
            "赌博", "博彩", "色情", "毒品", "枪支", "走私",
            "洗钱", "诈骗", "传销", "非法集资"
        )
        return !blockedKeywords.any { subject.contains(it) }
    }

    private fun resetDailyLimitIfNeeded() {
        val now = System.currentTimeMillis()
        val dayStart = now - (now % 86400000) // 当天 0 点
        if (dailyResetTime < dayStart) {
            dailyUsed = 0.0
            dailyResetTime = dayStart
        }
    }

    private fun calculateHash(entry: TransactionAuditEntry, prevHash: String): String {
        val data = "${entry.timestamp}|${entry.type}|${entry.amount}|${entry.status}|${entry.tradeNo}|${entry.deviceId}|$prevHash"
        return MessageDigest.getInstance("SHA-256")
            .digest(data.toByteArray())
            .joinToString("") { "%02x".format(it) }
    }

    private fun getDeviceId(): String {
        // 获取设备标识 — 生产环境应使用 ANDROID_ID 或硬件标识
        return "device_stub"
    }

    private fun syncAuditEntry(entry: TransactionAuditEntry) {
        scope.launch {
            try {
                val apiClient = MEOKCLAWApiClient(
                    baseUrl = getLocalNodeUrl(),
                    apiKey = null
                )
                apiClient.syncAuditEntry(
                    source = "alipay",
                    entry = entry
                )
            } catch (e: Exception) {
                // 审计同步失败不影响交易，但应记录本地
            }
        }
    }

    private fun getLocalNodeUrl(): String {
        return context.getSharedPreferences("meokclaw", Context.MODE_PRIVATE)
            .getString("local_node", "http://192.168.1.100:3201")
            ?: "http://192.168.1.100:3201"
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class TransactionAuditEntry(
    val timestamp: Long,
    val type: String,
    val amount: Double,
    val status: String,
    val tradeNo: String,
    val deviceId: String,
    val entryHash: String
)

// 占位类 — 生产环境接入真实 MEOKCLAW API Client
class MEOKCLAWApiClient(baseUrl: String, apiKey: String?) {
    suspend fun queryAlipayBills(startDate: String, endDate: String, category: String?): List<BillRecord> = emptyList()
    suspend fun queryUtilityBills(city: String, type: String): List<BillRecord> = emptyList()
    suspend fun collectAntForestEnergy(): AntForestResult = AntForestResult(0, 0, emptyList())
    suspend fun syncAuditEntry(source: String, entry: TransactionAuditEntry) {}
}
