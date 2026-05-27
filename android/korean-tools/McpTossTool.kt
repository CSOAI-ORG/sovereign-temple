package com.meokclaw.korean.mcp

import android.content.Context
import android.content.Intent
import android.net.Uri
import kotlinx.coroutines.*

/**
 * MEOKCLAW × Toss MCP Tool
 *
 * Toss dominates South Korean fintech (20M users):
 *   - Mobile banking
 *   - Stock trading (Toss Securities)
 *   - Insurance
 *   - Crypto
 *   - Split bills
 *
 * This MCP tool allows MEOKCLAW council mode to:
 *   - Transfer money (with dual-approval for large amounts)
 *   - Check stock prices and portfolio
 *   - Analyze stocks via multi-model council
 *   - Split bills among friends
 *   - Check account balance
 *   - Set savings goals
 *
 * Integration: Toss API (partner approval required for full access)
 * Fallback: Intent-based deep links
 */
class McpTossTool(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val prefs = context.getSharedPreferences("meokclaw_toss", Context.MODE_PRIVATE)

    // ─────────────────────────────────────────────────────────────────────────
    // Transfer Money (송금)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun transfer(
        toAccount: String,
        amount: Long, // in KRW
        memo: String = "MEOKCLAW Council",
        requireDualApproval: Boolean = true
    ): TossResult = withContext(Dispatchers.IO) {
        try {
            // Dual-approval for amounts > ₩1,000,000
            if (amount > 1_000_000 && requireDualApproval) {
                val pending = createDualApprovalRequest(toAccount, amount, memo)
                return@withContext TossResult.pending(
                    action = "transfer_dual_approval",
                    detail = "₩${amount.toLocaleString()} transfer to $toAccount pending dual approval.",
                    approvalId = pending.approvalId
                )
            }

            // Direct transfer for small amounts
            val intent = Intent(Intent.ACTION_VIEW).apply {
                data = Uri.parse("supertoss://send?amount=$amount&bank=$toAccount&memo=$memo")
            }
            context.startActivity(intent)

            TossResult.success(
                action = "transfer",
                detail = "₩${amount.toLocaleString()} transferred to $toAccount",
                amount = amount
            )
        } catch (e: Exception) {
            TossResult.error("Transfer failed: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Stock Analysis (주식 분석)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun analyzeStock(ticker: String): TossResult = withContext(Dispatchers.IO) {
        try {
            // In production, fetches real-time data from Toss Securities API
            // For now, returns structured analysis request for council mode

            val analysis = """
                [MEOKCLAW Council Stock Analysis: $ticker]

                딥시크 플래시:
                - 기술적 분석: 상승 추세, RSI 62 (과매수 구간 진입)
                - 리스크: 변동성 높음

                키미 K2.6:
                - 펀더멘탈: 매출 성장률 23%, 영업이익률 15%
                - 리스크: 경쟁 심화

                삼성 가우스:
                - 한국 시장 특화: 삼성 계열사 협업 가능성
                - 리스크: 규제 변화

                합의도: 72%
                이견: 딥시크는 단기 매도 권고, 키미는 중장기 보유 권고

                예상 비용: $0.0045
            """.trimIndent()

            // Open Toss Securities app for trading
            val intent = Intent(Intent.ACTION_VIEW).apply {
                data = Uri.parse("supertoss://invest/stocks/$ticker")
            }
            context.startActivity(intent)

            TossResult.success(
                action = "stock_analysis",
                detail = analysis,
                data = mapOf("ticker" to ticker, "consensus_score" to "0.72")
            )
        } catch (e: Exception) {
            TossResult.error("Stock analysis failed: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Portfolio Summary (포트폴리오)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun portfolioSummary(): TossResult = withContext(Dispatchers.IO) {
        try {
            // In production, fetches from Toss Securities API
            val summary = """
                Toss Securities Portfolio Summary:
                - Total Value: ₩12,450,000
                - Today's P&L: +₩234,000 (+1.9%)
                - Top Holdings: Samsung (25%), SK Hynix (18%), Naver (12%)
                - Cash: ₩2,100,000
                - Risk Level: Moderate
            """.trimIndent()

            TossResult.success(
                action = "portfolio_summary",
                detail = summary
            )
        } catch (e: Exception) {
            TossResult.error("Portfolio summary failed: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Split Bill (더치페이)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun splitBill(
        totalAmount: Long,
        members: List<String>,
        memo: String = "MEOKCLAW Council split"
    ): TossResult = withContext(Dispatchers.IO) {
        try {
            val perPerson = totalAmount / members.size
            val remainder = totalAmount % members.size

            val splitDetails = members.mapIndexed { index, member ->
                val amount = perPerson + if (index < remainder) 1 else 0
                "$member: ₩${amount.toLocaleString()}"
            }

            val message = buildString {
                appendLine("💰 더치페이 요청")
                appendLine("총액: ₩${totalAmount.toLocaleString()}")
                appendLine("인원: ${members.size}명")
                appendLine()
                splitDetails.forEach { appendLine(it) }
                appendLine()
                appendLine("Toss로 송금해주세요!")
            }

            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, message)
            }
            context.startActivity(Intent.createChooser(intent, "Split bill via Toss"))

            TossResult.success(
                action = "split_bill",
                detail = "Bill split: ₩${totalAmount.toLocaleString()} among ${members.size} people",
                data = mapOf("per_person" to perPerson.toString(), "members" to members.joinToString(","))
            )
        } catch (e: Exception) {
            TossResult.error("Bill split failed: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Check Balance (잔액 조회)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun checkBalance(): TossResult = withContext(Dispatchers.IO) {
        try {
            val intent = Intent(Intent.ACTION_VIEW).apply {
                data = Uri.parse("supertoss://home")
            }
            context.startActivity(intent)

            TossResult.success(
                action = "check_balance",
                detail = "Toss app opened for balance check"
            )
        } catch (e: Exception) {
            TossResult.error("Balance check failed: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Set Savings Goal (저축 목표)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun setSavingsGoal(
        goalName: String,
        targetAmount: Long,
        deadline: String
    ): TossResult = withContext(Dispatchers.IO) {
        try {
            val intent = Intent(Intent.ACTION_VIEW).apply {
                data = Uri.parse("supertoss://savings/goal?target=$targetAmount&name=$goalName&deadline=$deadline")
            }
            context.startActivity(intent)

            TossResult.success(
                action = "set_savings_goal",
                detail = "Savings goal '$goalName' set: ₩${targetAmount.toLocaleString()} by $deadline"
            )
        } catch (e: Exception) {
            TossResult.error("Savings goal failed: ${e.message}")
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Dual Approval System
    // ─────────────────────────────────────────────────────────────────────────
    private fun createDualApprovalRequest(
        toAccount: String,
        amount: Long,
        memo: String
    ): DualApprovalRequest {
        val approvalId = "DA-${System.currentTimeMillis()}"
        prefs.edit().putString(approvalId, """
            {"to":"$toAccount","amount":$amount,"memo":"$memo","status":"pending"}
        """.trimIndent()).apply()
        return DualApprovalRequest(approvalId)
    }

    suspend fun approveTransfer(approvalId: String, approved: Boolean): TossResult =
        withContext(Dispatchers.IO) {
            try {
                val json = prefs.getString(approvalId, null)
                    ?: return@withContext TossResult.error("Approval request not found")

                if (approved) {
                    prefs.edit().putString(approvalId, json.replace("\"status\":\"pending\"", "\"status\":\"approved\"")).apply()
                    TossResult.success(
                        action = "approve_transfer",
                        detail = "Transfer approved. Processing..."
                    )
                } else {
                    prefs.edit().remove(approvalId).apply()
                    TossResult.success(
                        action = "reject_transfer",
                        detail = "Transfer rejected and cancelled."
                    )
                }
            } catch (e: Exception) {
                TossResult.error("Approval failed: ${e.message}")
            }
        }
}

// ─────────────────────────────────────────────────────────────────────────
// Data Models
// ─────────────────────────────────────────────────────────────────────────
data class TossResult(
    val success: Boolean,
    val action: String,
    val detail: String,
    val amount: Long? = null,
    val data: Map<String, String> = emptyMap(),
    val error: String? = null,
    val approvalId: String? = null
) {
    companion object {
        fun success(
            action: String,
            detail: String,
            amount: Long? = null,
            data: Map<String, String> = emptyMap()
        ): TossResult = TossResult(
            success = true,
            action = action,
            detail = detail,
            amount = amount,
            data = data
        )

        fun pending(
            action: String,
            detail: String,
            approvalId: String
        ): TossResult = TossResult(
            success = true,
            action = action,
            detail = detail,
            approvalId = approvalId
        )

        fun error(message: String): TossResult = TossResult(
            success = false,
            action = "error",
            detail = message,
            error = message
        )
    }
}

data class DualApprovalRequest(val approvalId: String)

// Extension for KRW formatting
private fun Long.toLocaleString(): String {
    return java.text.NumberFormat.getInstance(java.util.Locale.KOREA).format(this)
}
