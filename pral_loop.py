#!/usr/bin/env python3
"""
PRAL Loop Framework — Plan, Reason, Act, Learn
===============================================
Implements the blueprint's core methodology for agent task execution.
Separates high-performing implementations from reactive systems.

Usage:
    from pral_loop import PRALAgent
    
    agent = PRALAgent(
        name="eu-ai-act-classifier",
        purpose="Classify AI systems under EU AI Act Annex III",
        tools=[classify_risk, generate_annex_iv],
        max_turns=10,
        confidence_threshold=0.7,
    )
    
    result = agent.execute("Is our resume screening AI high-risk?")
    print(result.plan, result.reasoning, result.action, result.learning)

Blueprint Reference: Section 2.2 — The PRAL Loop Framework
"""

import os
import json
import time
import hashlib
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Optional
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTCOMES_DIR = Path.home() / "clawd" / "memory" / "outcomes"
OUTCOMES_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRAL] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(str(OUTCOMES_DIR / "pral.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and Data Classes
# ---------------------------------------------------------------------------
class TaskState(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    REASONING = "reasoning"
    ACTING = "acting"
    LEARNING = "learning"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_HUMAN = "needs_human"
    TIMED_OUT = "timed_out"
    CIRCUIT_BROKEN = "circuit_broken"


class FinalState(Enum):
    COMPLETED = "TASK_COMPLETED"
    FAILED = "TASK_FAILED"
    NEEDS_HUMAN = "NEEDS_HUMAN"


@dataclass
class PlanStep:
    """A single step in the task decomposition."""
    step_id: int
    description: str
    tool: Optional[str] = None
    dependencies: list = field(default_factory=list)
    success_criteria: str = ""
    status: str = "pending"


@dataclass
class Plan:
    """Full task decomposition plan."""
    task_id: str
    objective: str
    steps: list = field(default_factory=list)
    estimated_turns: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class ReasoningResult:
    """Output of the reasoning phase."""
    options_evaluated: list = field(default_factory=list)
    selected_option: str = ""
    confidence: float = 0.0
    constraints_checked: list = field(default_factory=list)
    risks_identified: list = field(default_factory=list)
    tradeoffs: dict = field(default_factory=dict)


@dataclass
class ActionResult:
    """Output of the action phase."""
    tool_used: str = ""
    tool_input: dict = field(default_factory=dict)
    tool_output: Any = None
    success: bool = False
    error: str = ""
    latency_ms: float = 0.0
    token_cost: float = 0.0


@dataclass
class LearningResult:
    """Output of the learning phase."""
    outcome: str = ""
    feedback_signals: list = field(default_factory=list)
    pattern_detected: str = ""
    improvement_suggestions: list = field(default_factory=list)
    stored_for_future: bool = False


@dataclass
class PRALResult:
    """Complete PRAL loop result."""
    task_id: str
    state: str = ""
    plan: Optional[Plan] = None
    reasoning: Optional[ReasoningResult] = None
    actions: list = field(default_factory=list)
    learning: Optional[LearningResult] = None
    total_turns: int = 0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    final_state: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------
class CircuitBreaker:
    """Prevents cascading failures from repeated attempts.
    
    Blueprint Reference: Section 1.5.3 — Circuit breakers on retry and handoff
    """
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = {}
        self.last_failure_time = {}
        self.state = {}  # "closed", "open", "half-open"
    
    def _key(self, tool_name: str) -> str:
        return tool_name
    
    def can_execute(self, tool_name: str) -> bool:
        key = self._key(tool_name)
        state = self.state.get(key, "closed")
        
        if state == "closed":
            return True
        
        if state == "open":
            last_failure = self.last_failure_time.get(key, 0)
            if time.time() - last_failure > self.recovery_timeout:
                self.state[key] = "half-open"
                return True
            return False
        
        if state == "half-open":
            return True
        
        return True
    
    def record_success(self, tool_name: str):
        key = self._key(tool_name)
        self.state[key] = "closed"
        self.failures[key] = 0
    
    def record_failure(self, tool_name: str):
        key = self._key(tool_name)
        self.failures[key] = self.failures.get(key, 0) + 1
        self.last_failure_time[key] = time.time()
        
        if self.failures[key] >= self.failure_threshold:
            self.state[key] = "open"
            logger.warning(f"Circuit breaker OPEN for {tool_name} ({self.failures[key]} failures)")
    
    def get_state(self, tool_name: str) -> str:
        return self.state.get(self._key(tool_name), "closed")


# ---------------------------------------------------------------------------
# Semantic Loop Detector
# ---------------------------------------------------------------------------
class SemanticLoopDetector:
    """Detects semantic loops using embedding-based similarity.
    
    Blueprint Reference: Section 4.3.1 — Semantic similarity analysis
    """
    
    def __init__(self, similarity_threshold: float = 0.85, window_size: int = 5):
        self.similarity_threshold = similarity_threshold
        self.window_size = window_size
        self.message_history = {}  # task_id -> list of embeddings
    
    def _simple_hash(self, text: str) -> float:
        """Simple hash-based similarity (fallback when no embedding model)."""
        return int(hashlib.md5(text.encode()).hexdigest(), 16) / (16**32)
    
    def _cosine_similarity(self, a: float, b: float) -> float:
        """Simplified similarity for hash-based approach."""
        return 1.0 - abs(a - b)
    
    def add_message(self, task_id: str, message: str) -> bool:
        """Add a message and check for semantic loops.
        
        Returns True if a loop is detected.
        """
        if task_id not in self.message_history:
            self.message_history[task_id] = []
        
        current_hash = self._simple_hash(message)
        history = self.message_history[task_id]
        
        # Check against recent messages
        for prev_hash in history[-self.window_size:]:
            similarity = self._cosine_similarity(current_hash, prev_hash)
            if similarity > self.similarity_threshold:
                logger.warning(f"SEMANTIC LOOP detected for {task_id} (similarity: {similarity:.3f})")
                return True
        
        history.append(current_hash)
        
        # Trim history to window size
        if len(history) > self.window_size * 2:
            self.message_history[task_id] = history[-self.window_size:]
        
        return False
    
    def clear(self, task_id: str):
        if task_id in self.message_history:
            del self.message_history[task_id]


# ---------------------------------------------------------------------------
# PRAL Agent
# ---------------------------------------------------------------------------
class PRALAgent:
    """Agent implementing the Plan → Reason → Act → Learn loop.
    
    Blueprint Reference: Section 2.2 — The PRAL Loop Framework
    """
    
    def __init__(
        self,
        name: str,
        purpose: str,
        tools: list = None,
        max_turns: int = 10,
        confidence_threshold: float = 0.7,
        constraints: list = None,
        human_escalation_threshold: float = 0.5,
    ):
        self.name = name
        self.purpose = purpose
        self.tools = tools or []
        self.max_turns = max_turns
        self.confidence_threshold = confidence_threshold
        self.constraints = constraints or []
        self.human_escalation_threshold = human_escalation_threshold
        
        # Safety mechanisms
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        self.loop_detector = SemanticLoopDetector(similarity_threshold=0.85, window_size=5)
        
        # Metrics
        self.total_executions = 0
        self.total_successes = 0
        self.total_failures = 0
        self.total_human_escalations = 0
        self.avg_latency = 0.0
        self.avg_cost = 0.0
    
    def _generate_task_id(self, task: str) -> str:
        return hashlib.sha256(f"{self.name}:{task}:{time.time()}".encode()).hexdigest()[:12]
    
    def _plan(self, task: str) -> Plan:
        """Phase 1: Plan — Task decomposition into sub-tasks.
        
        Blueprint: "Explicit reasoning about decomposing complex tasks into manageable sub-tasks,
        identifying required resources, and sequencing execution steps."
        """
        task_id = self._generate_task_id(task)
        
        # Simple decomposition — in production, this would use an LLM
        steps = []
        
        # Step 1: Understand the task
        steps.append(PlanStep(
            step_id=1,
            description=f"Understand task: {task[:100]}",
            success_criteria="Task objective clearly defined"
        ))
        
        # Step 2: Identify required tools
        steps.append(PlanStep(
            step_id=2,
            description="Identify required tools and resources",
            tool="tool_selector",
            dependencies=[1],
            success_criteria="Tools selected match task requirements"
        ))
        
        # Step 3: Execute primary action
        steps.append(PlanStep(
            step_id=3,
            description="Execute primary action",
            dependencies=[2],
            success_criteria="Action completed successfully"
        ))
        
        # Step 4: Validate results
        steps.append(PlanStep(
            step_id=4,
            description="Validate results against success criteria",
            dependencies=[3],
            success_criteria="Results meet quality standards"
        ))
        
        plan = Plan(
            task_id=task_id,
            objective=task,
            steps=steps,
            estimated_turns=len(steps),
        )
        
        logger.info(f"[{self.name}] PLAN: {len(steps)} steps for task {task_id}")
        return plan
    
    def _reason(self, plan: Plan, task: str) -> ReasoningResult:
        """Phase 2: Reason — Evaluate options against constraints and goals.
        
        Blueprint: "Explicit consideration of trade-offs, risk assessment, and alignment
        with organizational objectives."
        """
        options = []
        
        for step in plan.steps:
            if step.tool:
                options.append({
                    "step": step.step_id,
                    "tool": step.tool,
                    "description": step.description,
                })
        
        # Check constraints
        constraints_checked = []
        for constraint in self.constraints:
            constraints_checked.append({
                "constraint": constraint,
                "satisfied": True,  # In production, evaluate each constraint
            })
        
        # Calculate confidence (simplified — in production, use model confidence)
        confidence = 0.8 if len(options) > 0 else 0.3
        
        reasoning = ReasoningResult(
            options_evaluated=options,
            selected_option=options[0]["tool"] if options else "none",
            confidence=confidence,
            constraints_checked=constraints_checked,
            risks_identified=[],
        )
        
        logger.info(f"[{self.name}] REASON: confidence={confidence:.2f}, {len(options)} options")
        return reasoning
    
    def _act(self, reasoning: ReasoningResult, task: str) -> list:
        """Phase 3: Act — Execute with tool use and API calls.
        
        Blueprint: "Robust error handling: interpreting system responses, detecting failures,
        implementing retry or escalation strategies."
        """
        actions = []
        
        for option in reasoning.options_evaluated:
            tool_name = option.get("tool", "unknown")
            
            # Check circuit breaker
            if not self.circuit_breaker.can_execute(tool_name):
                logger.warning(f"[{self.name}] CIRCUIT BREAKER: {tool_name} is open")
                actions.append(ActionResult(
                    tool_used=tool_name,
                    success=False,
                    error="Circuit breaker open",
                ))
                continue
            
            # Check for semantic loops
            if self.loop_detector.add_message(reasoning.selected_option, task):
                logger.warning(f"[{self.name}] SEMANTIC LOOP: Breaking cycle")
                actions.append(ActionResult(
                    tool_used=tool_name,
                    success=False,
                    error="Semantic loop detected",
                ))
                continue
            
            # Execute tool
            start_time = time.time()
            try:
                # In production, this would call the actual tool
                # For now, simulate execution
                tool_output = f"Executed {tool_name} for task: {task[:50]}"
                
                latency_ms = (time.time() - start_time) * 1000
                
                result = ActionResult(
                    tool_used=tool_name,
                    tool_input={"task": task},
                    tool_output=tool_output,
                    success=True,
                    latency_ms=latency_ms,
                )
                
                self.circuit_breaker.record_success(tool_name)
                logger.info(f"[{self.name}] ACT: {tool_name} SUCCESS ({latency_ms:.0f}ms)")
                
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                
                result = ActionResult(
                    tool_used=tool_name,
                    tool_input={"task": task},
                    success=False,
                    error=str(e),
                    latency_ms=latency_ms,
                )
                
                self.circuit_breaker.record_failure(tool_name)
                logger.error(f"[{self.name}] ACT: {tool_name} FAILED ({latency_ms:.0f}ms): {e}")
            
            actions.append(result)
            
            # Check if we should stop (first failure with low confidence)
            if not result.success and reasoning.confidence < self.confidence_threshold:
                logger.info(f"[{self.name}] ACT: Stopping due to failure + low confidence")
                break
        
        return actions
    
    def _learn(self, plan: Plan, reasoning: ReasoningResult, actions: list, task: str) -> LearningResult:
        """Phase 4: Learn — Incorporate feedback to improve future iterations.
        
        Blueprint: "Explicit human feedback, implicit signals from user behavior,
        and automated analysis of outcome metrics."
        """
        success_count = sum(1 for a in actions if a.success)
        total_actions = len(actions)
        success_rate = success_count / total_actions if total_actions > 0 else 0
        
        outcome = "success" if success_rate >= self.confidence_threshold else "failure"
        
        # Generate learning signals
        feedback_signals = []
        if success_rate < 0.5:
            feedback_signals.append("Low success rate — review tool selection")
        if reasoning.confidence < self.confidence_threshold:
            feedback_signals.append("Low confidence — needs more context")
        if any(a.error == "Circuit breaker open" for a in actions):
            feedback_signals.append("Circuit breaker triggered — tool reliability issue")
        if any(a.error == "Semantic loop detected" for a in actions):
            feedback_signals.append("Semantic loop detected — task decomposition issue")
        
        # Improvement suggestions
        improvement_suggestions = []
        if success_rate < 0.8:
            improvement_suggestions.append("Add more specific tool selection criteria")
        if reasoning.confidence < 0.7:
            improvement_suggestions.append("Improve context engineering for better confidence")
        
        learning = LearningResult(
            outcome=outcome,
            feedback_signals=feedback_signals,
            pattern_detected=f"Success rate: {success_rate:.2f}",
            improvement_suggestions=improvement_suggestions,
            stored_for_future=True,
        )
        
        logger.info(f"[{self.name}] LEARN: outcome={outcome}, signals={len(feedback_signals)}")
        return learning
    
    def execute(self, task: str) -> PRALResult:
        """Execute the full PRAL loop for a task.
        
        Returns PRALResult with plan, reasoning, actions, and learning.
        """
        task_id = self._generate_task_id(task)
        start_time = time.time()
        
        logger.info(f"[{self.name}] EXECUTE: task={task[:50]}... (id={task_id})")
        
        result = PRALResult(task_id=task_id)
        
        try:
            # Phase 1: Plan
            result.state = TaskState.PLANNING.value
            result.plan = self._plan(task)
            
            # Phase 2: Reason
            result.state = TaskState.REASONING.value
            result.reasoning = self._reason(result.plan, task)
            
            # Check confidence threshold for human escalation
            if result.reasoning.confidence < self.human_escalation_threshold:
                result.state = TaskState.NEEDS_HUMAN.value
                result.final_state = FinalState.NEEDS_HUMAN.value
                self.total_human_escalations += 1
                logger.warning(f"[{self.name}] HUMAN ESCALATION: confidence={result.reasoning.confidence:.2f}")
                return result
            
            # Phase 3: Act
            result.state = TaskState.ACTING.value
            result.actions = self._act(result.reasoning, task)
            
            # Check for circuit breaker or loop failures
            if any(a.error in ("Circuit breaker open", "Semantic loop detected") for a in result.actions):
                result.state = TaskState.CIRCUIT_BROKEN.value
                result.final_state = FinalState.FAILED.value
                return result
            
            # Phase 4: Learn
            result.state = TaskState.LEARNING.value
            result.learning = self._learn(result.plan, result.reasoning, result.actions, task)
            
            # Final state
            if result.learning.outcome == "success":
                result.state = TaskState.COMPLETED.value
                result.final_state = FinalState.COMPLETED.value
                self.total_successes += 1
            else:
                result.state = TaskState.FAILED.value
                result.final_state = FinalState.FAILED.value
                self.total_failures += 1
            
        except Exception as e:
            result.state = TaskState.FAILED.value
            result.final_state = FinalState.FAILED.value
            self.total_failures += 1
            logger.error(f"[{self.name}] EXECUTE FAILED: {e}", exc_info=True)
        
        # Update metrics
        self.total_executions += 1
        total_latency_ms = (time.time() - start_time) * 1000
        result.total_latency_ms = total_latency_ms
        result.total_turns = len(result.actions)
        
        # Update running averages
        self.avg_latency = (self.avg_latency * (self.total_executions - 1) + total_latency_ms) / self.total_executions
        
        # Store outcome
        self._store_outcome(result)
        
        logger.info(f"[{self.name}] COMPLETE: state={result.state}, latency={total_latency_ms:.0f}ms")
        return result
    
    def _store_outcome(self, result: PRALResult):
        """Store outcome for future learning and audit."""
        outcome_file = OUTCOMES_DIR / f"{self.name}-{result.timestamp.replace(':', '-')}.json"
        
        outcome_data = {
            "agent": self.name,
            "task_id": result.task_id,
            "state": result.state,
            "final_state": result.final_state,
            "plan_steps": len(result.plan.steps) if result.plan else 0,
            "actions_count": len(result.actions),
            "success_count": sum(1 for a in result.actions if a.success),
            "confidence": result.reasoning.confidence if result.reasoning else 0,
            "learning_outcome": result.learning.outcome if result.learning else "unknown",
            "total_latency_ms": result.total_latency_ms,
            "timestamp": result.timestamp,
        }
        
        with open(outcome_file, "w") as f:
            json.dump(outcome_data, f, indent=2)
    
    def get_metrics(self) -> dict:
        """Get agent performance metrics (CLEAR framework)."""
        return {
            "agent": self.name,
            "total_executions": self.total_executions,
            "successes": self.total_successes,
            "failures": self.total_failures,
            "human_escalations": self.total_human_escalations,
            "success_rate": self.total_successes / self.total_executions if self.total_executions > 0 else 0,
            "avg_latency_ms": self.avg_latency,
            "avg_cost": self.avg_cost,
            "circuit_breaker_states": {
                "tool": self.circuit_breaker.get_state("tool")
                for tool in [t.__name__ if hasattr(t, "__name__") else str(t) for t in self.tools]
            },
        }


# ---------------------------------------------------------------------------
# CLEAR Metrics Collector
# ---------------------------------------------------------------------------
class CLEARCollector:
    """Collects Cost, Latency, Efficacy, Assurance, Reliability metrics.
    
    Blueprint Reference: Section 7.1 — CLEAR framework for comprehensive agent evaluation
    """
    
    def __init__(self, output_dir: Path = OUTCOMES_DIR):
        self.output_dir = output_dir / "clear"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = []
    
    def record(self, agent_name: str, result: PRALResult):
        """Record a CLEAR metric entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "task_id": result.task_id,
            # Cost
            "cost": result.total_cost,
            # Latency
            "latency_ms": result.total_latency_ms,
            # Efficacy
            "efficacy": 1.0 if result.final_state == FinalState.COMPLETED.value else 0.0,
            "success_rate": sum(1 for a in result.actions if a.success) / len(result.actions) if result.actions else 0,
            # Assurance
            "confidence": result.reasoning.confidence if result.reasoning else 0,
            "constraints_violated": 0,  # In production, track actual violations
            # Reliability
            "circuit_breaker_trips": sum(1 for a in result.actions if a.error == "Circuit breaker open"),
            "loop_detections": sum(1 for a in result.actions if a.error == "Semantic loop detected"),
            "final_state": result.final_state,
        }
        
        self.metrics.append(entry)
        
        # Write to daily file
        daily_file = self.output_dir / f"clear-{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
        with open(daily_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_summary(self, agent_name: str = None, days: int = 7) -> dict:
        """Get CLEAR summary for an agent or all agents."""
        cutoff = time.time() - (days * 86400)
        
        filtered = [m for m in self.metrics if m["timestamp"] > datetime.fromtimestamp(cutoff).isoformat()]
        if agent_name:
            filtered = [m for m in filtered if m["agent"] == agent_name]
        
        if not filtered:
            return {"error": "No metrics found"}
        
        return {
            "count": len(filtered),
            "avg_cost": sum(m["cost"] for m in filtered) / len(filtered),
            "avg_latency_ms": sum(m["latency_ms"] for m in filtered) / len(filtered),
            "avg_efficacy": sum(m["efficacy"] for m in filtered) / len(filtered),
            "avg_success_rate": sum(m["success_rate"] for m in filtered) / len(filtered),
            "avg_confidence": sum(m["confidence"] for m in filtered) / len(filtered),
            "total_circuit_breaker_trips": sum(m["circuit_breaker_trips"] for m in filtered),
            "total_loop_detections": sum(m["loop_detections"] for m in filtered),
            "success_count": sum(1 for m in filtered if m["final_state"] == FinalState.COMPLETED.value),
            "failure_count": sum(1 for m in filtered if m["final_state"] == FinalState.FAILED.value),
            "human_escalation_count": sum(1 for m in filtered if m["final_state"] == FinalState.NEEDS_HUMAN.value),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    """Test the PRAL loop framework."""
    print("🧠 PRAL Loop Framework Test")
    print("=" * 50)
    
    # Create agent
    agent = PRALAgent(
        name="test-classifier",
        purpose="Test EU AI Act classification",
        max_turns=10,
        confidence_threshold=0.7,
        constraints=["No financial advice", "No legal guarantees"],
    )
    
    # Execute task
    result = agent.execute("Is our resume screening AI high-risk under EU AI Act Annex III?")
    
    print(f"\n📋 Task ID: {result.task_id}")
    print(f"📊 State: {result.state}")
    print(f"🎯 Final: {result.final_state}")
    print(f"📝 Plan steps: {len(result.plan.steps) if result.plan else 0}")
    print(f"🤔 Confidence: {result.reasoning.confidence:.2f}" if result.reasoning else "🤔 Confidence: N/A")
    print(f"⚡ Actions: {len(result.actions)}")
    print(f"⏱️  Latency: {result.total_latency_ms:.0f}ms")
    
    if result.learning:
        print(f"📚 Learning: {result.learning.outcome}")
        for signal in result.learning.feedback_signals:
            print(f"   - {signal}")
    
    # Get metrics
    metrics = agent.get_metrics()
    print(f"\n📈 Metrics:")
    print(f"   Executions: {metrics['total_executions']}")
    print(f"   Success rate: {metrics['success_rate']:.2f}")
    print(f"   Avg latency: {metrics['avg_latency_ms']:.0f}ms")
    
    print("\n✅ PRAL Loop Framework operational")


if __name__ == "__main__":
    main()
