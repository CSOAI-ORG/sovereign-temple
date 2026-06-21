#!/usr/bin/env python3
"""
RunPod Serverless Handler — Train MEOKCLAW LoRA on demand.
Deploy this as a RunPod serverless endpoint for bursty training.
"""
import os
import sys
import tarfile
import tempfile
from pathlib import Path

# RunPod serverless boilerplate
def handler(event):
    """RunPod serverless handler entrypoint."""
    job_input = event.get("input", {})
    model_name = job_input.get("model", "unsloth/Qwen2.5-7B-Instruct")
    epochs = job_input.get("epochs", 3)
    lora_r = job_input.get("lora_r", 16)

    print(f"🚀 Starting training: {model_name}")
    print(f"   Epochs: {epochs} | LoRA r: {lora_r}")

    # Set env vars
    os.environ["FT_MODEL"] = model_name

    # Run training
    sys.path.insert(0, "/Users/nicholas/clawd/sovereign-temple")
    import train_lora
    train_lora.NUM_EPOCHS = epochs
    train_lora.LORA_R = lora_r
    train_lora.main()

    # Package output
    output_dir = Path("/Users/nicholas/clawd/sovereign-temple/data/finetune_output")
    tar_path = "/tmp/meokclaw_lora.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(output_dir, arcname="finetune_output")

    return {
        "status": "success",
        "model": model_name,
        "epochs": epochs,
        "artifact_url": f"file://{tar_path}",
        "output_dir": str(output_dir),
    }


if __name__ == "__main__":
    # Local test
    print("RunPod handler ready. Test with:")
    print("  python3 runpod_train_handler.py")
    print("")
    print("For RunPod deployment, wrap this in their handler template.")
    print("See: https://docs.runpod.io/serverless/workers/handlers")
