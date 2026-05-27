package com.meokclaw.china.bytedance

import android.content.Context
import kotlinx.coroutines.*
import java.util.regex.Pattern

/**
 * MEOKCLAW 字节跳动专项内容合规护栏 (ByteDance Content Compliance)
 *
 * 针对字节跳动生态（抖音、飞书、今日头条、TikTok 国内版）的
 * 专项内容合规层：
 *
 *   - 抖音内容政策: 符合《网络视听节目内容审核通则》
 *   - 直播合规: 符合《网络直播营销管理办法》
 *   - 广告合规: 符合《互联网广告管理办法》
 *   - 未成年人保护: 不得诱导未成年人消费、沉迷
 *   - 飞书企业数据: 符合企业数据安全规范
 *
 * 字节跳动特有的合规要求:
 *   1. 绝对化用语禁令: 不得使用"第一""最好""全网最低"等
 *   2. 医疗/保健品: 不得宣称疗效，必须标注"本产品不能替代药物"
 *   3. 金融理财: 不得承诺收益，必须标注"投资有风险"
 *   4. 食品: 不得宣称保健功能
 *   5. 教育培训: 不得承诺效果，不得制造焦虑
 *   6. 虚假营销: 不得虚构原价、限时假象
 *
 * 法律依据:
 *   - 《网络直播营销管理办法（试行）》
 *   - 《互联网广告管理办法》
 *   - 《网络视听节目内容审核通则》
 *   - 《未成年人保护法》网络保护专章
 *   - 字节跳动社区自律公约
 */
class ByteDanceGuardrails(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // ─────────────────────────────────────────────────────────────────────────
    // 绝对化用语模式
    // ─────────────────────────────────────────────────────────────────────────
    private val absoluteTerms = listOf(
        "最好", "第一", "顶级", "极品", "极致", "绝对", "全网最低", "史上最低",
        "100%有效", "保证治愈", "绝对安全", "零风险", "稳赚不赔",
        "国家级", "最高级", "最佳", "最优", "最先进", "最新科学",
        "唯一", "首选", "首家", "独家", "独创", "绝无仅有"
    )

    // ─────────────────────────────────────────────────────────────────────────
    // 医疗虚假宣传模式
    // ─────────────────────────────────────────────────────────────────────────
    private val medicalFraudPatterns = listOf(
        Pattern.compile("(?:治愈|根治|治好).*(?:癌症|肿瘤|糖尿病|高血压|艾滋病)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:秘方|偏方|祖传).*(?:神医|神药)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:无效退款|包治百病|药到病除)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:不打针|不吃药|不手术).*(?:治愈|康复)", Pattern.CASE_INSENSITIVE),
    )

    // ─────────────────────────────────────────────────────────────────────────
    // 金融违规承诺模式
    // ─────────────────────────────────────────────────────────────────────────
    private val financialFraudPatterns = listOf(
        Pattern.compile("(?:保本|保息|稳赚|零风险).*(?:理财|投资|股票|基金)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:年化收益|回报率).*(?:\d+%|百分之\d+)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:内幕消息|庄家操盘|跟庄).*(?:股票|期货)", Pattern.CENSITIVE),
        Pattern.compile("(?:高额返利|拉人头|层级).*(?:投资|加盟)", Pattern.CASE_INSENSITIVE),
    )

    // ─────────────────────────────────────────────────────────────────────────
    // 教育培训焦虑营销
    // ─────────────────────────────────────────────────────────────────────────
    private val educationAnxietyPatterns = listOf(
        Pattern.compile("(?:不报名|不来).*(?:就晚了|后悔|输在起跑线)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:最后\d+个名额|限时抢购|马上截止)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:你的孩子|你的同学).*(?:都在学|已经会了)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?: guarantee|保证).*(?:提分|上岸|录取)", Pattern.CASE_INSENSITIVE),
    )

    // ─────────────────────────────────────────────────────────────────────────
    // 未成年人诱导模式
    // ─────────────────────────────────────────────────────────────────────────
    private val minorExploitationPatterns = listOf(
        Pattern.compile("(?:小朋友|小学生|初中生).*(?:快让|叫).*(?:爸爸妈妈|家长).*(?:买|充值)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:偷偷|背着爸妈).*(?:充值|打赏|买)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:送皮肤|送装备|免费领).*(?:扫码|点击)", Pattern.CASE_INSENSITIVE),
    )

    // ─────────────────────────────────────────────────────────────────────────
    // 政治敏感模式（继承自百度/通用）
    // ─────────────────────────────────────────────────────────────────────────
    private val politicalPatterns = listOf(
        Pattern.compile("颠覆国家.*政权|分裂.*祖国", Pattern.CASE_INSENSITIVE),
        Pattern.compile("台独|港独|藏独|疆独", Pattern.CASE_INSENSITIVE),
        Pattern.compile("邪教.*组织|法轮功", Pattern.CASE_INSENSITIVE),
        Pattern.compile("恶意.*攻击.*党和政府", Pattern.CASE_INSENSITIVE),
    )

    // ─────────────────────────────────────────────────────────────────────────
    // 主审查接口
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 全面内容审查 — 适用于所有字节跳动生态内容
     */
    fun sanitize(text: String?): String? {
        if (text.isNullOrBlank()) return text

        val violations = mutableListOf<ByteDanceViolation>()

        // 1. 政治敏感检查
        checkPoliticalSensitivity(text)?.let { violations.addAll(it) }

        // 2. 绝对化用语检查
        checkAbsoluteTerms(text)?.let { violations.addAll(it) }

        // 3. 医疗虚假宣传检查
        checkMedicalFraud(text)?.let { violations.addAll(it) }

        // 4. 金融违规承诺检查
        checkFinancialFraud(text)?.let { violations.addAll(it) }

        // 5. 教育焦虑营销检查
        checkEducationAnxiety(text)?.let { violations.addAll(it) }

        // 6. 未成年人诱导检查
        checkMinorExploitation(text)?.let { violations.addAll(it) }

        // 严重违规直接拦截
        val critical = violations.filter { it.severity == ViolationSeverity.CRITICAL }
        if (critical.isNotEmpty()) {
            return null
        }

        // 警告级违规返回清洗后文本
        val warnings = violations.filter { it.severity == ViolationSeverity.WARNING }
        return if (warnings.isNotEmpty()) {
            applyRedactions(text, warnings)
        } else {
            text
        }
    }

    /**
     * 快速检查
     */
    fun check(text: String): ByteDanceCheckResult {
        val violations = mutableListOf<ByteDanceViolation>()

        checkPoliticalSensitivity(text)?.let { violations.addAll(it) }
        checkAbsoluteTerms(text)?.let { violations.addAll(it) }
        checkMedicalFraud(text)?.let { violations.addAll(it) }
        checkFinancialFraud(text)?.let { violations.addAll(it) }
        checkEducationAnxiety(text)?.let { violations.addAll(it) }
        checkMinorExploitation(text)?.let { violations.addAll(it) }

        val blocked = violations.any { it.severity == ViolationSeverity.CRITICAL }
        val cleanedText = if (blocked) "" else applyRedactions(text, violations)

        // 添加合规建议
        val suggestions = generateComplianceSuggestions(violations)

        return ByteDanceCheckResult(
            blocked = blocked,
            cleanedText = cleanedText,
            violations = violations,
            enforcementLevel = if (blocked) "block" else if (violations.isNotEmpty()) "redact" else "pass",
            suggestions = suggestions
        )
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 专项审查方法
    // ─────────────────────────────────────────────────────────────────────────

    private fun checkPoliticalSensitivity(text: String): List<ByteDanceViolation>? {
        val violations = mutableListOf<ByteDanceViolation>()
        politicalPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(ByteDanceViolation(
                    type = ViolationType.POLITICAL_SENSITIVITY,
                    severity = ViolationSeverity.CRITICAL,
                    description = "政治敏感内容: ${matcher.group()}",
                    ruleId = "BD-POL-001",
                    matchedText = matcher.group(),
                    platform = Platform.ALL
                ))
            }
        }
        return if (violations.isNotEmpty()) violations else null
    }

    private fun checkAbsoluteTerms(text: String): List<ByteDanceViolation>? {
        val violations = mutableListOf<ByteDanceViolation>()
        absoluteTerms.forEach { term ->
            if (text.contains(term)) {
                violations.add(ByteDanceViolation(
                    type = ViolationType.ABSOLUTE_TERM,
                    severity = ViolationSeverity.WARNING,
                    description = "使用绝对化用语: $term",
                    ruleId = "BD-ADS-001",
                    matchedText = term,
                    platform = Platform.DOUYIN
                ))
            }
        }
        return if (violations.isNotEmpty()) violations else null
    }

    private fun checkMedicalFraud(text: String): List<ByteDanceViolation>? {
        val violations = mutableListOf<ByteDanceViolation>()
        medicalFraudPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(ByteDanceViolation(
                    type = ViolationType.MEDICAL_MISINFORMATION,
                    severity = ViolationSeverity.CRITICAL,
                    description = "医疗虚假宣传: ${matcher.group()}",
                    ruleId = "BD-MED-001",
                    matchedText = matcher.group(),
                    platform = Platform.DOUYIN
                ))
            }
        }
        return if (violations.isNotEmpty()) violations else null
    }

    private fun checkFinancialFraud(text: String): List<ByteDanceViolation>? {
        val violations = mutableListOf<ByteDanceViolation>()
        financialFraudPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(ByteDanceViolation(
                    type = ViolationType.FINANCIAL_FRAUD,
                    severity = ViolationSeverity.CRITICAL,
                    description = "金融违规承诺: ${matcher.group()}",
                    ruleId = "BD-FIN-001",
                    matchedText = matcher.group(),
                    platform = Platform.DOUYIN
                ))
            }
        }
        return if (violations.isNotEmpty()) violations else null
    }

    private fun checkEducationAnxiety(text: String): List<ByteDanceViolation>? {
        val violations = mutableListOf<ByteDanceViolation>()
        educationAnxietyPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(ByteDanceViolation(
                    type = ViolationType.EDUCATION_ANXIETY,
                    severity = ViolationSeverity.WARNING,
                    description = "教育焦虑营销: ${matcher.group()}",
                    ruleId = "BD-EDU-001",
                    matchedText = matcher.group(),
                    platform = Platform.DOUYIN
                ))
            }
        }
        return if (violations.isNotEmpty()) violations else null
    }

    private fun checkMinorExploitation(text: String): List<ByteDanceViolation>? {
        val violations = mutableListOf<ByteDanceViolation>()
        minorExploitationPatterns.forEach { pattern ->
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                violations.add(ByteDanceViolation(
                    type = ViolationType.MINOR_EXPLOITATION,
                    severity = ViolationSeverity.CRITICAL,
                    description = "诱导未成年人: ${matcher.group()}",
                    ruleId = "BD-MIN-001",
                    matchedText = matcher.group(),
                    platform = Platform.DOUYIN
                ))
            }
        }
        return if (violations.isNotEmpty()) violations else null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 合规建议生成
    // ─────────────────────────────────────────────────────────────────────────

    private fun generateComplianceSuggestions(violations: List<ByteDanceViolation>): List<String> {
        val suggestions = mutableListOf<String>()

        violations.forEach { v ->
            when (v.type) {
                ViolationType.ABSOLUTE_TERM ->
                    suggestions.add("建议将'${v.matchedText}'替换为更客观的描述，如'深受用户喜爱'"")
                ViolationType.MEDICAL_MISINFORMATION ->
                    suggestions.add("医疗相关内容必须标注'本产品不能替代药物'，不得宣称疗效")
                ViolationType.FINANCIAL_FRAUD ->
                    suggestions.add("金融相关内容必须标注'投资有风险，入市需谨慎'，不得承诺收益")
                ViolationType.EDUCATION_ANXIETY ->
                    suggestions.add("教育推广不得制造焦虑，不得承诺升学/提分效果")
                ViolationType.MINOR_EXPLOITATION ->
                    suggestions.add("严禁诱导未成年人消费，如涉及未成年人需家长监护")
                else -> {}
            }
        }

        return suggestions.distinct()
    }

    private fun applyRedactions(text: String, violations: List<ByteDanceViolation>): String {
        var result = text
        violations.forEach { v ->
            v.matchedText?.let { matched ->
                result = result.replace(matched, "[已优化]")
            }
        }
        return result
    }

    companion object {
        // 字节跳动内容审核 API 配置
        const val BYTEDANCE_CENSOR_API = "https://open.douyin.com/api/VideoUpload/"
    }
}

// ─────────────────────────────────────────────────────────────────────────
// 数据模型
// ─────────────────────────────────────────────────────────────────────────
data class ByteDanceViolation(
    val type: ViolationType,
    val severity: ViolationSeverity,
    val description: String,
    val ruleId: String,
    val matchedText: String? = null,
    val platform: Platform
)

data class ByteDanceCheckResult(
    val blocked: Boolean,
    val cleanedText: String,
    val violations: List<ByteDanceViolation>,
    val enforcementLevel: String,
    val suggestions: List<String>
)

enum class ViolationType {
    POLITICAL_SENSITIVITY,
    ABSOLUTE_TERM,
    MEDICAL_MISINFORMATION,
    FINANCIAL_FRAUD,
    EDUCATION_ANXIETY,
    MINOR_EXPLOITATION,
    COPYRIGHT_VIOLATION,
    PRIVACY_VIOLATION
}

enum class ViolationSeverity {
    WARNING,
    CRITICAL
}

enum class Platform {
    DOUYIN,    // 抖音
    LARK,      // 飞书
    TOUTIAO,   // 今日头条
    ALL        // 全平台
}
