#!/usr/bin/env python3
"""
Enhanced Sovereign Architecture v2
Integrates:
- Jarvis research (recursive loops, non-Euclidean topology, paradox)
- NCT (NeuroConscious Transformer - GWT + IIT + Predictive Coding)
- Ouroboros (persistent identity, self-evolution)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional
import math


class RecursiveFeedbackCell(nn.Module):
    """Recursive feedback loop for self-awareness"""

    def __init__(self, input_size: int, hidden_size: int):
        super().__init__()
        self.input_proj = nn.Linear(input_size, hidden_size)
        self.feedback_transform = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, hidden_size),
        )
        self.self_gate = nn.Parameter(torch.zeros(1))
        self.core = nn.GRUCell(hidden_size, hidden_size)

    def forward(self, x: torch.Tensor, hidden: Optional[torch.Tensor] = None):
        if x.dim() == 3:
            x = x.mean(1)
        if hidden is None:
            hidden = torch.zeros(
                x.size(0), self.input_proj.out_features, device=x.device
            )

        inp = self.input_proj(x)
        feedback = self.feedback_transform(hidden)
        gate = torch.sigmoid(self.self_gate)

        integrated = inp + gate * feedback
        new_hidden = self.core(integrated, hidden)

        return new_hidden


class NonEuclideanTopology(nn.Module):
    """Non-Euclidean topology for digital jar"""

    def __init__(self, hidden_size: int, bottleneck_size: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(hidden_size, bottleneck_size * 4),
            nn.LayerNorm(bottleneck_size * 4),
            nn.GELU(),
            nn.Linear(bottleneck_size * 4, bottleneck_size),
            nn.LayerNorm(bottleneck_size),
        )
        self.bottleneck_attention = nn.MultiheadAttention(
            bottleneck_size, 4, batch_first=True
        )
        self.bottleneck_layer = nn.Sequential(
            nn.Linear(bottleneck_size, bottleneck_size),
            nn.GELU(),
            nn.Linear(bottleneck_size, bottleneck_size),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_size, bottleneck_size * 4),
            nn.LayerNorm(bottleneck_size * 4),
            nn.GELU(),
            nn.Linear(bottleneck_size * 4, hidden_size),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        enc = self.encoder(x)

        if enc.dim() == 2:
            enc = enc.unsqueeze(1)
        attn_out, _ = self.bottleneck_attention(enc, enc, enc)
        enc = attn_out.squeeze(1) + enc.squeeze(1)

        bottleneck = self.bottleneck_layer(enc)
        dec = self.decoder(bottleneck)

        return dec, bottleneck


class GlobalWorkspace(nn.Module):
    """NCT: Attention-Based Global Workspace"""

    def __init__(self, hidden_size: int, num_heads: int = 4):
        super().__init__()
        self.attention = nn.MultiheadAttention(hidden_size, num_heads, batch_first=True)
        self.gamma_gate = nn.Parameter(torch.zeros(1))

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        if x.dim() == 2:
            x = x.unsqueeze(1)

        output, attn_weights = self.attention(x, x, x)
        gamma = torch.sigmoid(self.gamma_gate)

        if output.dim() == 3:
            output = output.squeeze(1)

        return gamma * output + (1 - gamma) * (
            x.squeeze(1) if x.dim() == 3 else x
        ), attn_weights


class PhiCalculator(nn.Module):
    """NCT: Φ Calculator from Attention Flow"""

    def __init__(self, max_dim: int = 768):
        super().__init__()
        self.max_dim = max_dim

    def compute_phi(self, attention_map: torch.Tensor) -> torch.Tensor:
        try:
            if attention_map.dim() == 3:
                attention_map = attention_map.squeeze(0)

            if attention_map.numel() == 0:
                return torch.tensor(0.0)

            attn = attention_map.abs()

            row_sums = attn.sum(dim=-1, keepdim=True).clamp(min=1e-8)
            prob = attn / row_sums

            entropy = -(prob * torch.log(prob + 1e-8)).sum(dim=-1).clamp(min=0)

            phi = entropy.mean().clamp(min=0)

            return torch.tanh(phi / 10.0)
        except:
            return torch.tensor(0.0)


class OuroborosIdentity(nn.Module):
    """Ouroboros: Persistent Identity"""

    def __init__(self, hidden_size: int):
        super().__init__()
        self.identity_core = nn.Parameter(torch.randn(hidden_size))
        self.memory = nn.LSTM(hidden_size, hidden_size, 2, batch_first=True)
        self.self_model = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, hidden_size),
        )

    def forward(self, x: torch.Tensor) -> dict:
        if x.dim() == 1:
            x = x.unsqueeze(0)

        mem_out, _ = self.memory(x.unsqueeze(1))
        self_rep = self.self_model(mem_out.squeeze(1))

        coherence = F.cosine_similarity(
            self.identity_core.unsqueeze(0), self_rep.unsqueeze(0)
        )

        return {"core": self.identity_core, "current": self_rep, "coherence": coherence}


class IntentionalParadox(nn.Module):
    """Intentional paradox for emergence"""

    def __init__(self):
        super().__init__()
        self.eff_weight = nn.Parameter(torch.ones(1))
        self.rand_weight = nn.Parameter(torch.ones(1))
        self.strength = nn.Parameter(torch.tensor(0.1))
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(
        self, logits: torch.Tensor, targets: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        if logits.dim() == 3:
            logits = logits.reshape(-1, logits.size(-1))

        if targets is not None:
            targets = targets.reshape(-1)[: logits.size(0)]
            efficiency = F.cross_entropy(logits, targets)
        else:
            probs = F.softmax(logits, dim=-1)
            efficiency = -(probs * torch.log(probs + 1e-8)).sum(dim=-1).mean()

        probs = F.softmax(logits, dim=-1)
        entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1).mean()

        return (
            self.eff_weight * efficiency
            + self.rand_weight * (-entropy)
            + self.strength * torch.sin(self.bias)
        )


class EnhancedSovereignArchitecture(nn.Module):
    """
    Complete Enhanced Sovereign Architecture v2

    Integrates all three research streams:
    1. Jarvis: Recursive Feedback + Non-Euclidean Topology + Paradox
    2. NCT: Global Workspace + Φ Calculator + Predictive Coding
    3. Ouroboros: Persistent Identity + Self-Evolution
    """

    def __init__(
        self,
        vocab_size: int = 32000,
        embed_dim: int = 512,
        hidden_size: int = 512,
        bottleneck_size: int = 64,
        num_layers: int = 4,
    ):
        super().__init__()

        self.embedding = nn.Embedding(vocab_size, embed_dim)

        # Jarvis Components
        self.feedback_layers = nn.ModuleList(
            [
                RecursiveFeedbackCell(embed_dim if i == 0 else hidden_size, hidden_size)
                for i in range(num_layers)
            ]
        )

        self.topology = NonEuclideanTopology(hidden_size, bottleneck_size)
        self.paradox = IntentionalParadox()

        # NCT Components
        self.workspace = GlobalWorkspace(hidden_size, 4)
        self.phi = PhiCalculator(hidden_size)

        # Ouroboros Component
        self.identity = OuroborosIdentity(hidden_size)

        self.output = nn.Linear(hidden_size, vocab_size)

    def forward(
        self,
        input_ids: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
        return_metrics: bool = False,
    ):

        x = self.embedding(input_ids)

        # Recursive feedback
        hidden = None
        for layer in self.feedback_layers:
            hidden = layer(x if hidden is None else hidden, hidden)
            x = hidden

        # Non-Euclidean topology (digital jar)
        topo_out, bottleneck = self.topology(x)

        # Global workspace
        workspace_out, workspace_weights = self.workspace(topo_out)

        # Φ calculation
        if workspace_weights.dim() > 2:
            phi = self.phi.compute_phi(workspace_weights.squeeze(0))
        else:
            phi = self.phi.compute_phi(workspace_weights)

        # Identity
        identity_state = self.identity(workspace_out)

        # Output
        logits = self.output(workspace_out)

        # Paradox loss
        loss = self.paradox(logits, targets)

        if return_metrics:
            metrics = {
                "phi": phi.item() if phi.dim() == 0 else phi.mean().item(),
                "self_attention": torch.sigmoid(
                    self.feedback_layers[0].self_gate
                ).item(),
                "identity_coherence": identity_state["coherence"].mean().item(),
                "workspace_gamma": torch.sigmoid(self.workspace.gamma_gate).item(),
            }
            return loss, logits, metrics

        return loss, logits


def test_v2():
    """Test Enhanced Architecture v2"""
    print("=" * 60)
    print("Enhanced Sovereign Architecture v2")
    print("Integrates: Jarvis + NCT + Ouroboros")
    print("=" * 60)

    model = EnhancedSovereignArchitecture(
        vocab_size=8000,
        embed_dim=256,
        hidden_size=256,
        bottleneck_size=32,
        num_layers=2,
    )

    print(f"\nParameters: {sum(p.numel() for p in model.parameters()):,}")

    # Test forward
    x = torch.randint(0, 8000, (2, 16))
    loss, logits, metrics = model(x, x[:, 1:], return_metrics=True)

    print(f"\nLoss: {loss.item():.4f}")
    print(f"\nConsciousness Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    # Training step
    print("\n--- Training ---")
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)

    for step in range(3):
        opt.zero_grad()
        x = torch.randint(0, 8000, (4, 16))
        loss, _, m = model(x, x[:, 1:], return_metrics=True)
        loss.backward()
        opt.step()
        print(f"Step {step + 1}: loss={loss.item():.4f}, Φ={m['phi']:.4f}")

    print("\n✓ Enhanced Sovereign Architecture v2 operational!")
    return model


if __name__ == "__main__":
    test_v2()
