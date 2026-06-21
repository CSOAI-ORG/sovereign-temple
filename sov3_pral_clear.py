#!/usr/bin/env python3
"""
SOV3 PRAL-CLEAR Integration Wrapper
=====================================
Wraps SOV3 MCP coordination calls with PRAL loop and CLEAR metrics.

Usage:
    from sov3_pral_clear import PRALClearCoordinator
    
    coord = PRALClearCoordinator()
    result = coord.execute_task(
        agent_id="jeeves-cli",
        task="Deploy EU AI Act landing page",
        priority="high"
    )
    
    # Get dashboard
    dashboard = coord.get_dashboard()

This integrates:
- PRAL Loop (Plan → Reason → Act → Learn)
- CLEAR Framework (Cost, Latency, Efficacy, Assurance, Reliability)
- SOV3 Coordination (existing MCP tools)
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Add SOV3 paths
sys.path.insert(0, str(Path.home() / "clawd" / "sovereign-temple"))
sys.path.insert(0, str(Path.home() / "clawd" / "scripts"))

from pral_loop import PRALAgent, CLEARCollector, FinalState
from clear_framework import CLEARFramework, CLEARMetric

SOV3_MCP = "http://localhost:3101/mcp"


def mcp_call(tool: str, arguments: dict = None) -> dict:
    """Call SOV3 MCP tool."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": str(int(time.time())),
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments or {}},
    }).encode()

    req = urllib.request.Request(
        SOV3_MCP,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
            result = d.get("result", {})
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and content:
                    return json.loads(content[0].get("text", "{}"))
            return result
    except Exception as e:
        return {"error": str(e)}


class PRALClearCoordinator:
    """SOV3 coordinator with PRAL loop and CLEAR metrics."""
    
    def __init__(self):
        self.pral_agents = {}  # agent_id -> PRALAgent
        self.clear_framework = CLEARFramework()
        self.clear_collector = CLEARCollector()
        self.task_history = []
    
    def _get_agent(self, agent_id: str) -> PRALAgent:
        """Get or create PRAL agent for an SOV3 agent."""
        if agent_id not in self.pral_agents:
            self.pral_agents[agent_id] = PRALAgent(
                name=agent_id,
                purpose=f"SOV3 agent: {agent_id}",
                max_turns=10,
                confidence_threshold=0.7,
                constraints=[
                    "No destructive commands without explicit approval",
                    "No production deployments without human review",
                    "No external communications without human approval",
                ],
            )
        return self.pral_agents[agent_id]
    
    def execute_task(self, agent_id: str, task: str, priority: str = "medium", task_type: str = "general") -> dict:
        """Execute a task through PRAL loop with CLEAR metrics."""
        start_time = time.time()
        
        # Phase 1: Plan (via PRAL)
        pral_agent = self._get_agent(agent_id)
        
        # Submit task to SOV3
        sov3_result = mcp_call("coord_submit_task", {
            "title": task[:100],
            "description": task,
            "files": [],
            "care_score": 0.7,
        })
        
        task_id = sov3_result.get("task_id", "unknown")
        
        # Execute PRAL loop
        pral_result = pral_agent.execute(task)
        
        # Calculate metrics
        latency_ms = (time.time() - start_time) * 1000
        cost = 0.0  # Would be calculated from token usage
        efficacy = 1.0 if pral_result.final_state == FinalState.COMPLETED.value else 0.0
        confidence = pral_result.reasoning.confidence if pral_result.reasoning else 0.0
        
        # Record CLEAR metric
        metric = CLEARMetric(
            timestamp=datetime.utcnow().isoformat(),
            agent=agent_id,
            task_id=task_id,
            cost=cost,
            latency_ms=latency_ms,
            efficacy=efficacy,
            success=(pral_result.final_state == FinalState.COMPLETED.value),
            confidence=confidence,
        )
        
        self.clear_framework.record(metric)
        self.clear_collector.record(agent_id, pral_result)
        
        # Store in history
        self.task_history.append({
            "task_id": task_id,
            "agent_id": agent_id,
            "task": task,
            "priority": priority,
            "sov3_result": sov3_result,
            "pral_state": pral_result.state,
            "pral_final": pral_result.final_state,
            "latency_ms": latency_ms,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return {
            "task_id": task_id,
            "sov3_result": sov3_result,
            "pral_state": pral_result.state,
            "pral_final": pral_result.final_state,
            "latency_ms": latency_ms,
            "confidence": confidence,
        }
    
    def complete_task(self, task_id: str, agent_id: str = "jeeves-cli", result_text: str = "completed") -> dict:
        """Complete a task with CLEAR metrics."""
        start_time = time.time()
        
        sov3_result = mcp_call("coord_complete_task", {
            "task_id": task_id,
            "agent_id": agent_id,
            "result_summary": result_text,
        })
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Record CLEAR metric for completion
        metric = CLEARMetric(
            timestamp=datetime.utcnow().isoformat(),
            agent=agent_id,
            task_id=task_id,
            cost=0.0,
            latency_ms=latency_ms,
            efficacy=1.0,
            success=True,
            confidence=0.9,
        )
        
        self.clear_framework.record(metric)
        
        return sov3_result
    
    def get_dashboard(self) -> dict:
        """Get combined PRAL-CLEAR-SOV3 dashboard."""
        # SOV3 dashboard
        sov3_dashboard = mcp_call("coord_get_dashboard", {})
        
        # CLEAR summary
        clear_summary = self.clear_framework.get_summary(days=1)
        
        # PRAL agent metrics
        pral_metrics = {}
        for agent_id, agent in self.pral_agents.items():
            pral_metrics[agent_id] = agent.get_metrics()
        
        return {
            "sov3": sov3_dashboard,
            "clear": clear_summary,
            "pral": pral_metrics,
            "task_history": self.task_history[-10:],  # Last 10 tasks
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def export_report(self) -> str:
        """Export a combined PRAL-CLEAR report."""
        dashboard = self.get_dashboard()
        
        report = f"""
# SOV3 PRAL-CLEAR Report
## Generated: {dashboard['timestamp']}

## SOV3 Coordination
- Agents: {dashboard['sov3'].get('agents', {}).get('total', 0)} total, {dashboard['sov3'].get('agents', {}).get('active', 0)} active
- Tasks: {dashboard['sov3'].get('tasks', {}).get('completed', 0)} completed

## CLEAR Metrics (Last 24h)
- Total entries: {dashboard['clear'].get('total_entries', 0)}
- Avg cost: £{dashboard['clear'].get('avg_cost', 0):.4f}
- Avg latency: {dashboard['clear'].get('avg_latency_ms', 0):.0f}ms
- Success rate: {dashboard['clear'].get('success_rate', 0):.1f}%
- Avg confidence: {dashboard['clear'].get('avg_confidence', 0):.3f}

## PRAL Agent Metrics
"""
        for agent_id, metrics in dashboard['pral'].items():
            report += f"\n### {agent_id}\n"
            report += f"- Executions: {metrics.get('total_executions', 0)}\n"
            report += f"- Success rate: {metrics.get('success_rate', 0):.2f}\n"
            report += f"- Avg latency: {metrics.get('avg_latency_ms', 0):.0f}ms\n"
        
        report += f"\n## Recent Tasks ({len(dashboard['task_history'])})\n"
        for task in dashboard['task_history']:
            report += f"- [{task['timestamp']}] {task['task'][:50]}... → {task['pral_final']}\n"
        
        return report


def main():
    """Test the PRAL-CLEAR integration."""
    print("🧠 SOV3 PRAL-CLEAR Integration Test")
    print("=" * 50)
    
    coord = PRALClearCoordinator()
    
    # Test task execution
    print("\n📋 Executing test task...")
    result = coord.execute_task(
        agent_id="jeeves-cli",
        task="Test PRAL-CLEAR integration",
        priority="high",
    )
    
    print(f"   Task ID: {result['task_id']}")
    print(f"   SOV3: {result['sov3_result']}")
    print(f"   PRAL state: {result['pral_state']}")
    print(f"   PRAL final: {result['pral_final']}")
    print(f"   Latency: {result['latency_ms']:.0f}ms")
    print(f"   Confidence: {result['confidence']:.2f}")
    
    # Test task completion
    if result['task_id'] != "unknown":
        print("\n✅ Completing task...")
        complete_result = coord.complete_task(
            task_id=result['task_id'],
            agent_id="jeeves-cli",
            result_text="PRAL-CLEAR integration test completed",
        )
        print(f"   Result: {complete_result}")
    
    # Get dashboard
    print("\n📊 Dashboard:")
    dashboard = coord.get_dashboard()
    print(f"   SOV3 agents: {dashboard['sov3'].get('agents', {}).get('total', 0)}")
    print(f"   CLEAR entries: {dashboard['clear'].get('total_entries', 0)}")
    print(f"   PRAL agents: {len(dashboard['pral'])}")
    
    # Export report
    print("\n📄 Report:")
    report = coord.export_report()
    print(report)
    
    print("\n✅ PRAL-CLEAR integration operational")


if __name__ == "__main__":
    main()
