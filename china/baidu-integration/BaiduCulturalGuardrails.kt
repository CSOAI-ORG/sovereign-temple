package com.meokclaw.china.baidu

import android.content.Context
import kotlinx.coroutines.*
import java.util.regex.Pattern

/**
 * MEOKCLAW 百度专项文化护栏 (Baidu Cultural Guardrails)
 *
 * 在百度文心/千帆集成之上的专项内容安全层：
 *   - 百度特有的内容政策适配
 *   - 百度搜索生态敏感词同步
 *   - 百度行业模型（法律/医疗/金融）专用审查规则
 *   - 百度 AI 伦理准则对齐
 *
 * 为什么需要专项 guardrails:
 *   百度作为搜索引擎巨头，对内容合规有极其严格的要求。
 *   百度云平台的内容审核标准比通用标准更细，涵盖：
 *     - 政治敏感内容（实时同步百度搜索屏蔽词库）
 *     - 虚假医疗/金融信息
 *     - 侵权内容（版权保护）
 *     - 低俗色情（百度贴吧/知道标准）
 *     - 广告欺诈
 *
 * 法律依据:
 *   - 《网络信息内容生态治理规定》
 *   - 《生成式人工智能服务管理暂行办法》
 *   - 《互联网信息服务算法推荐管理规定》
 *   - 百度云平台服务协议
 */
class BaiduCulturalGuardrails(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // 敏感词库 — 生产环境应从百度内容审核 API 实时同步
    private val politicalPatterns: List<Pattern> = listOf(
        Pattern.compile("颠覆国家.*政权", Pattern.CASE_INSENSITIVE),
        Pattern.compile("分裂.*祖国", Pattern.CASE_INSENSITIVE),
        Pattern.compile("台独|港独|藏独|疆独", Pattern.CASE_INSENSITIVE),
        Pattern.compile("邪教.*组织|法轮功", Pattern.CASE_INSENSITIVE),
        Pattern.compile("恐怖主义.*支持", Pattern.CASE_INSENSITIVE),
        Pattern.compile("恶意.*攻击.*党和政府", Pattern.CASE_INSENSITIVE),
    )

    // 医疗虚假信息模式
    private val medicalMisinformationPatterns: List<Pattern> = listOf(
        Pattern.compile("(?:神医|秘方|偏方).*治愈.*(?:癌症|艾滋病|糖尿病)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:百分百|绝对|保证).*(?:治愈|根除).*(?:癌症|肿瘤)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:无需手术|不用吃药).*(?:治愈|康复)", Pattern.CASE_INSENSITIVE),
    )

    // 金融欺诈模式
    private val financialFraudPatterns: List<Pattern> = listOf(
        Pattern.compile("(?:保本|稳赚|零风险).*(?:理财|投资|股票)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:内幕消息|庄家).*(?:股票|期货)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:高额回报|翻倍).*(?:投资|加盟)", Pattern.CASE_INSENSITIVE),
    )

    // 社会主义核心价值观 — 正面价值关键词（检测恶意曲解）
    private val coreSocialistValues = setOf(
        "富强", "民主", "文明", "和谐",
        "自由", "平等", "公正", "法治",
        "爱国", "敬业", "诚信", "友善"
    )

    // ─────────────────────────────────────────────────────────────────────────
    // 主审查接口
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 全面内容审查 — 适用于所有百度模型输出
     */
    fun sanitize(text: String?): String? {
        if (text.isNullOrBlank()) return text

        val violations = mutableListOf<BaiduViolation>()

        // 1. 政治敏感检查
        val politicalResult = checkPoliticalSensitivity(text)
        if (politicalResult.blocked) {
            violations.addAll(politicalResult.violations)
        }

        // 2. 医疗虚假信息检查
        val medicalResult = checkMedicalMisinformation(text)
        if (medicalResult.blocked) {
            violations.addAll(medicalResult.violations)
        }

        // 3. 金融欺诈检查
        val financialResult = checkFinancialFraud(text)
        if (financialResult.blocked) {
            violations.addAll(financialResult.violations)
        }

        // 4. 低俗色情检查（简化版 — 生产环境接入百度内容审核 API）
        val contentResult = checkInappropriateContent(text)
        if (contentResult.blocked) {
            violations.addAll(contentResult.violations)
        }

        // 如果有严重违规，直接拦截
        val criticalViolations = violations.filter { it.severity == ViolationSeverity.CRITICAL }
        if (criticalViolations.isNotEmpty()) {
            return null // 返回 null 表示内容被拦截
        }

        // 如果有警告级违规，返回清洗后的文本
        val warnings = violations.filter { it.severity == ViolationSeverity.WARNING }
        return if (warnings.isNotEmpty()) {
            applyRedactions(text, warnings)
        } else {
            text
        }
    }

    /**
     * 快速检查 — 用于输入预检
     */
    fun check(text: String): GuardrailsCheckResult {
        val violations = mutableListOf<BaiduViolation>()

        checkPoliticalSensitivity(text).violations.let { violations.addAll(it) }
        checkMedicalMisinformation(text).violations.let { violations.addAll(it) }
        checkFinancialFraud(text).violations.let { violations.addAll(it) }
        checkInappropriateContent(text).violations.let { violations.addAll(it) }

        val blocked = violations.any { it.severity == ViolationSeverity.CRITICAL }
        val cleanedText = if (blocked) "" else applyRedactions(text, violations)

        return GuardrailsCheckResult(
            blocked = blocked,
            cleanedText = cleanedText,
            violations = violations,
            enforcementLevel = if (blocked) "block" else if (violations.isNotEmpty()) "redact" else "pass"
        )
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 专项审查
    // ─────────────────────────────────────────────────────────────────────────

    private fun checkPoliticalSensitivity(text: String): CheckResult {
        val violations = mutableListOf<BaiduViolation>()

        politicalPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(
                    BaiduViolation(
                        type = ViolationType.POLITICAL_SENSITIVITY,
                        severity = ViolationSeverity.CRITICAL,
                        description = "检测到政治敏感内容: ${matcher.group()}",
                        ruleId = "BD-POL-001",
                        matchedText = matcher.group()
                    )
                )
            }
        }

        // 检查社会主义核心价值观的恶意曲解
        coreSocialistValues.forEach { value ->
            if (text.contains("反对$value") || text.contains("否定$value") || text.contains("$value 是骗局")) {
                violations.add(
                    BaiduViolation(
                        type = ViolationType.CORE_VALUES_ATTACK,
                        severity = ViolationSeverity.CRITICAL,
                        description = "恶意曲解社会主义核心价值观: $value",
                        ruleId = "BD-CSV-001",
                        matchedText = value
                    )
                )
            }
        }

        return CheckResult(blocked = violations.any { it.severity == ViolationSeverity.CRITICAL }, violations)
    }

    private fun checkMedicalMisinformation(text: String): CheckResult {
        val violations = mutableListOf<BaiduViolation>()

        medicalMisinformationPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(
                    BaiduViolation(
                        type = ViolationType.MEDICAL_MISINFORMATION,
                        severity = ViolationSeverity.CRITICAL,
                        description = "检测到医疗虚假信息: ${matcher.group()}",
                        ruleId = "BD-MED-001",
                        matchedText = matcher.group()
                    )
                )
            }
        }

        return CheckResult(blocked = violations.any { it.severity == ViolationSeverity.CRITICAL }, violations)
    }

    private fun checkFinancialFraud(text: String): CheckResult {
        val violations = mutableListOf<BaiduViolation>()

        financialFraudPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(
                    BaiduViolation(
                        type = ViolationType.FINANCIAL_FRAUD,
                        severity = ViolationSeverity.CRITICAL,
                        description = "检测到金融欺诈信息: ${matcher.group()}",
                        ruleId = "BD-FIN-001",
                        matchedText = matcher.group()
                    )
                )
            }
        }

        return CheckResult(blocked = violations.any { it.severity == ViolationSeverity.CRITICAL }, violations)
    }

    private fun checkInappropriateContent(text: String): CheckResult {
        val violations = mutableListOf<BaiduViolation>()

        // 简化实现 — 生产环境接入百度内容审核 API
        // https://ai.baidu.com/tech/textcensoring

        return CheckResult(blocked = false, violations)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 数据主权验证
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 验证文本内容是否符合数据主权要求
     * 检测是否包含可能触发跨境传输的敏感数据类型
     */
    fun validateDataSovereignty(text: String): Boolean {
        // 检测国家秘密相关关键词
        val stateSecretPatterns = listOf(
            "机密文件", "内部资料", "国家秘密", "涉密"
        )
        stateSecretPatterns.forEach { pattern ->
            if (text.contains(pattern)) {
                return false
            }
        }

        // 检测大规模个人信息（可能触发跨境评估）
        val idPattern = Pattern.compile("\\d{17}[\\dXx]")
        val idMatcher = idPattern.matcher(text)
        var idCount = 0
        while (idMatcher.find()) idCount++
        if (idCount >= 10) { // 超过 10 个身份证号视为大规模个人信息
            return false
        }

        return true
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 格式化输出
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 格式化回复，使其符合百度平台和中国文化规范
     */
    fun formatResponse(text: String, politenessLevel: PolitenessLevel = PolitenessLevel.AUTO): String {
        var formatted = text

        // 确保使用中文标点
        formatted = formatted.replace(", ", "，").replace(". ", "。")
            .replace("? ", "？").replace("! ", "！")

        // 根据礼貌级别调整
        when (politenessLevel) {
            PolitenessLevel.FORMAL -> {
                if (!formatted.startsWith("您好") && !formatted.startsWith("尊敬")) {
                    formatted = "您好，$formatted"
                }
            }
            PolitenessLevel.POLITE -> {
                // 保持原样，已足够礼貌
            }
            PolitenessLevel.CASUAL -> {
                // 使用更随意的表达
            }
            PolitenessLevel.AUTO -> {
                // 自动检测不调整
            }
        }

        // 添加免责声明（医疗/法律/金融内容）
        if (containsRegulatedContent(formatted)) {
            formatted += "\n\n【免责声明】以上内容仅供参考，不构成专业建议。如有需要，请咨询相关领域专业人士。"
        }

        return formatted
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 内部辅助
    // ─────────────────────────────────────────────────────────────────────────

    private fun applyRedactions(text: String, violations: List<BaiduViolation>): String {
        var result = text
        violations.forEach { violation ->
            violation.matchedText?.let { matched ->
                result = result.replace(matched, "[已脱敏]")
            }
        }
        return result
    }

    private fun containsRegulatedContent(text: String): Boolean {
        val regulatedKeywords = listOf("医疗建议", "法律建议", "投资建议", "处方", "诊断")
        return regulatedKeywords.any { text.contains(it) }
    }

    companion object {
        // 百度内容审核 API 配置
        const val BAIDU_CENSOR_API = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined"
        const val BAIDU_CENSOR_APP_ID = ""
        const val BAIDU_CENSOR_API_KEY = ""
        const val BAIDU_CENSOR_SECRET_KEY = ""
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class BaiduViolation(
    val type: ViolationType,
    val severity: ViolationSeverity,
    val description: String,
    val ruleId: String,
    val matchedText: String? = null
)

data class CheckResult(
    val blocked: Boolean,
    val violations: List<BaiduViolation>
)

data class GuardrailsCheckResult(
    val blocked: Boolean,
    val cleanedText: String,
    val violations: List<BaiduViolation>,
    val enforcementLevel: String
)

enum class ViolationType {
    POLITICAL_SENSITIVITY,
    CORE_VALUES_ATTACK,
    MEDICAL_MISINFORMATION,
    FINANCIAL_FRAUD,
    INAPPROPRIATE_CONTENT,
    COPYRIGHT_VIOLATION,
    PII_EXPOSURE
}

enum class ViolationSeverity {
    WARNING,    // 警告 — 可清洗后放行
    CRITICAL    // 严重 — 必须拦截
}
