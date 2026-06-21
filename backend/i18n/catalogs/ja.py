"""Japanese message catalog for MEOKCLAW API responses."""
from __future__ import annotations

MESSAGES: dict[str, str | dict[str, str]] = {
    # Generic
    "error.generic": "問題が発生しました。もう一度お試しください。",
    "error.not_found": "要求されたリソースが見つかりません。",
    "error.unauthorized": "この操作を実行する権限がありません。",
    "error.forbidden": "アクセスが拒否されました。",
    "error.rate_limited": "リクエストが多すぎます。しばらくしてからお試しください。",
    "error.timeout": "リクエストがタイムアウトしました。もう一度お試しください。",
    "error.validation_failed": "検証に失敗しました。入力を確認してもう一度お試しください。",
    "error.service_unavailable": "サービスは一時的に利用できません。後でもう一度お試しください。",

    # Guardrails
    "guardrails.blocked": "安全システムによりリクエストがブロックされました。",
    "guardrails.pii_detected": "個人情報が検出され、編集されました。",
    "guardrails.injection_detected": "潜在的なプロンプトインジェクションが検出されました。",
    "guardrails.content_filtered": "コンテンツが利用規約に違反しています。",
    "guardrails.violation_prefix": "安全違反",

    # Dual-brain / Chat
    "chat.empty_message": "メッセージを空にすることはできません。",
    "chat.message_too_long": "メッセージが最大長を超えています。",
    "chat.model_unavailable": "選択したモデルは現在利用できません。",
    "chat.no_response": "[応答なし]",
    "chat.thinking": "考え中...",

    # Council / Arena
    "council.consensus_reached": "合意に達しました。",
    "council.no_consensus": "合意に達することができませんでした。",
    "council.model_failed": "モデルの応答に失敗しました。",
    "arena.winner_announced": "勝者が発表されました。",
    "arena.no_winner": "明確な勝者はいません。",

    # Cost / Savings
    "cost.transparent": "費用透明",
    "cost.savings_beast": "節約の怪物：GPT-4 と比較して 95% 以上節約しました！",
    "cost.massive_savings": "大幅な節約：GPT-4 より 90% 以上安い",
    "cost.great_savings": "素晴らしい節約：GPT-4 より 80% 以上安い",
    "cost.good_savings": "良好な節約：GPT-4 より 50% 以上安い",

    # Auth
    "auth.invalid_key": "API キーが無効です。",
    "auth.key_expired": "API キーの有効期限が切れました。",
    "auth.budget_exhausted": "API キーの予算を使い果たしました。",
    "auth.insufficient_scope": "API キーに必要なスコープがありません。",

    # Batch
    "batch.submitted": "バッチジョブが正常に送信されました。",
    "batch.invalid_request": "バッチリクエストの形式が無効です。",
    "batch.job_not_found": "バッチジョブが見つかりません。",

    # Health
    "health.ok": "正常",
    "health.degraded": "低下",
    "health.down": "停止",
}

VIOLATION_MESSAGES: dict[str, str] = {
    "pii": "リクエストに個人情報が含まれているのを検出しました。",
    "prompt_injection": "潜在的なプロンプトインジェクションまたは指示の上書きを検出しました。",
    "content_filter": "リクエストに利用規約に違反するコンテンツが含まれています。",
    "custom": "カスタム安全ルールがトリガーされました。",
    "repetition_attack": "潜在的な反復攻撃を検出しました。",
}
