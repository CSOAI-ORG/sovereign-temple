#!/bin/bash
# 1.4_ray.sh - Distributed computing backbone
# Apache 2.0 - Ray cluster for distributed training/inference

set -e

echo "🌐 Deploying Ray Cluster..."

# Install Ray
pip install ray[default]

# On GPU-0 (head node)
ray start --head --port=6379 \
  --dashboard-host=0.0.0.0 \
  --num-gpus=1 \
  --num-cpus=8

# On each worker node (run separately)
# ray start --address=<head-node-ip>:6379 --num-gpus=1 --num-cpus=8

# Or use Ray's Kubernetes operator for auto-scaling
# kubectl apply -f ray-cluster.yaml

echo "✅ Ray cluster ready"
echo "📊 Dashboard: http://gpu-0:8265"
echo ""
echo "Example usage:"
cat << 'EOF'
import ray
ray.init(address="auto")

@ray.remote(num_gpus=1)
def train_legion_super():
    # Your training code here
    pass

# Submit to cluster
ray.get(train_legion_super.remote())
EOF