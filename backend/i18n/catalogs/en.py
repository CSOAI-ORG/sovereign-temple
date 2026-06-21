"""English message catalog for MEOKCLAW API responses.

Mirrors frontend i18n keys to ensure consistent localization
across client and server boundaries.
"""
from __future__ import annotations

MESSAGES: dict[str, str | dict[str, str]] = {
    # Generic
    "error.generic": "Something went wrong. Please try again.",
    "error.not_found": "The requested resource was not found.",
    "error.unauthorized": "You are not authorized to perform this action.",
    "error.forbidden": "Access denied.",
    "error.rate_limited": "Too many requests. Please slow down.",
    "error.timeout": "The request timed out. Please try again.",
    "error.validation_failed": "Validation failed. Check your input and try again.",
    "error.service_unavailable": "Service temporarily unavailable. Please try again later.",

    # Guardrails
    "guardrails.blocked": "Your request was blocked by our safety system.",
    "guardrails.pii_detected": "Personal information was detected and redacted.",
    "guardrails.injection_detected": "Potential prompt injection detected.",
    "guardrails.content_filtered": "Content violates usage policies.",
    "guardrails.violation_prefix": "Safety violation",

    # Dual-brain / Chat
    "chat.empty_message": "Message cannot be empty.",
    "chat.message_too_long": "Message exceeds maximum length.",
    "chat.model_unavailable": "The selected model is currently unavailable.",
    "chat.no_response": "[No response]",
    "chat.thinking": "Thinking...",

    # Council / Arena
    "council.consensus_reached": "Consensus reached.",
    "council.no_consensus": "No consensus could be reached.",
    "council.model_failed": "Model failed to respond.",
    "arena.winner_announced": "Winner announced.",
    "arena.no_winner": "No clear winner.",

    # Cost / Savings
    "cost.transparent": "Cost transparent",
    "cost.savings_beast": "SAVINGS BEAST: You saved 95%+ vs GPT-4!",
    "cost.massive_savings": "MASSIVE SAVINGS: 90%+ cheaper than GPT-4",
    "cost.great_savings": "Great savings: 80%+ cheaper than GPT-4",
    "cost.good_savings": "Good savings: 50%+ cheaper than GPT-4",

    # Auth
    "auth.invalid_key": "Invalid API key.",
    "auth.key_expired": "API key has expired.",
    "auth.budget_exhausted": "API key budget exhausted.",
    "auth.insufficient_scope": "API key lacks required scope.",

    # Batch
    "batch.submitted": "Batch job submitted successfully.",
    "batch.invalid_request": "Invalid batch request format.",
    "batch.job_not_found": "Batch job not found.",

    # Health
    "health.ok": "ok",
    "health.degraded": "degraded",
    "health.down": "down",
}

VIOLATION_MESSAGES: dict[str, str] = {
    "pii": "Personal information was detected in your request.",
    "prompt_injection": "Potential prompt injection or instruction override detected.",
    "content_filter": "Your request contains content that violates our usage policies.",
    "custom": "A custom safety rule was triggered.",
    "repetition_attack": "Potential repetition attack detected.",
}
