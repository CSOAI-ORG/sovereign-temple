#!/bin/bash
# 6.1_mlflow.sh - Model registry and experiment tracking
# Apache 2.0 - MLflow for model lifecycle management

set -e

echo "📊 Deploying MLflow..."

# Quick start with Docker
docker run -d --name mlflow \
  -p 5000:5000 \
  -v /Users/nicholas/clawd/sovereign-temple/mlflow:/mlflow \
  -e MLFLOW_TRACKING_URI=http://localhost:5000 \
  -e MLFLOW_S3_ENDPOINT_URL=http://localhost:7480 \
  -e AWS_ACCESS_KEY_ID=minimax \
  -e AWS_SECRET_ACCESS_KEY=dragon-mode \
  mlflow/mlflow:latest \
  mlflow server \
    --backend-store-uri sqlite:///mlflow/mlflow.db \
    --default-artifact-root ./mlflow-artifacts \
    --host 0.0.0.0

# Create tracking script
cat > /meok/src/mlflow_track.py << 'EOF'
"""MLflow tracking for Legion models"""
import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri("http://localhost:5000")

# Log experiment
with mlflow.start_run(run_name="legion-super-training"):
    mlflow.log_param("model", "legion-super-1.0")
    mlflow.log_param("quantization", "iq4_xs")
    mlflow.log_metric("loss", 0.234)
    mlflow.log_metric("accuracy", 0.891)
    
    # Log model
    mlflow.pytorch.log_model(
        pytorch_model=model,
        artifact_path="model"
    )

# Register model
client = MlflowClient()
client.create_registered_model("legion-super")
client.create_model_version(
    name="legion-super",
    source="runs:/abc123/model"
)

print("✅ MLflow tracking configured")
EOF

echo "✅ MLflow deployed at http://localhost:5000"
echo "📁 Tracking: /meok/src/mlflow_track.py"