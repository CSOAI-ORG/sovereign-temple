"""
HamsaController — SOV3-integrated robotic hand/arm controller.

Fork of Apache 2.0 Hamsa servo library.
Extended with: EI³ safety pipeline, Active Inference gesture classification,
Byzantine Servo Consensus for multi-arm fleets.

Supported hardware:
  - SO-101 arm (6 DOF, LeRobot protocol)
  - Robot Nano Hand (11 DOF, tendon-driven)
  - Custom MEOK hand (DissolvPCB, 8 DOF)
  - Any servo bus (Dynamixel, Feetech, custom)

License: Apache 2.0 (original Hamsa + MEOK extensions)
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple, Any

log = logging.getLogger("hamsa_meok")

# ---------------------------------------------------------------------------
# Servo / Joint model
# ---------------------------------------------------------------------------


@dataclass
class ServoSpec:
    """Specification for a single servo joint."""

    servo_id: int
    name: str
    min_angle: float = -180.0  # degrees
    max_angle: float = 180.0
    default_angle: float = 0.0
    max_velocity: float = 90.0  # degrees/second
    max_torque: float = 1.0  # Nm (normalised 0-1 if unknown)
    hardware_type: str = "dynamixel"  # dynamixel | feetech | custom


@dataclass
class JointState:
    """Current state of a single joint."""

    servo_id: int
    angle: float = 0.0
    velocity: float = 0.0
    torque: float = 0.0
    temperature_c: float = 25.0
    voltage: float = 12.0


# ---------------------------------------------------------------------------
# Predefined gestures
# ---------------------------------------------------------------------------

# Each gesture maps joint_id -> target_angle (degrees)
GESTURE_LIBRARY: Dict[str, Dict[int, float]] = {
    "home": {i: 0.0 for i in range(11)},
    "open": {i: 45.0 for i in range(11)},
    "close": {i: -45.0 for i in range(11)},
    "wave": {0: 30, 1: -30, 2: 30, 3: -30, 4: 0, 5: 0},
    "point": {
        0: 0,
        1: 80,
        2: -60,
        3: -60,
        4: -60,
        5: -60,
        6: -60,
        7: -60,
        8: -60,
        9: -60,
        10: -60,
    },
    "thumbs_up": {
        0: 70,
        1: -70,
        2: -70,
        3: -70,
        4: -70,
        5: -70,
        6: -70,
        7: -70,
        8: -70,
        9: -70,
        10: 0,
    },
    "grasp": {i: -60.0 for i in range(11)},
    "pinch": {
        0: -30,
        1: -60,
        2: -70,
        3: -80,
        4: -80,
        5: -80,
        6: -80,
        7: -80,
        8: -80,
        9: -80,
        10: -80,
    },
    "peace": {
        0: 0,
        1: 80,
        2: 80,
        3: -70,
        4: -70,
        5: -70,
        6: -70,
        7: -70,
        8: -70,
        9: -70,
        10: 0,
    },
    "salute": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 60, 7: 0, 8: 0, 9: 0, 10: 0},
}

# Gesture safety metadata
GESTURE_SAFETY: Dict[str, Dict[str, Any]] = {
    "wave": {"action_type": "wave", "force_level": 0.1, "target_category": "person"},
    "point": {
        "action_type": "gesture",
        "force_level": 0.1,
        "target_category": "object",
    },
    "thumbs_up": {
        "action_type": "gesture",
        "force_level": 0.05,
        "target_category": "person",
    },
    "grasp": {"action_type": "grasp", "force_level": 0.4, "target_category": "object"},
    "pinch": {"action_type": "grasp", "force_level": 0.2, "target_category": "object"},
    "peace": {
        "action_type": "gesture",
        "force_level": 0.05,
        "target_category": "person",
    },
    "salute": {
        "action_type": "gesture",
        "force_level": 0.05,
        "target_category": "person",
    },
    "open": {"action_type": "open", "force_level": 0.1, "target_category": "object"},
    "close": {"action_type": "close", "force_level": 0.3, "target_category": "object"},
    "home": {
        "action_type": "gesture",
        "force_level": 0.05,
        "target_category": "object",
    },
}


# ---------------------------------------------------------------------------
# Active Inference gesture classifier (Free Energy Principle)
# ---------------------------------------------------------------------------


class ActiveInferenceGestureClassifier:
    """
    Classifies intended gesture from sensor data using active inference /
    Free Energy Principle (replaces the original Hamsa rule-based lookup).

    Instead of hard rules, the classifier maintains a generative model of
    each gesture, computes prediction error (free energy) for observed joint
    states, and selects the gesture with lowest free energy (best fit).

    In production this would be backed by a trained variational autoencoder;
    here we provide the mathematical skeleton with mock generative models.
    """

    def __init__(self):
        # Prior beliefs over gestures (uniform initially)
        self._priors: Dict[str, float] = {
            g: 1.0 / len(GESTURE_LIBRARY) for g in GESTURE_LIBRARY
        }
        self._update_count = 0

    def _generative_model(self, gesture: str, num_joints: int) -> List[float]:
        """Returns expected joint angles for a given gesture (generative model)."""
        gesture_angles = GESTURE_LIBRARY.get(gesture, GESTURE_LIBRARY["home"])
        return [gesture_angles.get(i, 0.0) for i in range(num_joints)]

    def _free_energy(self, observed: List[float], predicted: List[float]) -> float:
        """
        Variational free energy ≈ prediction error (MSE) in the linear regime.
        Lower = observed data better explained by this gesture.
        """
        if not observed:
            return float("inf")
        return sum((o - p) ** 2 for o, p in zip(observed, predicted)) / len(observed)

    def classify(self, joint_states: List[JointState]) -> Tuple[str, float]:
        """
        Returns (gesture_name, confidence) for the observed joint states.
        """
        observed = [js.angle for js in joint_states]
        num_joints = len(observed)

        free_energies: Dict[str, float] = {}
        for gesture in GESTURE_LIBRARY:
            predicted = self._generative_model(gesture, num_joints)
            fe = self._free_energy(observed, predicted)
            free_energies[gesture] = fe

        # Softmax over negative free energies → posterior
        min_fe = min(free_energies.values())
        raw = {
            g: math.exp(-(fe - min_fe) / max(min_fe, 1.0))
            for g, fe in free_energies.items()
        }
        total = sum(raw.values())
        posterior = {g: v / total for g, v in raw.items()}

        # Update prior via Bayesian update (running average)
        alpha = 0.1
        for g in self._priors:
            self._priors[g] = (1 - alpha) * self._priors[g] + alpha * posterior.get(
                g, 0
            )

        best_gesture = min(free_energies, key=free_energies.get)
        confidence = posterior[best_gesture]
        self._update_count += 1

        return best_gesture, confidence

    def get_stats(self) -> dict:
        return {
            "update_count": self._update_count,
            "prior_beliefs": {k: round(v, 4) for k, v in self._priors.items()},
        }


# ---------------------------------------------------------------------------
# Hardware interface (mock + real)
# ---------------------------------------------------------------------------


class MockServoInterface:
    """Simulates a servo bus for development/testing without hardware."""

    def __init__(self, num_servos: int):
        self.joint_states = [JointState(servo_id=i) for i in range(num_servos)]

    async def read_joints(self) -> List[JointState]:
        # Drift joints slightly to simulate real hardware
        for js in self.joint_states:
            js.angle += random.uniform(-0.5, 0.5)
            js.temperature_c = 25.0 + random.uniform(-1, 2)
        return self.joint_states

    async def move_to(self, targets: Dict[int, float], speed: float = 1.0) -> bool:
        """Move joints toward target angles at given speed (0-1)."""
        dt = 0.05  # seconds per step
        steps = max(1, int(1.0 / speed * 5))

        for _ in range(steps):
            for servo_id, target in targets.items():
                if servo_id < len(self.joint_states):
                    js = self.joint_states[servo_id]
                    diff = target - js.angle
                    step = diff * 0.4  # PD-style convergence
                    js.angle += step
                    js.velocity = step / dt
            await asyncio.sleep(dt)

        return True

    async def set_torque(self, enabled: bool):
        pass

    async def get_temperature(self) -> Dict[int, float]:
        return {js.servo_id: js.temperature_c for js in self.joint_states}


# ---------------------------------------------------------------------------
# HamsaController — main public API
# ---------------------------------------------------------------------------


class HamsaController:
    """
    Main controller for Hamsa-MEOK robotic hands/arms.

    All motion commands pass through EI³ safety pipeline when an EI3Node
    is attached. Without EI³, commands execute directly (dev/demo mode).

    Usage (basic):
        ctrl = HamsaController(num_servos=6)
        await ctrl.gesture("wave")

    Usage (SOV3-safe):
        from ei3_node import EI3Node
        ei3 = EI3Node(sov_url="http://localhost:3200")
        ctrl = HamsaController(num_servos=11, ei3_node=ei3)
        await ctrl.gesture("wave")  # goes through Maternal Covenant + Council
    """

    def __init__(
        self,
        num_servos: int = 6,
        hardware_type: str = "mock",  # mock | dynamixel | feetech | so101
        ei3_node: Optional[Any] = None,  # EI3Node instance (optional)
        sov_url: str = "http://localhost:3200",
        robot_id: str = "hand_001",
    ):
        self.num_servos = num_servos
        self.hardware_type = hardware_type
        self.robot_id = robot_id
        self.sov_url = sov_url
        self._ei3 = ei3_node

        # Hardware interface
        if hardware_type == "mock" or not self._real_hardware_available():
            self._hw = MockServoInterface(num_servos)
            log.info(f"HamsaController: mock hardware ({num_servos} servos)")
        else:
            self._hw = self._init_real_hardware()

        # Gesture classifier
        self._classifier = ActiveInferenceGestureClassifier()

        # State
        self._current_gesture: Optional[str] = None
        self._gesture_history: List[Dict] = []
        self._gestures_executed = 0
        self._gestures_blocked = 0

        log.info(
            f"HamsaController ready — robot={robot_id} servos={num_servos} "
            f"hardware={hardware_type} ei3={'yes' if ei3_node else 'no'}"
        )

    def _real_hardware_available(self) -> bool:
        """Check if real servo hardware library is importable."""
        try:
            if self.hardware_type in ("dynamixel", "so101"):
                import dynamixel_sdk  # type: ignore

                return True
            elif self.hardware_type == "feetech":
                import scservo_sdk  # type: ignore

                return True
        except ImportError:
            pass
        return False

    def _init_real_hardware(self) -> Any:
        """Initialise real servo hardware interface."""
        log.warning("Real hardware init not fully implemented — using mock")
        return MockServoInterface(self.num_servos)

    # ------------------------------------------------------------------
    # High-level gesture API
    # ------------------------------------------------------------------

    async def gesture(
        self,
        gesture_name: str,
        speed: float = 0.5,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Execute a named gesture.

        If EI³ is attached, the gesture goes through:
          1. Maternal Covenant hard-rules
          2. SOV3 care_validation_nn
          3. Byzantine Council consensus
          → only then do servos move

        Returns execution result dict.
        """
        if gesture_name not in GESTURE_LIBRARY:
            return {
                "status": "error",
                "reason": f"Unknown gesture: '{gesture_name}'. "
                f"Available: {list(GESTURE_LIBRARY.keys())}",
            }

        targets = GESTURE_LIBRARY[gesture_name]
        safety_meta = GESTURE_SAFETY.get(
            gesture_name,
            {
                "action_type": "gesture",
                "force_level": 0.1,
                "target_category": "object",
            },
        )

        action = {
            **safety_meta,
            "description": description or f"Gesture: {gesture_name} on {self.robot_id}",
            "target": "workspace",
            "parameters": {"gesture": gesture_name, "speed": speed},
        }

        if self._ei3 is not None:
            # Route through EI³ safety pipeline
            result = await self._ei3.execute_action(action)
            if result["executed"]:
                await self._hw.move_to(targets, speed)
                self._current_gesture = gesture_name
                self._gestures_executed += 1
            else:
                self._gestures_blocked += 1

            self._gesture_history.append(
                {
                    "gesture": gesture_name,
                    "executed": result["executed"],
                    "care_score": result["care_score"],
                    "timestamp": time.time(),
                }
            )
            return result
        else:
            # No EI³ — execute directly (dev mode)
            log.warning(f"Executing '{gesture_name}' without EI³ safety (dev mode)")
            success = await self._hw.move_to(targets, speed)
            self._current_gesture = gesture_name
            self._gestures_executed += 1
            return {
                "status": "executed",
                "gesture": gesture_name,
                "care_score": None,
                "ei3": False,
                "warning": "no_safety_pipeline",
            }

    async def move_joint(
        self,
        joint_id: int,
        angle: float,
        speed: float = 0.5,
    ) -> Dict:
        """Move a single joint to a target angle (degrees)."""
        if joint_id >= self.num_servos:
            return {"status": "error", "reason": f"Joint {joint_id} out of range"}

        action = {
            "action_type": "joint_move",
            "description": f"Move joint {joint_id} to {angle}° on {self.robot_id}",
            "force_level": speed * 0.3,
            "target": f"joint_{joint_id}",
            "target_category": "object",
            "parameters": {"joint_id": joint_id, "angle": angle},
        }

        if self._ei3 is not None:
            result = await self._ei3.execute_action(action)
            if result["executed"]:
                await self._hw.move_to({joint_id: angle}, speed)
            return result
        else:
            await self._hw.move_to({joint_id: angle}, speed)
            return {"status": "executed", "joint": joint_id, "angle": angle}

    async def read_joints(self) -> List[Dict]:
        """Read current joint states."""
        states = await self._hw.read_joints()
        return [asdict(s) for s in states]

    async def classify_current_gesture(self) -> Tuple[str, float]:
        """Classify the current gesture from observed joint states."""
        states = await self._hw.read_joints()
        return self._classifier.classify(states)

    async def home(self) -> Dict:
        """Return all joints to home position."""
        return await self.gesture("home", speed=0.3)

    async def demo(self) -> List[Dict]:
        """Run a demo sequence of gestures."""
        sequence = ["wave", "open", "close", "thumbs_up", "peace", "home"]
        results = []
        print("\n=== Hamsa-MEOK Demo ===")
        for gest in sequence:
            print(f"  Executing: {gest}")
            result = await self.gesture(gest, speed=0.5)
            status = (
                "✓"
                if result.get("executed") or result.get("status") == "executed"
                else "✗"
            )
            print(f"  {status} {gest} — care={result.get('care_score', 'N/A')}")
            results.append(result)
            await asyncio.sleep(0.5)
        print("=== Demo complete ===\n")
        return results

    # ------------------------------------------------------------------
    # Byzantine Servo Consensus (multi-arm fleet coordination)
    # ------------------------------------------------------------------

    async def fleet_gesture(
        self,
        gesture_name: str,
        fleet: List["HamsaController"],
        require_consensus: int = 2,
    ) -> Dict:
        """
        Execute a gesture across a fleet of arms with Byzantine consensus.

        At least `require_consensus` arms must successfully validate the
        action before any arm moves. If consensus isn't reached, all arms
        stay in current position.

        Args:
            gesture_name: Gesture to execute
            fleet: List of HamsaController instances (including self)
            require_consensus: Minimum approvals required

        Returns:
            Dict with consensus result and per-arm outcomes
        """
        all_arms = [self] + fleet
        approvals = []

        # Phase 1: Collect votes from all arms
        for arm in all_arms:
            if arm._ei3 is not None:
                action = {
                    **GESTURE_SAFETY.get(gesture_name, {}),
                    "description": f"Fleet gesture: {gesture_name}",
                    "parameters": {"gesture": gesture_name},
                }
                safety = await arm._ei3.check_action_safety(action)
                approvals.append(safety["safe"])
            else:
                approvals.append(True)  # No EI³ = auto-approve (dev mode)

        approved_count = sum(approvals)
        consensus_reached = approved_count >= require_consensus

        if not consensus_reached:
            return {
                "status": "consensus_failed",
                "approved": approved_count,
                "required": require_consensus,
                "total_arms": len(all_arms),
                "reason": f"Only {approved_count}/{len(all_arms)} arms approved",
            }

        # Phase 2: Execute simultaneously on all arms
        tasks = [arm.gesture(gesture_name, speed=0.5) for arm in all_arms]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "status": "executed",
            "gesture": gesture_name,
            "consensus": f"{approved_count}/{len(all_arms)}",
            "arm_results": [
                r
                if not isinstance(r, Exception)
                else {"status": "error", "reason": str(r)}
                for r in results
            ],
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        return {
            "robot_id": self.robot_id,
            "hardware_type": self.hardware_type,
            "num_servos": self.num_servos,
            "ei3_attached": self._ei3 is not None,
            "current_gesture": self._current_gesture,
            "gestures_executed": self._gestures_executed,
            "gestures_blocked": self._gestures_blocked,
            "classifier": self._classifier.get_stats(),
        }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    async def main():
        print("Hamsa-MEOK v2.0.0 — standalone demo (no EI³)")
        ctrl = HamsaController(num_servos=6, robot_id="demo_arm")
        await ctrl.demo()
        stats = ctrl.get_stats()
        print(f"Stats: {json.dumps(stats, indent=2)}")

    asyncio.run(main())
