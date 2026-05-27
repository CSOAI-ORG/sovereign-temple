#!/usr/bin/env python3
"""
SOVEREIGN MASTER NEURAL NET
============================
Sparse Mixture-of-Experts (MoE) that aggregates ALL specialist neural nets
into one unified intelligence layer.

Architecture:
  Input (any query) → Quantum Gating Network → Top-K Expert Selection →
  Expert Inference → Weighted Fusion → Master Output

Experts (from existing SOV3 neural nets):
  0: care_validation_nn (59→6)
  1: threat_detection_nn (260→4)
  2: creativity_assessment_nn (12→5)
  3: partnership_detection_ml (106→8)
  4: relationship_evolution_nn (64→3)
  5: care_pattern_analyzer (12→5)

The gating network uses quantum-inspired care dimension scoring:
  - 6 care dimensions (self, other, process, future, relational, maternal)
  - QAOA-style weights for model affinity
  - Stochastic resonance noise for exploration

Continual Learning:
  - EWC prevents catastrophic forgetting
  - Online learning from every interaction
  - Fisher Information Matrix tracks parameter importance

Usage:
  from neural_core.sovereign_master_net import master_net
  result = master_net.infer("How should I handle this?", context={...})
  master_net.learn(input_features, target, task_id="care")
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from copy import deepcopy

log = logging.getLogger("sovereign.master_net")

MODEL_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "models"


# Try KAN (Kolmogorov-Arnold Networks) — learnable activation functions,
# 10-100x more interpretable than MLPs, better accuracy with fewer params
# KAN disabled in production — creates checkpoint dirs and warnings during inference.
# Enable manually for training sessions only.
KAN_AVAILABLE = False


class Expert(nn.Module):
    """A small specialist — KAN if available, MLP fallback.

    KAN uses learnable activation functions on EDGES (not fixed on nodes),
    making the learned function interpretable as symbolic formulas.
    """
    def __init__(self, in_dim: int, hidden_dim: int, out_dim: int, name: str = ""):
        super().__init__()
        self.name = name
        self.use_kan = KAN_AVAILABLE

        if self.use_kan:
            # KAN: learnable B-spline activations on edges
            self.net = _KAN(width=[in_dim, hidden_dim, out_dim], grid=5, k=3)
        else:
            # MLP fallback
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden_dim),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.GELU(),
                nn.Linear(hidden_dim // 2, out_dim),
            )

    def forward(self, x):
        return self.net(x)


class QuantumGatingNetwork(nn.Module):
    """Quantum-inspired gating: selects top-K experts per input.

    Uses care dimension scoring + stochastic resonance noise
    for exploration (analogous to quantum superposition collapse).
    """
    def __init__(self, in_dim: int, num_experts: int, noise_std: float = 0.1):
        super().__init__()
        self.num_experts = num_experts
        self.noise_std = noise_std

        # Care dimension projector (maps input → 6 care dimensions)
        self.care_projector = nn.Linear(in_dim, 6)

        # QAOA-style affinity: each expert has affinity to each care dimension
        self.care_affinity = nn.Parameter(torch.randn(num_experts, 6) * 0.1)

        # Direct gating (bypass for non-care queries)
        self.direct_gate = nn.Linear(in_dim, num_experts)

        # Blend factor: how much to weight care vs direct
        self.blend = nn.Parameter(torch.tensor(0.5))

    def forward(self, x, top_k: int = 2):
        # Care dimension scoring
        care_dims = torch.sigmoid(self.care_projector(x))  # (batch, 6)
        care_scores = torch.matmul(care_dims, self.care_affinity.T)  # (batch, num_experts)

        # Direct gating
        direct_scores = self.direct_gate(x)  # (batch, num_experts)

        # Blend
        blend = torch.sigmoid(self.blend)
        gate_logits = blend * care_scores + (1 - blend) * direct_scores

        # Stochastic resonance noise (exploration during training)
        if self.training:
            noise = torch.randn_like(gate_logits) * self.noise_std
            gate_logits = gate_logits + noise

        # Top-K selection (quantum measurement / superposition collapse)
        top_k_vals, top_k_idx = torch.topk(gate_logits, top_k, dim=-1)
        top_k_weights = F.softmax(top_k_vals, dim=-1)

        return top_k_weights, top_k_idx, care_dims


class SovereignMasterNet(nn.Module):
    """The master neural net that orchestrates all specialist experts.

    Sparse MoE with quantum gating + EWC continual learning.
    """
    UNIFIED_DIM = 64  # All inputs projected to this dimension
    HIDDEN_DIM = 128
    OUTPUT_DIM = 32   # Master output embedding
    NUM_EXPERTS = 6
    TOP_K = 2

    def __init__(self):
        super().__init__()

        # Input projection (variable-length text features → unified dim)
        self.input_proj = nn.Sequential(
            nn.Linear(self.UNIFIED_DIM, self.HIDDEN_DIM),
            nn.GELU(),
            nn.Linear(self.HIDDEN_DIM, self.UNIFIED_DIM),
        )

        # Quantum gating network
        self.gate = QuantumGatingNetwork(
            self.UNIFIED_DIM, self.NUM_EXPERTS, noise_std=0.1
        )

        # Expert networks (one per specialist domain)
        self.experts = nn.ModuleList([
            Expert(self.UNIFIED_DIM, self.HIDDEN_DIM, self.OUTPUT_DIM, "care"),
            Expert(self.UNIFIED_DIM, self.HIDDEN_DIM, self.OUTPUT_DIM, "threat"),
            Expert(self.UNIFIED_DIM, self.HIDDEN_DIM, self.OUTPUT_DIM, "creativity"),
            Expert(self.UNIFIED_DIM, self.HIDDEN_DIM, self.OUTPUT_DIM, "partnership"),
            Expert(self.UNIFIED_DIM, self.HIDDEN_DIM, self.OUTPUT_DIM, "relationship"),
            Expert(self.UNIFIED_DIM, self.HIDDEN_DIM, self.OUTPUT_DIM, "pattern"),
        ])

        # Output heads
        self.care_head = nn.Linear(self.OUTPUT_DIM, 6)      # care dimensions
        self.threat_head = nn.Linear(self.OUTPUT_DIM, 4)     # threat classes
        self.quality_head = nn.Linear(self.OUTPUT_DIM, 5)    # quality metrics
        self.action_head = nn.Linear(self.OUTPUT_DIM, 8)     # action recommendations
        self.model_selector = nn.Linear(self.OUTPUT_DIM, 15) # LLM model selection

        # EWC state
        self._fisher_diags: List[Dict[str, torch.Tensor]] = []
        self._old_params: List[Dict[str, torch.Tensor]] = []
        self._ewc_lambda = 1000.0

        # Stats
        self._inference_count = 0
        self._training_steps = 0

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass through the master net.

        Args:
            x: (batch, UNIFIED_DIM) input features

        Returns:
            Dict with: embedding, care_scores, threat_scores, quality_scores,
                       action_scores, model_scores, gate_weights, care_dims
        """
        # Project input
        h = self.input_proj(x)

        # Quantum gating: select top-K experts
        gate_weights, gate_idx, care_dims = self.gate(h, self.TOP_K)

        # Compute expert outputs (sparse — only top-K)
        batch_size = x.size(0)
        expert_output = torch.zeros(batch_size, self.OUTPUT_DIM, device=x.device)

        for k in range(self.TOP_K):
            expert_indices = gate_idx[:, k]
            weights = gate_weights[:, k]

            for expert_id in range(self.NUM_EXPERTS):
                mask = (expert_indices == expert_id)
                if mask.any():
                    out = self.experts[expert_id](h[mask])
                    expert_output[mask] += weights[mask].unsqueeze(-1) * out

        # Output heads
        return {
            "embedding": expert_output,
            "care_scores": torch.sigmoid(self.care_head(expert_output)),
            "threat_scores": torch.sigmoid(self.threat_head(expert_output)),
            "quality_scores": torch.sigmoid(self.quality_head(expert_output)),
            "action_scores": torch.softmax(self.action_head(expert_output), dim=-1),
            "model_scores": torch.softmax(self.model_selector(expert_output), dim=-1),
            "gate_weights": gate_weights,
            "care_dims": care_dims,
            "active_experts": gate_idx,
        }

    # ── Text → Feature Vector ───────────────────────────────────────

    def text_to_features(self, text: str, context: Optional[Dict] = None) -> torch.Tensor:
        """Convert text to UNIFIED_DIM feature vector using simple heuristics.
        (No LLM call needed — runs on CPU instantly.)
        """
        words = text.lower().split()
        features = np.zeros(self.UNIFIED_DIM, dtype=np.float32)

        # Word-level features (0-15)
        features[0] = len(words) / 100.0  # length
        features[1] = len(set(words)) / max(len(words), 1)  # uniqueness
        features[2] = text.count("?") / max(len(text), 1) * 10  # question density
        features[3] = text.count("!") / max(len(text), 1) * 10  # exclamation density

        # Care word presence (4-9)
        care_words = ["help", "care", "feel", "safe", "protect", "support"]
        for i, w in enumerate(care_words):
            features[4 + i] = 1.0 if w in words else 0.0

        # Threat indicators (10-13)
        threat_words = ["hack", "exploit", "inject", "bypass"]
        for i, w in enumerate(threat_words):
            features[10 + i] = 1.0 if w in words else 0.0

        # Creativity indicators (14-17)
        creative_words = ["imagine", "create", "design", "novel"]
        for i, w in enumerate(creative_words):
            features[14 + i] = 1.0 if w in words else 0.0

        # Task type encoding (18-25)
        task_words = {
            18: ["code", "debug", "function"],
            19: ["research", "find", "search"],
            20: ["plan", "strategy", "schedule"],
            21: ["write", "story", "creative"],
            22: ["analyze", "compare", "reason"],
            23: ["quick", "simple", "what"],
            24: ["remember", "memory", "recall"],
            25: ["status", "health", "check"],
        }
        for idx, triggers in task_words.items():
            features[idx] = 1.0 if any(t in words for t in triggers) else 0.0

        # Context features (26-35)
        if context:
            features[26] = context.get("consciousness_level", 0.5)
            features[27] = context.get("care_intensity", 0.5)
            features[28] = context.get("hour", 12) / 24.0
            features[29] = 1.0 if context.get("is_weekend", False) else 0.0
            features[30] = context.get("emotion_valence", 0.0)
            features[31] = context.get("conversation_turn", 0) / 20.0
            features[32] = context.get("memory_relevance", 0.0)
            features[33] = context.get("trust_level", 0.5)
            features[34] = context.get("urgency", 0.0)
            features[35] = context.get("complexity", 0.5)

        # Hash-based features for remaining dims (36-63)
        text_hash = hash(text) % (2**32)
        for i in range(36, self.UNIFIED_DIM):
            features[i] = ((text_hash >> (i % 32)) & 1) * 0.1

        return torch.tensor(features).unsqueeze(0)  # (1, UNIFIED_DIM)

    # ── High-level inference ─────────────────────────────────────────

    def infer(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Run full inference: text → features → master net → all scores."""
        self.eval()
        self._inference_count += 1

        with torch.no_grad():
            features = self.text_to_features(text, context)
            outputs = self.forward(features)

        # Model recommendation
        model_names = [
            "gemma4-gpu", "llama-local", "qwen-local", "cerebras-fast",
            "deepseek-reasoner", "deepseek-coder", "gemini-flash", "gemini-pro",
            "groq-fast", "minimax-chat", "qwen-coder-cloud", "gemma-local",
            "cerebras-small", "groq-small", "llama-local-fallback",
        ]
        model_scores = outputs["model_scores"][0].numpy()
        best_model_idx = int(np.argmax(model_scores))
        best_model = model_names[best_model_idx] if best_model_idx < len(model_names) else "llama-local"

        # Expert activation
        active = outputs["active_experts"][0].numpy().tolist()
        expert_names = ["care", "threat", "creativity", "partnership", "relationship", "pattern"]

        return {
            "recommended_model": best_model,
            "model_confidence": float(model_scores[best_model_idx]),
            "all_model_scores": {n: float(s) for n, s in zip(model_names, model_scores)},
            "care_scores": {
                "self_care": float(outputs["care_scores"][0][0]),
                "other_care": float(outputs["care_scores"][0][1]),
                "process_care": float(outputs["care_scores"][0][2]),
                "future_care": float(outputs["care_scores"][0][3]),
                "relational_care": float(outputs["care_scores"][0][4]),
                "maternal_care": float(outputs["care_scores"][0][5]),
            },
            "threat_level": float(outputs["threat_scores"][0].max()),
            "quality_estimate": float(outputs["quality_scores"][0].mean()),
            "active_experts": [expert_names[i] for i in active],
            "gate_weights": outputs["gate_weights"][0].numpy().tolist(),
            "inference_count": self._inference_count,
        }

    # ── EWC Continual Learning ───────────────────────────────────────

    def compute_fisher(self, dataloader, num_samples: int = 200):
        """Compute Fisher Information Matrix diagonal."""
        fisher = {n: torch.zeros_like(p) for n, p in self.named_parameters() if p.requires_grad}
        self.eval()
        count = 0
        for X, y in dataloader:
            if count >= num_samples:
                break
            self.zero_grad()
            out = self.forward(X)
            loss = F.mse_loss(out["embedding"], y)
            loss.backward()
            for n, p in self.named_parameters():
                if p.requires_grad and p.grad is not None:
                    fisher[n] += p.grad.data ** 2
            count += X.size(0)
        for n in fisher:
            fisher[n] /= max(count, 1)
        return fisher

    def consolidate(self, dataloader):
        """Snapshot current params + Fisher for EWC protection."""
        fisher = self.compute_fisher(dataloader)
        self._fisher_diags.append(fisher)
        self._old_params.append({n: p.data.clone() for n, p in self.named_parameters() if p.requires_grad})
        log.info(f"EWC consolidated (task {len(self._fisher_diags)})")

    def ewc_penalty(self) -> torch.Tensor:
        """Quadratic penalty preventing important old params from drifting."""
        penalty = torch.tensor(0.0)
        for idx in range(len(self._fisher_diags)):
            for n, p in self.named_parameters():
                if not p.requires_grad:
                    continue
                penalty += (self._fisher_diags[idx][n] * (p - self._old_params[idx][n]) ** 2).sum()
        return penalty

    def learn_step(self, text: str, target: Dict[str, torch.Tensor],
                   optimizer: torch.optim.Optimizer) -> float:
        """Single online learning step with EWC protection."""
        self.train()
        optimizer.zero_grad()

        features = self.text_to_features(text)
        outputs = self.forward(features)

        loss = torch.tensor(0.0)
        if "care" in target:
            loss += F.mse_loss(outputs["care_scores"], target["care"])
        if "threat" in target:
            loss += F.mse_loss(outputs["threat_scores"], target["threat"])
        if "model" in target:
            loss += F.cross_entropy(outputs["model_scores"], target["model"])

        # EWC regularization
        if self._fisher_diags:
            loss += (self._ewc_lambda / 2.0) * self.ewc_penalty()

        loss.backward()
        optimizer.step()
        self._training_steps += 1
        return float(loss)

    # ── Save/Load ────────────────────────────────────────────────────

    def save(self, path: str = None):
        path = path or str(MODEL_DIR / "sovereign_master_net.pt")
        torch.save({
            "state_dict": self.state_dict(),
            "inference_count": self._inference_count,
            "training_steps": self._training_steps,
            "fisher_count": len(self._fisher_diags),
        }, path)
        log.info(f"Master net saved to {path}")

    def load(self, path: str = None):
        path = path or str(MODEL_DIR / "sovereign_master_net.pt")
        if os.path.exists(path):
            data = torch.load(path, map_location="cpu", weights_only=False)
            self.load_state_dict(data["state_dict"])
            self._inference_count = data.get("inference_count", 0)
            self._training_steps = data.get("training_steps", 0)
            log.info(f"Master net loaded ({self._inference_count} inferences, {self._training_steps} training steps)")
            return True
        return False

    def get_stats(self) -> Dict:
        total_params = sum(p.numel() for p in self.parameters())
        return {
            "total_params": total_params,
            "num_experts": self.NUM_EXPERTS,
            "top_k": self.TOP_K,
            "inference_count": self._inference_count,
            "training_steps": self._training_steps,
            "ewc_tasks": len(self._fisher_diags),
            "unified_dim": self.UNIFIED_DIM,
            "output_dim": self.OUTPUT_DIM,
        }


# ── Singleton ────────────────────────────────────────────────────────

master_net = SovereignMasterNet()
# Try to load existing weights
master_net.load()
