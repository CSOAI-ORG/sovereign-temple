#!/usr/bin/env python3
"""
CLEAR Framework — Cost, Latency, Efficacy, Assurance, Reliability
=================================================================
Blueprint Reference: Section 7.1 — Outcome-based measurement

Measures what matters: revenue, cost savings, customer satisfaction — not task completion rates.

Usage:
    python3 clear_framework.py --record --agent "eu-ai-act" --cost 0.05 --latency 1200 --success
    python3 clear_framework.py --summary --days 7
    python3 clear_framework.py --dashboard
    python3 clear_framework.py --export csv
"""

import os
import sys
import json
import time
import csv
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CLEAR_DIR = Path.home() / "clawd" / "memory" / "clear-metrics"
CLEAR_DIR.mkdir(parents=True, exist_ok=True)

# SLA thresholds
SLA_LATENCY_MS = 2000  # 2 seconds
SLA_COST_PER_QUERY = 0.01  # £0.01
SLA_EFFICACY = 0.8  # 80% success rate
SLA_CONFIDENCE = 0.7  # 70% confidence
SLA_UPTIME = 0.99  # 99% uptime


@dataclass
class CLEARMetric:
    """Single CLEAR metric entry."""
    timestamp: str
    agent: str
    task_id: str
    # Cost
    cost: float = 0.0
    # Latency
    latency_ms: float = 0.0
    # Efficacy
    efficacy: float = 0.0  # 0-1, did it achieve the business outcome?
    success: bool = False
    # Assurance
    confidence: float = 0.0
    constraints_violated: int = 0
    policy_violations: int = 0
    # Reliability
    retries: int = 0
    circuit_breaker_tripped: bool = False
    loop_detected: bool = False
    # Business outcomes
    revenue_impact: float = 0.0
    customer_satisfaction: float = 0.0
    retention_signal: bool = False
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "task_id": self.task_id,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "efficacy": self.efficacy,
            "success": self.success,
            "confidence": self.confidence,
            "constraints_violated": self.constraints_violated,
            "policy_violations": self.policy_violations,
            "retries": self.retries,
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "loop_detected": self.loop_detected,
            "revenue_impact": self.revenue_impact,
            "customer_satisfaction": self.customer_satisfaction,
            "retention_signal": self.retention_signal,
        }


class CLEARFramework:
    """CLEAR Framework implementation."""
    
    def __init__(self, output_dir: Path = CLEAR_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def record(self, metric: CLEARMetric):
        """Record a CLEAR metric entry."""
        daily_file = self.output_dir / f"clear-{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        with open(daily_file, "a") as f:
            f.write(json.dumps(metric.to_dict()) + "\n")
    
    def get_summary(self, agent: str = None, days: int = 7) -> dict:
        """Get CLEAR summary for an agent or all agents."""
        cutoff = datetime.now() - timedelta(days=days)
        metrics = []
        
        for i in range(days):
            date = cutoff + timedelta(days=i)
            daily_file = self.output_dir / f"clear-{date.strftime('%Y-%m-%d')}.jsonl"
            
            if daily_file.exists():
                with open(daily_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if agent and entry.get("agent") != agent:
                                continue
                            metrics.append(entry)
                        except json.JSONDecodeError:
                            continue
        
        if not metrics:
            return {"error": "No metrics found", "days_searched": days}
        
        # Calculate CLEAR metrics
        total = len(metrics)
        
        # Cost
        total_cost = sum(m.get("cost", 0) for m in metrics)
        avg_cost = total_cost / total if total > 0 else 0
        
        # Latency
        latencies = [m.get("latency_ms", 0) for m in metrics]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0
        
        # Efficacy
        successes = sum(1 for m in metrics if m.get("success", False))
        efficacy = sum(m.get("efficacy", 0) for m in metrics) / total if total > 0 else 0
        success_rate = successes / total if total > 0 else 0
        
        # Assurance
        avg_confidence = sum(m.get("confidence", 0) for m in metrics) / total if total > 0 else 0
        total_violations = sum(m.get("constraints_violated", 0) for m in metrics)
        total_policy = sum(m.get("policy_violations", 0) for m in metrics)
        
        # Reliability
        total_retries = sum(m.get("retries", 0) for m in metrics)
        circuit_breaker_trips = sum(1 for m in metrics if m.get("circuit_breaker_tripped", False))
        loop_detections = sum(1 for m in metrics if m.get("loop_detected", False))
        
        # Business outcomes
        total_revenue = sum(m.get("revenue_impact", 0) for m in metrics)
        avg_satisfaction = sum(m.get("customer_satisfaction", 0) for m in metrics) / total if total > 0 else 0
        retention_signals = sum(1 for m in metrics if m.get("retention_signal", False))
        
        # SLA compliance
        latency_sla = sum(1 for m in metrics if m.get("latency_ms", 0) <= SLA_LATENCY_MS) / total if total > 0 else 0
        cost_sla = sum(1 for m in metrics if m.get("cost", 0) <= SLA_COST_PER_QUERY) / total if total > 0 else 0
        efficacy_sla = sum(1 for m in metrics if m.get("efficacy", 0) >= SLA_EFFICACY) / total if total > 0 else 0
        confidence_sla = sum(1 for m in metrics if m.get("confidence", 0) >= SLA_CONFIDENCE) / total if total > 0 else 0
        
        return {
            "period_days": days,
            "agent": agent or "all",
            "total_entries": total,
            # Cost
            "total_cost": round(total_cost, 4),
            "avg_cost": round(avg_cost, 4),
            "cost_sla_compliance": round(cost_sla * 100, 1),
            # Latency
            "avg_latency_ms": round(avg_latency, 0),
            "p95_latency_ms": round(p95_latency, 0),
            "p99_latency_ms": round(p99_latency, 0),
            "latency_sla_compliance": round(latency_sla * 100, 1),
            # Efficacy
            "avg_efficacy": round(efficacy, 3),
            "success_rate": round(success_rate * 100, 1),
            "efficacy_sla_compliance": round(efficacy_sla * 100, 1),
            # Assurance
            "avg_confidence": round(avg_confidence, 3),
            "total_violations": total_violations,
            "total_policy_violations": total_policy,
            "confidence_sla_compliance": round(confidence_sla * 100, 1),
            # Reliability
            "total_retries": total_retries,
            "circuit_breaker_trips": circuit_breaker_trips,
            "loop_detections": loop_detections,
            # Business outcomes
            "total_revenue_impact": round(total_revenue, 2),
            "avg_customer_satisfaction": round(avg_satisfaction, 2),
            "retention_signals": retention_signals,
        }
    
    def get_dashboard(self) -> str:
        """Generate a text dashboard."""
        summary = self.get_summary()
        
        if "error" in summary:
            return f"❌ {summary['error']}"
        
        dashboard = f"""
╔══════════════════════════════════════════════════════════╗
║              CLEAR Framework Dashboard                   ║
║              Last {summary['period_days']} days                   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  💰 COST                                                 ║
║  Total: £{summary['total_cost']:.4f}    Avg: £{summary['avg_cost']:.4f}   SLA: {summary['cost_sla_compliance']}%      ║
║                                                          ║
║  ⏱️  LATENCY                                              ║
║  Avg: {summary['avg_latency_ms']:.0f}ms    P95: {summary['p95_latency_ms']:.0f}ms    P99: {summary['p99_latency_ms']:.0f}ms   SLA: {summary['latency_sla_compliance']}% ║
║                                                          ║
║  🎯 EFFICACY                                              ║
║  Avg: {summary['avg_efficacy']:.3f}    Success: {summary['success_rate']}%   SLA: {summary['efficacy_sla_compliance']}%      ║
║                                                          ║
║  🛡️  ASSURANCE                                            ║
║  Confidence: {summary['avg_confidence']:.3f}   Violations: {summary['total_violations']}   SLA: {summary['confidence_sla_compliance']}%  ║
║                                                          ║
║  🔧 RELIABILITY                                           ║
║  Retries: {summary['total_retries']}   Circuit Breaks: {summary['circuit_breaker_trips']}   Loops: {summary['loop_detections']}   ║
║                                                          ║
║  💼 BUSINESS OUTCOMES                                     ║
║  Revenue Impact: £{summary['total_revenue_impact']:.2f}                              ║
║  Customer Satisfaction: {summary['avg_customer_satisfaction']:.2f}                          ║
║  Retention Signals: {summary['retention_signals']}                                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
        return dashboard
    
    def export_csv(self, agent: str = None, days: int = 7) -> str:
        """Export metrics to CSV."""
        cutoff = datetime.now() - timedelta(days=days)
        metrics = []
        
        for i in range(days):
            date = cutoff + timedelta(days=i)
            daily_file = self.output_dir / f"clear-{date.strftime('%Y-%m-%d')}.jsonl"
            
            if daily_file.exists():
                with open(daily_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if agent and entry.get("agent") != agent:
                                continue
                            metrics.append(entry)
                        except json.JSONDecodeError:
                            continue
        
        if not metrics:
            return "No metrics to export"
        
        csv_file = self.output_dir / f"clear-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=metrics[0].keys())
            writer.writeheader()
            writer.writerows(metrics)
        
        return f"Exported {len(metrics)} entries to {csv_file}"


def main():
    parser = argparse.ArgumentParser(description="CLEAR Framework")
    parser.add_argument("--record", action="store_true", help="Record a metric")
    parser.add_argument("--summary", action="store_true", help="Show summary")
    parser.add_argument("--dashboard", action="store_true", help="Show dashboard")
    parser.add_argument("--export", choices=["csv"], help="Export metrics")
    parser.add_argument("--agent", help="Filter by agent name")
    parser.add_argument("--days", type=int, default=7, help="Number of days")
    parser.add_argument("--task-id", help="Task ID")
    parser.add_argument("--cost", type=float, default=0.0, help="Cost")
    parser.add_argument("--latency", type=float, default=0.0, help="Latency (ms)")
    parser.add_argument("--efficacy", type=float, default=0.0, help="Efficacy (0-1)")
    parser.add_argument("--success", action="store_true", help="Was it successful?")
    parser.add_argument("--confidence", type=float, default=0.0, help="Confidence (0-1)")
    parser.add_argument("--revenue", type=float, default=0.0, help="Revenue impact")
    parser.add_argument("--satisfaction", type=float, default=0.0, help="Customer satisfaction")
    
    args = parser.parse_args()
    framework = CLEARFramework()
    
    if args.record:
        metric = CLEARMetric(
            timestamp=datetime.now(datetime.timezone.utc).isoformat(),
            agent=args.agent or "unknown",
            task_id=args.task_id or "manual",
            cost=args.cost,
            latency_ms=args.latency,
            efficacy=args.efficacy,
            success=args.success,
            confidence=args.confidence,
            revenue_impact=args.revenue,
            customer_satisfaction=args.satisfaction,
        )
        framework.record(metric)
        print(f"✅ Recorded metric for {metric.agent}")
    
    elif args.summary:
        summary = framework.get_summary(agent=args.agent, days=args.days)
        print(json.dumps(summary, indent=2))
    
    elif args.dashboard:
        print(framework.get_dashboard())
    
    elif args.export:
        result = framework.export_csv(agent=args.agent, days=args.days)
        print(result)
    
    else:
        print(framework.get_dashboard())


if __name__ == "__main__":
    main()
