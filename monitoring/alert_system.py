"""
Alert System for Sovereign Temple
Real-time alerting with multiple notification channels
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(Enum):
    """Available alert channels"""
    CONSOLE = "console"
    FILE = "file"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    source: str
    title: str
    message: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """
    Manages alert generation, deduplication, and notification
    """
    
    def __init__(self, max_alerts: int = 1000):
        self.max_alerts = max_alerts
        self.alerts: List[Alert] = []
        self.alert_handlers: Dict[AlertChannel, List[Callable]] = {
            channel: [] for channel in AlertChannel
        }
        
        # Deduplication window (minutes)
        self.dedup_window = 15
        self.recent_alerts: Dict[str, datetime] = {}
        
        # Alert rules
        self.rules: List[Dict[str, Any]] = []
        
        # Rate limiting
        self.rate_limits: Dict[str, int] = {
            "info": 100,
            "warning": 50,
            "critical": 20,
            "emergency": 10
        }
        self.alert_counts: Dict[str, List[datetime]] = {
            severity.value: [] for severity in AlertSeverity
        }
    
    def add_handler(self, channel: AlertChannel, handler: Callable[[Alert], None]):
        """Add an alert handler for a channel"""
        self.alert_handlers[channel].append(handler)
    
    def add_rule(self, 
                 name: str,
                 condition: Callable[[Dict[str, Any]], bool],
                 severity: AlertSeverity,
                 title_template: str,
                 message_template: str,
                 channels: List[AlertChannel] = None):
        """Add an alert rule"""
        self.rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "title_template": title_template,
            "message_template": message_template,
            "channels": channels or [AlertChannel.CONSOLE]
        })
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        return f"alt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.alerts):06d}"
    
    def _check_rate_limit(self, severity: AlertSeverity) -> bool:
        """Check if alert rate limit is exceeded"""
        now = datetime.now()
        window_start = now - timedelta(minutes=1)
        
        # Clean old entries
        self.alert_counts[severity.value] = [
            t for t in self.alert_counts[severity.value] if t > window_start
        ]
        
        # Check limit
        if len(self.alert_counts[severity.value]) >= self.rate_limits[severity.value]:
            return False
        
        self.alert_counts[severity.value].append(now)
        return True
    
    def _check_dedup(self, alert_key: str) -> bool:
        """Check if similar alert was recently fired"""
        now = datetime.now()
        
        if alert_key in self.recent_alerts:
            last_fired = self.recent_alerts[alert_key]
            if now - last_fired < timedelta(minutes=self.dedup_window):
                return True
        
        self.recent_alerts[alert_key] = now
        return False
    
    async def fire_alert(self,
                        severity: AlertSeverity,
                        source: str,
                        title: str,
                        message: str,
                        metric_name: Optional[str] = None,
                        metric_value: Optional[float] = None,
                        threshold: Optional[float] = None,
                        metadata: Optional[Dict[str, Any]] = None,
                        channels: Optional[List[AlertChannel]] = None) -> Optional[Alert]:
        """Fire an alert"""
        
        # Check rate limit
        if not self._check_rate_limit(severity):
            return None
        
        # Check deduplication
        alert_key = f"{source}:{title}:{severity.value}"
        if self._check_dedup(alert_key):
            return None
        
        # Create alert
        alert = Alert(
            id=self._generate_alert_id(),
            timestamp=datetime.now(),
            severity=severity,
            source=source,
            title=title,
            message=message,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
            metadata=metadata or {}
        )
        
        # Store alert
        self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Send to channels
        target_channels = channels or [AlertChannel.CONSOLE]
        for channel in target_channels:
            for handler in self.alert_handlers[channel]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert)
                    else:
                        handler(alert)
                except Exception as e:
                    print(f"Alert handler error: {e}")
        
        return alert
    
    async def check_rules(self, metrics: Dict[str, Any]):
        """Evaluate all alert rules against current metrics"""
        for rule in self.rules:
            try:
                if rule["condition"](metrics):
                    await self.fire_alert(
                        severity=rule["severity"],
                        source=rule["name"],
                        title=rule["title_template"],
                        message=rule["message_template"],
                        channels=rule["channels"]
                    )
            except Exception as e:
                print(f"Rule evaluation error: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return True
        return False
    
    def get_active_alerts(self, 
                         min_severity: Optional[AlertSeverity] = None,
                         source: Optional[str] = None) -> List[Alert]:
        """Get active (unresolved) alerts"""
        active = [a for a in self.alerts if not a.resolved]
        
        if min_severity:
            severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, 
                           AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]
            min_idx = severity_order.index(min_severity)
            allowed = severity_order[min_idx:]
            active = [a for a in active if a.severity in allowed]
        
        if source:
            active = [a for a in active if a.source == source]
        
        return sorted(active, key=lambda a: (a.severity.value, a.timestamp), reverse=True)
    
    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [a for a in self.alerts if a.timestamp > cutoff]
        
        by_severity = {}
        by_source = {}
        
        for alert in recent:
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
            by_source[alert.source] = by_source.get(alert.source, 0) + 1
        
        return {
            "total": len(recent),
            "active": len([a for a in recent if not a.resolved]),
            "acknowledged": len([a for a in recent if a.acknowledged]),
            "by_severity": by_severity,
            "by_source": by_source,
            "recent": [{
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "severity": a.severity.value,
                "source": a.source,
                "title": a.title,
                "acknowledged": a.acknowledged,
                "resolved": a.resolved
            } for a in recent[-10:]]
        }
    
    def setup_default_rules(self):
        """Setup default alert rules"""
        
        # High CPU usage
        self.add_rule(
            name="high_cpu_usage",
            condition=lambda m: m.get("system_cpu_percent", 0) > 80,
            severity=AlertSeverity.WARNING,
            title_template="High CPU Usage",
            message_template="System CPU usage is above 80%",
            channels=[AlertChannel.CONSOLE]
        )
        
        # Critical CPU usage
        self.add_rule(
            name="critical_cpu_usage",
            condition=lambda m: m.get("system_cpu_percent", 0) > 95,
            severity=AlertSeverity.CRITICAL,
            title_template="Critical CPU Usage",
            message_template="System CPU usage is above 95%",
            channels=[AlertChannel.CONSOLE]
        )
        
        # High memory usage
        self.add_rule(
            name="high_memory_usage",
            condition=lambda m: m.get("system_memory_percent", 0) > 85,
            severity=AlertSeverity.WARNING,
            title_template="High Memory Usage",
            message_template="System memory usage is above 85%",
            channels=[AlertChannel.CONSOLE]
        )
        
        # Neural model latency
        self.add_rule(
            name="neural_latency_high",
            condition=lambda m: m.get("neural_latency_p95", 0) > 500,
            severity=AlertSeverity.WARNING,
            title_template="High Neural Prediction Latency",
            message_template="Neural prediction P95 latency exceeds 500ms",
            channels=[AlertChannel.CONSOLE]
        )
        
        # Memory query latency
        self.add_rule(
            name="memory_latency_high",
            condition=lambda m: m.get("memory_latency_p95", 0) > 1000,
            severity=AlertSeverity.WARNING,
            title_template="High Memory Query Latency",
            message_template="Memory query P95 latency exceeds 1000ms",
            channels=[AlertChannel.CONSOLE]
        )
        
        # Threat detected
        self.add_rule(
            name="security_threat",
            condition=lambda m: m.get("threats_detected", 0) > 0,
            severity=AlertSeverity.CRITICAL,
            title_template="Security Threat Detected",
            message_template="A security threat was detected in user input",
            channels=[AlertChannel.CONSOLE]
        )


# Default alert handlers

def console_alert_handler(alert: Alert):
    """Print alert to console"""
    severity_colors = {
        AlertSeverity.INFO: "\033[94m",      # Blue
        AlertSeverity.WARNING: "\033[93m",   # Yellow
        AlertSeverity.CRITICAL: "\033[91m",  # Red
        AlertSeverity.EMERGENCY: "\033[95m"  # Magenta
    }
    reset = "\033[0m"
    
    color = severity_colors.get(alert.severity, "")
    print(f"{color}[{alert.severity.value.upper()}] {alert.title}{reset}")
    print(f"  Source: {alert.source}")
    print(f"  Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Message: {alert.message}")
    if alert.metric_name:
        print(f"  Metric: {alert.metric_name} = {alert.metric_value:.2f} (threshold: {alert.threshold})")
    print()


async def file_alert_handler(alert: Alert, log_file: str = "logs/alerts.log"):
    """Write alert to file"""
    import os
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with open(log_file, "a") as f:
        f.write(json.dumps({
            "id": alert.id,
            "timestamp": alert.timestamp.isoformat(),
            "severity": alert.severity.value,
            "source": alert.source,
            "title": alert.title,
            "message": alert.message,
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
            "metadata": alert.metadata
        }) + "\n")
