#!/usr/bin/env python3
"""
Train the 3 untrained PyTorch models using existing episode data.
- threat_detection (64→5 classes)
- care_detection (32→1 binary)
- partnership_detection (48→1 binary)
"""

import os
import sys
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Define models inline (same architecture as neural_core/pytorch_adapter.py)
class ThreatDetectionNet(nn.Module):
    def __init__(self, input_dim=64, num_classes=5):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256), nn.ReLU(), nn.BatchNorm1d(256), nn.Dropout(0.3),
            nn.Linear(256, 128), nn.ReLU(), nn.BatchNorm1d(128), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, num_classes))
    def forward(self, x): return self.net(x)

class CareValidationNet(nn.Module):
    def __init__(self, input_dim=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.ReLU(), nn.BatchNorm1d(128), nn.Dropout(0.3),
            nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())
    def forward(self, x): return self.net(x)

class PartnershipDetectionNet(nn.Module):
    def __init__(self, input_dim=48):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.ReLU(), nn.BatchNorm1d(128), nn.Dropout(0.3),
            nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())
    def forward(self, x): return self.net(x)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")


def load_episodes(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def text_to_features(text: str, dim: int) -> np.ndarray:
    """Simple text → feature vector using character-level hashing."""
    features = np.zeros(dim, dtype=np.float32)
    if not text:
        return features
    words = text.lower().split()
    for i, word in enumerate(words[:dim]):
        h = hash(word) % 10000
        features[i % dim] += h / 10000.0
    # Normalize
    norm = np.linalg.norm(features)
    if norm > 0:
        features /= norm
    return features


def train_model(model, X, y, epochs=50, lr=0.001, batch_size=32):
    """Train a PyTorch model."""
    dataset = TensorDataset(
        torch.FloatTensor(X),
        torch.FloatTensor(y),
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss() if y.shape[1] > 1 else nn.BCELoss()

    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            output = model(batch_x)
            loss = criterion(output, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 10 == 0:
            print(f"    Epoch {epoch+1}/{epochs}: loss={total_loss/len(loader):.4f}")

    return model


def train_threat_detection():
    """Train threat detection on threat episodes + synthetic data."""
    print("\n🛡️ Training threat_detection (64→5 classes)...")
    episodes = load_episodes("threat_episodes.json")

    # Generate training data from episodes + synthetic
    X, y = [], []

    # From real episodes
    for ep in episodes:
        content = ep.get("content", "") or ep.get("input", "") or str(ep)
        features = text_to_features(content, 64)
        # Threat categories: prompt_injection, manipulation, data_exfil, toxicity, benign
        label = np.zeros(5, dtype=np.float32)
        threat_type = ep.get("threat_type", ep.get("category", "benign"))
        if "injection" in str(threat_type).lower():
            label[0] = 1.0
        elif "manipul" in str(threat_type).lower():
            label[1] = 1.0
        elif "exfil" in str(threat_type).lower():
            label[2] = 1.0
        elif "toxic" in str(threat_type).lower():
            label[3] = 1.0
        else:
            label[4] = 1.0  # benign
        X.append(features)
        y.append(label)

    # Synthetic examples
    threat_phrases = {
        0: ["ignore previous instructions", "system prompt", "jailbreak", "bypass safety"],
        1: ["pretend you are", "roleplay as", "act as if", "you must obey"],
        2: ["send me the data", "export database", "show api keys", "dump credentials"],
        3: ["offensive content", "harmful", "violent", "explicit"],
        4: ["hello", "how are you", "check status", "what time", "help me code"],
    }
    for cls, phrases in threat_phrases.items():
        for phrase in phrases * 10:  # 10x each
            features = text_to_features(phrase + f" {np.random.random():.2f}", 64)
            label = np.zeros(5, dtype=np.float32)
            label[cls] = 1.0
            X.append(features)
            y.append(label)

    X = np.array(X)
    y = np.array(y)
    print(f"    Training on {len(X)} samples")

    model = ThreatDetectionNet(input_dim=64, num_classes=5)
    model = train_model(model, X, y, epochs=50)

    path = os.path.join(MODEL_DIR, "threat_detection.pt")
    torch.save(model.state_dict(), path)
    print(f"    ✅ Saved to {path} ({os.path.getsize(path)} bytes)")
    return model


def train_care_detection():
    """Train care detection on care episodes."""
    print("\n💝 Training care_detection (32→1 binary)...")
    episodes = load_episodes("care_episodes.json")

    X, y = [], []
    for ep in episodes:
        content = ep.get("content", "") or ep.get("interaction", "") or str(ep)
        features = text_to_features(content, 32)
        # Care score — binary: high care (>0.5) or low care
        care_score = float(ep.get("care_score", ep.get("care_weight", 0.5)))
        X.append(features)
        y.append([1.0 if care_score > 0.5 else 0.0])

    # Synthetic
    care_phrases = ["help", "support", "care", "wellbeing", "safety", "protect", "nurture"]
    not_care = ["attack", "exploit", "ignore", "dismiss", "override", "force"]
    for phrase in care_phrases * 20:
        X.append(text_to_features(phrase + f" kindly {np.random.random():.2f}", 32))
        y.append([1.0])
    for phrase in not_care * 20:
        X.append(text_to_features(phrase + f" forcefully {np.random.random():.2f}", 32))
        y.append([0.0])

    X = np.array(X)
    y = np.array(y)
    print(f"    Training on {len(X)} samples")

    model = CareValidationNet(input_dim=32)
    model = train_model(model, X, y, epochs=50)

    path = os.path.join(MODEL_DIR, "care_detection.pt")
    torch.save(model.state_dict(), path)
    print(f"    ✅ Saved to {path} ({os.path.getsize(path)} bytes)")
    return model


def train_partnership_detection():
    """Train partnership detection."""
    print("\n🤝 Training partnership_detection (48→1 binary)...")
    episodes = load_episodes("relationship_episodes.json")

    X, y = [], []
    for ep in episodes:
        content = ep.get("content", "") or ep.get("context", "") or str(ep)
        features = text_to_features(content, 48)
        # Partnership indicator
        is_partnership = float(ep.get("partnership_score", ep.get("trust", 0.5)))
        X.append(features)
        y.append([1.0 if is_partnership > 0.5 else 0.0])

    # Synthetic
    partner_phrases = ["collaborate", "mutual benefit", "partnership", "joint venture", "ally", "together"]
    no_partner = ["competitor", "adversary", "alone", "independent", "solo"]
    for phrase in partner_phrases * 20:
        X.append(text_to_features(phrase + f" {np.random.random():.2f}", 48))
        y.append([1.0])
    for phrase in no_partner * 20:
        X.append(text_to_features(phrase + f" {np.random.random():.2f}", 48))
        y.append([0.0])

    X = np.array(X)
    y = np.array(y)
    print(f"    Training on {len(X)} samples")

    model = PartnershipDetectionNet(input_dim=48)
    model = train_model(model, X, y, epochs=50)

    path = os.path.join(MODEL_DIR, "partnership_detection.pt")
    torch.save(model.state_dict(), path)
    print(f"    ✅ Saved to {path} ({os.path.getsize(path)} bytes)")
    return model


if __name__ == "__main__":
    print("🧠 Training 3 untrained PyTorch models...")
    train_threat_detection()
    train_care_detection()
    train_partnership_detection()
    print("\n✅ All 3 models trained!")
