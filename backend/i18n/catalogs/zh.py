"""Chinese (Simplified / Traditional fallback) message catalog for MEOKCLAW API responses."""
from __future__ import annotations

MESSAGES: dict[str, str | dict[str, str]] = {
    # Generic
    "error.generic": "出了点问题，请稍后再试。",
    "error.not_found": "请求的资源不存在。",
    "error.unauthorized": "您无权执行此操作。",
    "error.forbidden": "访问被拒绝。",
    "error.rate_limited": "请求过于频繁，请放慢速度。",
    "error.timeout": "请求超时，请稍后再试。",
    "error.validation_failed": "验证失败，请检查输入后重试。",
    "error.service_unavailable": "服务暂时不可用，请稍后再试。",

    # Guardrails
    "guardrails.blocked": "您的请求已被安全系统拦截。",
    "guardrails.pii_detected": "检测到个人信息并已脱敏。",
    "guardrails.injection_detected": "检测到潜在的提示注入攻击。",
    "guardrails.content_filtered": "内容违反使用政策。",
    "guardrails.violation_prefix": "安全违规",

    # Dual-brain / Chat
    "chat.empty_message": "消息不能为空。",
    "chat.message_too_long": "消息长度超出限制。",
    "chat.model_unavailable": "所选模型当前不可用。",
    "chat.no_response": "[无响应]",
    "chat.thinking": "思考中……",

    # Council / Arena
    "council.consensus_reached": "已达成共识。",
    "council.no_consensus": "无法达成共识。",
    "council.model_failed": "模型响应失败。",
    "arena.winner_announced": "已公布胜出方。",
    "arena.no_winner": "未产生明确胜出方。",

    # Cost / Savings
    "cost.transparent": "费用透明",
    "cost.savings_beast": "省钱怪兽：相比 GPT-4 节省 95% 以上！",
    "cost.massive_savings": "大幅节省：比 GPT-4 便宜 90% 以上",
    "cost.great_savings": "非常划算：比 GPT-4 便宜 80% 以上",
    "cost.good_savings": "不错：比 GPT-4 便宜 50% 以上",

    # Auth
    "auth.invalid_key": "API 密钥无效。",
    "auth.key_expired": "API 密钥已过期。",
    "auth.budget_exhausted": "API 密钥额度已用完。",
    "auth.insufficient_scope": "API 密钥缺少所需权限。",

    # Batch
    "batch.submitted": "批处理任务提交成功。",
    "batch.invalid_request": "批处理请求格式无效。",
    "batch.job_not_found": "未找到批处理任务。",

    # Health
    "health.ok": "正常",
    "health.degraded": "降级",
    "health.down": "不可用",
}

VIOLATION_MESSAGES: dict[str, str] = {
    "pii": "您的请求中检测到个人信息。",
    "prompt_injection": "检测到潜在的提示注入或指令覆盖。",
    "content_filter": "您的请求包含违反使用政策的内容。",
    "custom": "触发了自定义安全规则。",
    "repetition_attack": "检测到潜在的重复攻击。",
}
