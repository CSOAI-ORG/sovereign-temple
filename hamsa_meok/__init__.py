"""
Hamsa-MEOK — Open Source Robotic Hand Control Library
Fork of Apache 2.0 Hamsa, extended with Sovereign Mind integration.

Original: github.com/hamsa-robotics/hamsa (Apache 2.0)
License: Apache 2.0
MEOK Extensions: SOV3 Byzantine Council governance, Maternal Covenant safety,
                 Active Inference gesture classification

Key additions over original Hamsa:
- SovereignHandController: wraps every servo command with EI3 safety checks
  before execution; no servo moves without care validation.
- ActiveInferenceGesture: probabilistic gesture classification using Free Energy
  Principle (replaces the original rule-based lookup table).
- ByzantineServoConsensus: multi-servo coordination via distributed consensus
  when controlling multi-arm arrays (SO-101 fleet, Robot Nano Hand).
- SOV3 embodied memory logging: every gesture is stored as an interaction
  episode in Sovereign Temple v3.0 for continual learning.

Supported hardware (tested):
  - SO-101 arm (£100, LeRobot compatible)         -> 6 DOF
  - Robot Nano Hand (tendon-driven, 11 DOF)       -> full biomimetic
  - Custom MEOK hand (DissolvPCB + Hamsa-MEOK)    -> 8 DOF configurable

Quick start:
  from hamsa_meok import HamsaController
  import asyncio

  async def main():
      ctrl = HamsaController(num_servos=6)
      await ctrl.gesture("wave")

  asyncio.run(main())

With SOV3 safety:
  from hamsa_meok import HamsaController
  from ei3_node import EI3Node

  async def main():
      ei3 = EI3Node()
      ctrl = HamsaController(num_servos=11, ei3_node=ei3)
      await ctrl.gesture("grasp")   # Passes Maternal Covenant before moving

  asyncio.run(main())
"""

__version__ = "2.0.0-meok"
__license__ = "Apache 2.0"
__author__ = "MEOK AI LTD"
__upstream__ = "github.com/hamsa-robotics/hamsa"

from .controller import HamsaController

__all__ = ["HamsaController"]
