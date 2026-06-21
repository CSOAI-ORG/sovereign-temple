"""
TurnState — Explicit state-machine agent loop for Jarvis/SOV3.
Inspired by Nanobot's state-machine architecture.
Eliminates nested callback hell. Makes the agent loop testable and observable.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import asyncio


class TurnState(Enum):
    IDLE = auto()
    LISTENING = auto()
    TRANSCRIBING = auto()
    ROUTING = auto()          # Decide which brain/model to use
    THINKING = auto()         # LLM inference
    TOOL_CALLING = auto()     # Execute MCP tools
    OBSERVING = auto()        # Process tool results
    SPEAKING = auto()         # TTS output
    WAITING = auto()          # Awaiting user response
    INTERRUPTED = auto()      # Barge-in detected
    ERROR = auto()
    CHECKPOINTING = auto()


# Valid state transitions — any transition not listed here raises ValueError
_TRANSITIONS: Dict[TurnState, List[TurnState]] = {
    TurnState.IDLE: [TurnState.LISTENING, TurnState.ERROR],
    TurnState.LISTENING: [TurnState.TRANSCRIBING, TurnState.INTERRUPTED, TurnState.ERROR],
    TurnState.TRANSCRIBING: [TurnState.ROUTING, TurnState.ERROR],
    TurnState.ROUTING: [TurnState.THINKING, TurnState.TOOL_CALLING, TurnState.SPEAKING, TurnState.ERROR],
    TurnState.THINKING: [TurnState.TOOL_CALLING, TurnState.SPEAKING, TurnState.OBSERVING, TurnState.ERROR],
    TurnState.TOOL_CALLING: [TurnState.OBSERVING, TurnState.ERROR],
    TurnState.OBSERVING: [TurnState.THINKING, TurnState.SPEAKING, TurnState.TOOL_CALLING, TurnState.ERROR],
    TurnState.SPEAKING: [TurnState.WAITING, TurnState.INTERRUPTED, TurnState.ERROR],
    TurnState.WAITING: [TurnState.LISTENING, TurnState.IDLE, TurnState.ERROR],
    TurnState.INTERRUPTED: [TurnState.LISTENING, TurnState.IDLE, TurnState.ERROR],
    TurnState.ERROR: [TurnState.IDLE, TurnState.LISTENING],
    TurnState.CHECKPOINTING: [TurnState.IDLE, TurnState.LISTENING, TurnState.THINKING],
}


@dataclass
class TurnContext:
    """Immutable-ish context for a single turn."""
    session_id: str
    state: TurnState = TurnState.IDLE
    user_utterance: Optional[str] = None
    transcription_confidence: float = 0.0
    selected_model: Optional[str] = None
    model_provider: Optional[str] = None
    reasoning_text: Optional[str] = None
    assistant_response: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    interrupted: bool = False
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class StateMachineError(Exception):
    pass


class AgentLoop:
    """
    Explicit state-machine agent loop.
    Usage:
        loop = AgentLoop(session_id="abc")
        await loop.transition_to(TurnState.LISTENING)
        # ... audio pipeline feeds utterance ...
        await loop.transition_to(TurnState.TRANSCRIBING)
        await loop.transition_to(TurnState.ROUTING)
    """

    def __init__(self, session_id: str, checkpoint_callback: Optional[Callable] = None):
        self.session_id = session_id
        self.ctx = TurnContext(session_id=session_id)
        self._transition_hooks: Dict[TurnState, List[Callable]] = {s: [] for s in TurnState}
        self._checkpoint_callback = checkpoint_callback
        self._lock = asyncio.Lock()

    def on_enter(self, state: TurnState, hook: Callable):
        """Register a hook to run when entering a state."""
        self._transition_hooks[state].append(hook)

    async def transition_to(self, new_state: TurnState, **ctx_updates) -> TurnContext:
        async with self._lock:
            current = self.ctx.state
            if new_state not in _TRANSITIONS.get(current, []):
                raise StateMachineError(
                    f"Invalid transition: {current.name} -> {new_state.name}"
                )
            self.ctx.state = new_state
            self.ctx.updated_at = datetime.utcnow().isoformat()
            for k, v in ctx_updates.items():
                if hasattr(self.ctx, k):
                    setattr(self.ctx, k, v)
            # Run hooks
            for hook in self._transition_hooks.get(new_state, []):
                if asyncio.iscoroutinefunction(hook):
                    await hook(self.ctx)
                else:
                    hook(self.ctx)
            # Checkpoint
            if self._checkpoint_callback:
                if asyncio.iscoroutinefunction(self._checkpoint_callback):
                    await self._checkpoint_callback(self.ctx)
                else:
                    self._checkpoint_callback(self.ctx)
            return self.ctx

    def can_transition(self, new_state: TurnState) -> bool:
        return new_state in _TRANSITIONS.get(self.ctx.state, [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.ctx.state.name,
            "context": {
                k: v for k, v in self.ctx.__dict__.items()
                if k not in ("created_at", "updated_at")
            },
            "created_at": self.ctx.created_at,
            "updated_at": self.ctx.updated_at,
        }
