package com.meokclaw.china.hms

import android.content.Context
import com.huawei.hms.aaid.HmsInstanceId
import com.huawei.hms.common.ApiException
import com.huawei.hms.push.HmsMessageService
import com.huawei.hms.push.RemoteMessage
import com.huawei.hms.support.account.AccountAuthManager
import com.huawei.hms.support.account.request.AccountAuthParams
import com.huawei.hms.support.account.request.AccountAuthParamsHelper
import com.huawei.hms.support.account.result.AuthAccount
import com.huawei.hms.support.account.service.AccountAuthService
import kotlinx.coroutines.*
import org.json.JSONObject

/**
 * MEOKCLAW HMS Core 桥接器
 *
 * 集成华为 HMS Core 核心服务:
 *   - Push Kit: 接收 MEOKCLAW 议会结果推送、实时通知
 *   - Account Kit: 华为账号一键登录，符合 PIPL 最小必要原则
 *   - Location Kit: (可选) 基于地理位置的智能决策
 *   - Analytics Kit: 匿名化使用分析
 *
 * 合规要点:
 *   - 用户同意后才获取 Push Token（个保法第13条）
 *   - 华为账号信息仅用于身份标识，不传输原始数据
 *   - 所有推送内容经过中国 guardrails 审查
 */
class HMSCoreBridge(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var authService: AccountAuthService
    private lateinit var apiClient: MEOKCLAWApiClient

    init {
        val authParams = AccountAuthParamsHelper(AccountAuthParams.DEFAULT_AUTH_REQUEST_PARAM)
            .setIdToken()
            .setAccessToken()
            .createParams()
        authService = AccountAuthManager.getService(context, authParams)
        apiClient = MEOKCLAWApiClient(
            baseUrl = getLocalNodeUrl(),
            apiKey = null
        )
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Push Kit — 消息推送服务
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 获取并注册 HMS Push Token 到 MEOKCLAW 后端
     * 必须在用户明确同意推送后才能调用（PIPL 合规）
     */
    fun registerPushToken(userConsented: Boolean) {
        if (!userConsented) {
            return // 严格遵守个保法 — 无同意不获取
        }

        scope.launch {
            try {
                val appId = context.getString(R.string.huawei_app_id)
                val token = HmsInstanceId.getInstance(context).getToken(appId, "HCM")

                if (token.isNotEmpty()) {
                    // 注册到 MEOKCLAW 后端
                    apiClient.registerDevice(
                        pushToken = token,
                        platform = "huawei_hms",
                        deviceType = "harmonyos_or_android"
                    )
                }
            } catch (e: ApiException) {
                // HMS 服务异常，记录但不崩溃
            }
        }
    }

    /**
     * 删除 Push Token（用户撤回同意时使用）
     */
    fun deletePushToken() {
        scope.launch {
            try {
                val appId = context.getString(R.string.huawei_app_id)
                HmsInstanceId.getInstance(context).deleteToken(appId, "HCM")
                apiClient.unregisterDevice(platform = "huawei_hms")
            } catch (e: ApiException) {
                // 静默处理
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Account Kit — 华为账号集成
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 华为账号静默登录（已登录用户）
     * 返回的 AuthAccount 仅用于生成匿名化用户标识符
     */
    fun silentSignIn(callback: (Result<HuaweiAccountInfo>) -> Unit) {
        val task = authService.silentSignIn()
        task.addOnSuccessListener { account ->
            val accountInfo = createAnonymousAccountInfo(account)
            callback(Result.success(accountInfo))
        }.addOnFailureListener { e ->
            callback(Result.failure(e))
        }
    }

    /**
     * 显式登录（弹窗授权）
     */
    fun explicitSignIn(activity: android.app.Activity, requestCode: Int) {
        val signInIntent = authService.signInIntent
        activity.startActivityForResult(signInIntent, requestCode)
    }

    /**
     * 处理登录结果
     */
    fun handleSignInResult(data: android.content.Intent?): Result<HuaweiAccountInfo> {
        return try {
            val account = AccountAuthManager.parseAuthResultFromIntent(data)
            if (account != null) {
                Result.success(createAnonymousAccountInfo(account))
            } else {
                Result.failure(Exception("Account is null"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 登出并清除本地数据
     */
    fun signOut() {
        authService.signOut()
        val prefs = context.getSharedPreferences("meokclaw_hms", Context.MODE_PRIVATE)
        prefs.edit().clear().apply()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 数据同步与合规
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 同步用户偏好到 MEOKCLAW 后端（符合 PIPL 最小必要原则）
     * 只传输匿名化 ID，不传输原始华为账号信息
     */
    fun syncUserPreferences(preferences: Map<String, String>) {
        scope.launch {
            try {
                val anonymousId = getAnonymousUserId()
                apiClient.syncPreferences(
                    userId = anonymousId,
                    preferences = preferences
                )
            } catch (e: Exception) {
                // 偏好同步失败不影响核心功能
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 内部辅助
    // ─────────────────────────────────────────────────────────────────────────

    private fun createAnonymousAccountInfo(account: AuthAccount): HuaweiAccountInfo {
        // 生成匿名化用户标识 — 原始华为 OpenID 永不离开设备
        val anonymousId = hashString(account.openId + "meokclaw_salt_2026")

        // 仅存储非敏感偏好数据
        val prefs = context.getSharedPreferences("meokclaw_hms", Context.MODE_PRIVATE)
        prefs.edit().putString("anonymous_id", anonymousId).apply()

        return HuaweiAccountInfo(
            anonymousId = anonymousId,
            displayName = maskDisplayName(account.displayName),
            avatarUri = account.avatarUriString ?: ""
        )
    }

    private fun getAnonymousUserId(): String {
        val prefs = context.getSharedPreferences("meokclaw_hms", Context.MODE_PRIVATE)
        return prefs.getString("anonymous_id", "") ?: ""
    }

    private fun maskDisplayName(name: String?): String {
        if (name.isNullOrEmpty()) return "华为用户"
        if (name.length <= 2) return "*${name.last()}"
        return "${name.first()}${"*".repeat(name.length - 2)}${name.last()}"
    }

    private fun hashString(input: String): String {
        return java.security.MessageDigest.getInstance("SHA-256")
            .digest(input.toByteArray())
            .joinToString("") { "%02x".format(it) }
    }

    private fun getLocalNodeUrl(): String {
        val prefs = context.getSharedPreferences("meokclaw", Context.MODE_PRIVATE)
        return prefs.getString("local_node", "http://192.168.1.100:3201")
            ?: "http://192.168.1.100:3201"
    }
}

// ─────────────────────────────────────────────────────────────────────────
// HMS Push 消息服务
// ─────────────────────────────────────────────────────────────────────────
class MEOKCLAWHmsMessageService : HmsMessageService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val guardrails by lazy { ChinaCulturalGuardrails(this) }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)

        val data = message.dataOfMap
        val notificationType = data["type"] ?: "general"
        val rawContent = data["content"] ?: ""

        // 所有推送内容必须经过 guardrails 审查
        val safeContent = guardrails.sanitize(rawContent) ?: run {
            // 不合规内容不显示
            return
        }

        when (notificationType) {
            "council_result" -> showCouncilResultNotification(safeContent, data)
            "cost_alert" -> showCostAlertNotification(safeContent, data)
            "guardrails_block" -> showGuardrailsBlockNotification(safeContent, data)
            "system_update" -> showSystemUpdateNotification(safeContent, data)
        }
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        // 新 token 注册到后端
        scope.launch {
            try {
                MEOKCLAWApiClient(
                    baseUrl = "http://localhost:3201",
                    apiKey = null
                ).registerDevice(
                    pushToken = token,
                    platform = "huawei_hms",
                    deviceType = "harmonyos_or_android"
                )
            } catch (e: Exception) {
                // 静默处理
            }
        }
    }

    private fun showCouncilResultNotification(content: String, data: Map<String, String>) {
        val title = data["title"] ?: "MEOKCLAW 议会结果"
        // 使用 HarmonyOS / Android NotificationManager 显示
        // 实现省略...
    }

    private fun showCostAlertNotification(content: String, data: Map<String, String>) {
        val title = data["title"] ?: "费用提醒"
        // 实现省略...
    }

    private fun showGuardrailsBlockNotification(content: String, data: Map<String, String>) {
        // guardrails 拦截通知 — 仅在 debug 模式显示
    }

    private fun showSystemUpdateNotification(content: String, data: Map<String, String>) {
        val title = data["title"] ?: "系统更新"
        // 实现省略...
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class HuaweiAccountInfo(
    val anonymousId: String,
    val displayName: String,
    val avatarUri: String
)
