"""
Real-time Metrics Collection for Sovereign Temple
Dashboard metrics, performance profiling, and system health
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil
import json


@dataclass
class MetricPoint:
    """A single metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates real-time metrics from all subsystems
    """
    
    def __init__(self, retention_seconds: int = 3600):
        self.retention_seconds = retention_seconds
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Performance profiling
        self.latency_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.throughput_counter: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Alert thresholds
        self.alert_thresholds: Dict[str, Dict[str, float]] = {
            "neural_prediction_latency_ms": {"warning": 100, "critical": 500},
            "memory_query_latency_ms": {"warning": 200, "critical": 1000},
            "system_cpu_percent": {"warning": 70, "critical": 90},
            "system_memory_percent": {"warning": 80, "critical": 95},
        }
        
        self.alert_handlers: List[Callable] = []
        self._collection_task: Optional[asyncio.Task] = None
    
    def add_alert_handler(self, handler: Callable[[str, str, float, float], None]):
        """Add an alert handler callback"""
        self.alert_handlers.append(handler)
    
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        point = MetricPoint(time.time(), value, labels or {})
        self.metrics[name].append(point)
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self.counters[key] += value
        self.record_metric(f"{name}_total", self.counters[key], labels)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self.gauges[key] = value
        self.record_metric(name, value, labels)
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a value to a histogram"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self.histograms[key].append(value)
        if len(self.histograms[key]) > 10000:
            self.histograms[key] = self.histograms[key][-5000:]
        self.record_metric(name, value, labels)
    
    def time_operation(self, name: str):
        """Context manager for timing operations"""
        return OperationTimer(self, name)
    
    async def start_collection(self, interval_seconds: float = 10.0):
        """Start background metrics collection"""
        self._collection_task = asyncio.create_task(
            self._collect_system_metrics(interval_seconds)
        )
    
    async def _collect_system_metrics(self, interval: float):
        """Collect system-level metrics"""
        while True:
            try:
                # CPU
                cpu_percent = psutil.cpu_percent(interval=1)
                self.set_gauge("system_cpu_percent", cpu_percent)
                self._check_alert("system_cpu_percent", cpu_percent)
                
                # Memory
                memory = psutil.virtual_memory()
                self.set_gauge("system_memory_percent", memory.percent)
                self.set_gauge("system_memory_available_gb", memory.available / (1024**3))
                self._check_alert("system_memory_percent", memory.percent)
                
                # Disk
                disk = psutil.disk_usage('/')
                self.set_gauge("system_disk_percent", disk.percent)
                
                # Network
                net_io = psutil.net_io_counters()
                self.set_gauge("system_network_bytes_sent", net_io.bytes_sent)
                self.set_gauge("system_network_bytes_recv", net_io.bytes_recv)
                
                # Process-specific
                process = psutil.Process()
                self.set_gauge("process_memory_mb", process.memory_info().rss / (1024**2))
                self.set_gauge("process_cpu_percent", process.cpu_percent())
                
            except Exception as e:
                self.record_metric("metrics_collection_error", 1, {"error": str(e)})
            
            await asyncio.sleep(interval)
    
    def _check_alert(self, metric_name: str, value: float):
        """Check if metric triggers an alert"""
        if metric_name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric_name]
        
        if value >= thresholds.get("critical", float('inf')):
            level = "critical"
        elif value >= thresholds.get("warning", float('inf')):
            level = "warning"
        else:
            return
        
        for handler in self.alert_handlers:
            try:
                handler(metric_name, level, value, thresholds.get(level))
            except Exception:
                pass
    
    def get_metric_summary(self, name: str, minutes: int = 5) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        cutoff = time.time() - (minutes * 60)
        points = [p for p in self.metrics[name] if p.timestamp >= cutoff]
        
        if not points:
            return {"count": 0}
        
        values = [p.value for p in points]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
            "last": values[-1]
        }
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])
    
    def get_histogram_stats(self, name: str) -> Dict[str, Any]:
        """Get histogram statistics"""
        key_prefix = f"{name}:"
        all_values = []
        
        for key, values in self.histograms.items():
            if key.startswith(key_prefix):
                all_values.extend(values)
        
        if not all_values:
            return {"count": 0}
        
        return {
            "count": len(all_values),
            "min": min(all_values),
            "max": max(all_values),
            "mean": sum(all_values) / len(all_values),
            "p50": self._percentile(all_values, 50),
            "p95": self._percentile(all_values, 95),
            "p99": self._percentile(all_values, 99),
            "buckets": self._calculate_buckets(all_values)
        }
    
    def _calculate_buckets(self, values: List[float], bucket_count: int = 10) -> Dict[str, int]:
        """Calculate histogram buckets"""
        if not values:
            return {}
        
        min_val, max_val = min(values), max(values)
        if min_val == max_val:
            return {f"{min_val:.2f}": len(values)}
        
        bucket_size = (max_val - min_val) / bucket_count
        buckets = defaultdict(int)
        
        for v in values:
            bucket_idx = int((v - min_val) / bucket_size)
            bucket_idx = min(bucket_idx, bucket_count - 1)
            bucket_label = f"{min_val + bucket_idx * bucket_size:.2f}-{min_val + (bucket_idx + 1) * bucket_size:.2f}"
            buckets[bucket_label] += 1
        
        return dict(buckets)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data for monitoring dashboard"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu": self.get_metric_summary("system_cpu_percent"),
                "memory": self.get_metric_summary("system_memory_percent"),
                "disk": self.get_metric_summary("system_disk_percent"),
            },
            "neural": {
                "prediction_latency": self.get_histogram_stats("neural_prediction_latency_ms"),
                "predictions_total": self.get_metric_summary("neural_predictions_total"),
            },
            "memory": {
                "query_latency": self.get_histogram_stats("memory_query_latency_ms"),
                "queries_total": self.get_metric_summary("memory_queries_total"),
            },
            "mcp": {
                "tool_calls": self.get_metric_summary("mcp_tool_calls_total"),
                "tool_latency": self.get_histogram_stats("mcp_tool_latency_ms"),
            },
            "alerts": self._get_recent_alerts(),
            "gauges": dict(self.gauges)
        }
    
    def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alert history (placeholder)"""
        return []
    
    async def stop(self):
        """Stop metrics collection"""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass


class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, name: str):
        self.collector = collector
        self.name = name
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000  # ms
        self.collector.record_histogram(f"{self.name}_latency_ms", duration)
        
        if exc_type is not None:
            self.collector.increment_counter(f"{self.name}_errors_total")
        else:
            self.collector.increment_counter(f"{self.name}_success_total")
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000  # ms
        self.collector.record_histogram(f"{self.name}_latency_ms", duration)
        
        if exc_type is not None:
            self.collector.increment_counter(f"{self.name}_errors_total")
        else:
            self.collector.increment_counter(f"{self.name}_success_total")
