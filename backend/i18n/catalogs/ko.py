"""Korean message catalog for MEOKCLAW API responses."""
from __future__ import annotations

MESSAGES: dict[str, str | dict[str, str]] = {
    # Generic
    "error.generic": "문제가 발생했습니다. 다시 시도해 주세요.",
    "error.not_found": "요청한 리소스를 찾을 수 없습니다.",
    "error.unauthorized": "이 작업을 수행할 권한이 없습니다.",
    "error.forbidden": "접근이 거부되었습니다.",
    "error.rate_limited": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
    "error.timeout": "요청 시간이 초과되었습니다. 다시 시도해 주세요.",
    "error.validation_failed": "유효성 검사에 실패했습니다. 입력을 확인하고 다시 시도해 주세요.",
    "error.service_unavailable": "서비스를 일시적으로 사용할 수 없습니다. 나중에 다시 시도해 주세요.",

    # Guardrails
    "guardrails.blocked": "안전 시스템에 의해 요청이 차단되었습니다.",
    "guardrails.pii_detected": "개인정보가 감지되어 삭제 처리되었습니다.",
    "guardrails.injection_detected": "잠재적인 프롬프트 인젝션이 감지되었습니다.",
    "guardrails.content_filtered": "사용 정책을 위반하는 콘텐츠입니다.",
    "guardrails.violation_prefix": "안전 위반",

    # Dual-brain / Chat
    "chat.empty_message": "메시지는 비워둘 수 없습니다.",
    "chat.message_too_long": "메시지 길이가 최대 한도를 초과했습니다.",
    "chat.model_unavailable": "선택한 모델을 현재 사용할 수 없습니다.",
    "chat.no_response": "[응답 없음]",
    "chat.thinking": "생각 중...",

    # Council / Arena
    "council.consensus_reached": "합의에 도달했습니다.",
    "council.no_consensus": "합의에 도달할 수 없습니다.",
    "council.model_failed": "모델 응답에 실패했습니다.",
    "arena.winner_announced": "승자가 발표되었습니다.",
    "arena.no_winner": "명확한 승자가 없습니다.",

    # Cost / Savings
    "cost.transparent": "비용 투명",
    "cost.savings_beast": "절약 마스터: GPT-4 대비 95% 이상 절약했습니다!",
    "cost.massive_savings": "대폭적인 절약: GPT-4보다 90% 이상 저렴합니다",
    "cost.great_savings": "훌륭한 절약: GPT-4보다 80% 이상 저렴합니다",
    "cost.good_savings": "좋은 절약: GPT-4보다 50% 이상 저렴합니다",

    # Auth
    "auth.invalid_key": "API 키가 유효하지 않습니다.",
    "auth.key_expired": "API 키가 만료되었습니다.",
    "auth.budget_exhausted": "API 키 예산이 소진되었습니다.",
    "auth.insufficient_scope": "API 키에 필요한 권한이 없습니다.",

    # Batch
    "batch.submitted": "배치 작업이 성공적으로 제출되었습니다.",
    "batch.invalid_request": "배치 요청 형식이 잘못되었습니다.",
    "batch.job_not_found": "배치 작업을 찾을 수 없습니다.",

    # Health
    "health.ok": "정상",
    "health.degraded": "성능 저하",
    "health.down": "사용 불가",
}

VIOLATION_MESSAGES: dict[str, str] = {
    "pii": "요청에서 개인정보가 감지되었습니다.",
    "prompt_injection": "잠재적인 프롬프트 인젝션 또는 명령 덮어쓰기가 감지되었습니다.",
    "content_filter": "요청에 사용 정책을 위반하는 콘텐츠가 포함되어 있습니다.",
    "custom": "사용자 정의 안전 규칙이 트리거되었습니다.",
    "repetition_attack": "잠재적인 반복 공격이 감지되었습니다.",
}
