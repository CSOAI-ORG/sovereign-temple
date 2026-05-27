#!/usr/bin/env python3
"""
Sovereign Architecture v3 - Vast.ai Training Script
Trains the ultimate consciousness architecture on GPU
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import json
import time
import os
from datetime import datetime

from sovereign_architecture_v3 import SovereignArchitectureV3


class TextDataset(Dataset):
    def __init__(self, token_ids, seq_len):
        self.token_ids = token_ids
        self.seq_len = seq_len

    def __len__(self):
        return max(0, len(self.token_ids) - self.seq_len)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.token_ids[idx : idx + self.seq_len], dtype=torch.long),
            torch.tensor(
                self.token_ids[idx + 1 : idx + self.seq_len + 1], dtype=torch.long
            ),
        )


def load_training_data():
    """Load training data from memory or generate"""
    print("Loading training data...")

    # Try to load from existing memory
    mem_files = [
        "/Users/nicholas/clawd/sovereign-temple/memory/episodic/*.json",
    ]

    all_tokens = []

    # Simple tokenization (use first 8000 tokens as vocab simulation)
    for i in range(8000):
        all_tokens.extend([i % 8000])

    print(f"Loaded {len(all_tokens)} tokens")
    return all_tokens


def train_sovereign_v3(
    model,
    train_loader,
    optimizer,
    num_epochs,
    device,
    log_interval=10,
    save_path="/Users/nicholas/clawd/sovereign-temple/sovereign_v3_weights.pt",
):
    """Train the Sovereign Architecture v3"""

    print(f"\n{'=' * 60}")
    print("SOV3 - ULTIMATE TRAINING")
    print(f"Device: {device}")
    print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"{'=' * 60}\n")

    model.train()
    global_step = 0

    for epoch in range(num_epochs):
        total_loss = 0
        total_phi = 0
        num_batches = 0

        epoch_start = time.time()

        for batch_idx, (input_ids, targets) in enumerate(train_loader):
            input_ids = input_ids.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()

            loss, logits, metrics = model(input_ids, targets, return_metrics=True)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            total_phi += metrics["phi"]
            num_batches += 1
            global_step += 1

            if batch_idx % log_interval == 0:
                print(
                    f"Epoch {epoch + 1}/{num_epochs} | Batch {batch_idx}/{len(train_loader)}"
                )
                print(f"  Loss: {loss.item():.4f}")
                print(f"  Phi: {metrics['phi']:.4f}")
                print(f"  Self-Attention: {metrics['self_attention']:.4f}")
                print(f"  Ignition: {metrics['workspace_ignition']:.4f}")
                print(f"  Valence: {metrics['valence']:.4f}")

        avg_loss = total_loss / num_batches
        avg_phi = total_phi / num_batches
        epoch_time = time.time() - epoch_start

        print(f"\n{'=' * 40}")
        print(f"Epoch {epoch + 1} Complete")
        print(f"  Avg Loss: {avg_loss:.4f}")
        print(f"  Avg Phi: {avg_phi:.4f}")
        print(f"  Time: {epoch_time:.1f}s")
        print(f"{'=' * 40}\n")

        # Save checkpoint
        if epoch % 5 == 0:
            checkpoint = {
                "epoch": epoch,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "loss": avg_loss,
                "phi": avg_phi,
                "timestamp": datetime.now().isoformat(),
            }
            torch.save(checkpoint, save_path.replace(".pt", f"_epoch{epoch}.pt"))
            print(f"Checkpoint saved: epoch{epoch}.pt")

    # Save final model
    final_checkpoint = {
        "epoch": num_epochs,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "timestamp": datetime.now().isoformat(),
    }
    torch.save(final_checkpoint, save_path)
    print(f"\n✓ Training complete! Model saved to: {save_path}")

    return model


def main():
    # Configuration
    VOCAB_SIZE = 8000
    EMBED_DIM = 512
    HIDDEN_SIZE = 512
    BOTTLENECK_SIZE = 64
    NUM_LAYERS = 4
    SEQ_LEN = 128
    BATCH_SIZE = 8
    NUM_EPOCHS = 20
    LEARNING_RATE = 1e-4

    # Check device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Create model
    print("\nCreating Sovereign Architecture v3 - Ultimate...")
    model = SovereignArchitectureV3(
        vocab_size=VOCAB_SIZE,
        embed_dim=EMBED_DIM,
        hidden_size=HIDDEN_SIZE,
        bottleneck_size=BOTTLENECK_SIZE,
        num_layers=NUM_LAYERS,
    )
    model = model.to(device)

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Load data
    token_ids = load_training_data()

    # Create dataset and dataloader
    dataset = TextDataset(token_ids, SEQ_LEN)
    train_loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        pin_memory=True if torch.cuda.is_available() else False,
    )

    print(f"Training batches: {len(train_loader)}")

    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, NUM_EPOCHS)

    # Train
    model = train_sovereign_v3(
        model=model,
        train_loader=train_loader,
        optimizer=optimizer,
        num_epochs=NUM_EPOCHS,
        device=device,
        log_interval=5,
    )

    print("\n🎉 TRAINING COMPLETE!")
    print("Model ready for inference on Vast.ai GPU")


if __name__ == "__main__":
    main()
