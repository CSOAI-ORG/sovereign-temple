#!/bin/bash
# 3.1_temporal.sh - Durable workflows (workflows survive crashes)
# MIT License - Netflix uses this

set -e

echo "🧬 Deploying Temporal Server..."

# Quick start with Docker
docker run -d --name temporal \
  -p 7233:7233 \
  -p 8233:8233 \
  temporalio/auto-setup:latest

# Or use docker-compose for production
cat > /meok/docker-compose.temporal.yml << 'EOF'
version: '3.8'
services:
  temporal:
    image: temporalio/server:1.23.0
    ports:
      - "7233:7233"
      - "8233:8233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=sovereign
      - POSTGRES_PWD=dragon
      - POSTGRES_DB=temporal
    volumes:
      - temporal-data:/var/lib/temporal

  temporal-web:
    image: temporalio/web:1.23.0
    ports:
      - "8088:8088"
    environment:
      - TEMPORAL_ADDRESS=temporal:7233

volumes:
  temporal-data:
EOF

# Create worker script
cat > /meok/legion/legion_orchestrator.py << 'EOF'
"""Temporal workflow for farm management"""
import asyncio
from temporalio import workflow, activity
from datetime import timedelta
import logging

@activity.defn
async def collect_sensor_data() -> dict:
    """Collect farm sensor data"""
    return {"ph": 7.2, "temp": 18.5, "oxygen": 85}

@activity.defn
async def analyze_with_legion(data: dict) -> dict:
    """Legion-Super decision"""
    return {"action": "maintain", "confidence": 0.9}

@activity.defn
async def execute_action(action: dict) -> bool:
    """Execute farm control"""
    return True

@workflow.defn
class FarmWorkflow:
    @workflow.run
    async def run(self) -> dict:
        # Step 1: Collect
        data = await workflow.execute_activity(
            collect_sensor_data,
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 2: Analyze
        decision = await workflow.execute_activity(
            analyze_with_legion,
            data,
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        # Step 3: Execute
        result = await workflow.execute_activity(
            execute_action,
            decision,
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        return {"status": "success", "decision": decision}

if __name__ == "__main__":
    asyncio.run(FarmWorkflow.run())
EOF

echo "✅ Temporal deployed"
echo "🌐 Web UI: http://localhost:8088"
echo "📁 Workflow: /meok/legion/legion_orchestrator.py"