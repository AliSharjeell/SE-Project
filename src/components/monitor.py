"""
Monitoring System Component for AI-Driven Infrastructure Manager.

Provides real-time and historical metrics collection, aggregation, and analysis
for backend servers in the infrastructure.
"""

import json
import threading
import time
import random
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class ServerMetrics:
    """
    Represents metrics collected from a server at a specific point in time.

    Attributes:
        cpu_usage: CPU usage percentage (0-100)
        memory_usage: Memory usage percentage (0-100)
        response_time: Response time in milliseconds
        request_rate: Number of requests per second
        active_connections: Number of active connections
        timestamp: Unix timestamp when metrics were collected
    """
    cpu_usage: float
    memory_usage: float
    response_time: float
    request_rate: float
    active_connections: int
    timestamp: float

    def to_dict(self) -> dict:
        """Convert metrics to dictionary format."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert metrics to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> 'ServerMetrics':
        """Create ServerMetrics instance from dictionary."""
        return cls(**data)


class MonitoringSystem:
    """
    Thread-safe monitoring system for collecting and analyzing server metrics.

    Features:
        - Real-time metrics collection from simulated servers
        - Configurable history buffer with deque for efficient storage
        - Aggregated statistics calculation (avg, max, min, percentiles)
        - Thread-safe metric operations using locks
    """

    def __init__(self, history_size: int = 1000):
        """
        Initialize the monitoring system.

        Args:
            history_size: Maximum number of metrics entries to retain in history.
                         Older entries are automatically removed when limit is reached.
        """
        self._history_size = history_size
        self._metrics_history: deque[ServerMetrics] = deque(maxlen=history_size)
        self._lock = threading.Lock()
        self._is_collecting = False
        self._collection_thread: Optional[threading.Thread] = None

    @property
    def history_size(self) -> int:
        """Get the configured history buffer size."""
        return self._history_size

    @property
    def history_count(self) -> int:
        """Get the current number of metrics entries stored."""
        with self._lock:
            return len(self._metrics_history)

    def add_metric(self, metric: ServerMetrics) -> None:
        """
        Add a single metric entry to the history buffer.

        Args:
            metric: ServerMetrics instance to store
        """
        with self._lock:
            self._metrics_history.append(metric)

    def add_metric_raw(
        self,
        cpu_usage: float,
        memory_usage: float,
        response_time: float,
        request_rate: float,
        active_connections: int
    ) -> ServerMetrics:
        """
        Add a metric entry with raw values (convenience method).

        Args:
            cpu_usage: CPU usage percentage (0-100)
            memory_usage: Memory usage percentage (0-100)
            response_time: Response time in milliseconds
            request_rate: Requests per second
            active_connections: Number of active connections

        Returns:
            The created ServerMetrics instance
        """
        metric = ServerMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            response_time=response_time,
            request_rate=request_rate,
            active_connections=active_connections,
            timestamp=time.time()
        )
        self.add_metric(metric)
        return metric

    def get_latest(self) -> Optional[ServerMetrics]:
        """
        Get the most recent metrics entry.

        Returns:
            ServerMetrics instance or None if history is empty
        """
        with self._lock:
            if not self._metrics_history:
                return None
            return self._metrics_history[-1]

    def get_history(self, limit: Optional[int] = None) -> list[ServerMetrics]:
        """
        Get metrics history.

        Args:
            limit: Maximum number of entries to return (most recent first).
                  If None, returns all entries.

        Returns:
            List of ServerMetrics instances
        """
        with self._lock:
            history = list(self._metrics_history)
            if limit:
                return history[-limit:]
            return history

    def get_history_dicts(self, limit: Optional[int] = None) -> list[dict]:
        """
        Get metrics history as list of dictionaries.

        Args:
            limit: Maximum number of entries to return. If None, returns all.

        Returns:
            List of metric dictionaries
        """
        return [m.to_dict() for m in self.get_history(limit)]

    def get_history_json(self, limit: Optional[int] = None) -> str:
        """
        Get metrics history as JSON string.

        Args:
            limit: Maximum number of entries to return. If None, returns all.

        Returns:
            JSON string of metrics history
        """
        return json.dumps(self.get_history_dicts(limit), indent=2)

    def clear_history(self) -> None:
        """Clear all metrics history."""
        with self._lock:
            self._metrics_history.clear()

    def calculate_stats(self, field: str) -> dict:
        """
        Calculate aggregated statistics for a specific metric field.

        Args:
            field: Name of the field to calculate stats for.
                  Must be one of: cpu_usage, memory_usage, response_time,
                  request_rate, active_connections

        Returns:
            Dictionary with avg, max, min, and percentile values
        """
        with self._lock:
            if not self._metrics_history:
                return {
                    'avg': 0.0,
                    'max': 0.0,
                    'min': 0.0,
                    'p50': 0.0,
                    'p90': 0.0,
                    'p95': 0.0,
                    'p99': 0.0,
                    'count': 0
                }

            values = [getattr(m, field) for m in self._metrics_history]

        return self._compute_percentiles(values)

    def _compute_percentiles(self, values: list[float]) -> dict:
        """
        Compute percentiles and basic statistics for a list of values.

        Args:
            values: List of numeric values

        Returns:
            Dictionary with avg, max, min, and percentiles
        """
        if not values:
            return {
                'avg': 0.0, 'max': 0.0, 'min': 0.0,
                'p50': 0.0, 'p90': 0.0, 'p95': 0.0, 'p99': 0.0,
                'count': 0
            }

        sorted_values = sorted(values)
        n = len(sorted_values)

        def percentile(p: float) -> float:
            """Calculate percentile using linear interpolation."""
            if n == 1:
                return sorted_values[0]
            idx = (n - 1) * p
            lower = int(idx)
            upper = min(lower + 1, n - 1)
            return sorted_values[lower] + (idx - lower) * (sorted_values[upper] - sorted_values[lower])

        return {
            'avg': sum(values) / n,
            'max': max(values),
            'min': min(values),
            'p50': percentile(0.50),
            'p90': percentile(0.90),
            'p95': percentile(0.95),
            'p99': percentile(0.99),
            'count': n
        }

    def get_all_stats(self) -> dict:
        """
        Calculate statistics for all metric fields.

        Returns:
            Dictionary mapping field names to their statistics
        """
        fields = ['cpu_usage', 'memory_usage', 'response_time',
                  'request_rate', 'active_connections']
        return {field: self.calculate_stats(field) for field in fields}

    def get_stats_summary(self) -> dict:
        """
        Get a concise summary of all key statistics.

        Returns:
            Dictionary with key statistics for monitoring dashboard
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'samples_collected': self.history_count,
            'max_history_size': self._history_size,
            'latest': self.get_latest().to_dict() if self.get_latest() else None,
            'averages': {
                'cpu_usage': self.calculate_stats('cpu_usage')['avg'],
                'memory_usage': self.calculate_stats('memory_usage')['avg'],
                'response_time': self.calculate_stats('response_time')['avg'],
                'request_rate': self.calculate_stats('request_rate')['avg'],
                'active_connections': self.calculate_stats('active_connections')['avg']
            }
        }

    def start_collection(self, interval: float = 1.0) -> None:
        """
        Start automatic metrics collection from simulated servers.

        Args:
            interval: Time in seconds between collection attempts
        """
        if self._is_collecting:
            return

        self._is_collecting = True

        def collect_loop():
            while self._is_collecting:
                metric = self.generate_simulated_metric()
                self.add_metric(metric)
                time.sleep(interval)

        self._collection_thread = threading.Thread(target=collect_loop, daemon=True)
        self._collection_thread.start()

    def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        self._is_collecting = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2.0)
            self._collection_thread = None

    def generate_simulated_metric(self) -> ServerMetrics:
        """
        Generate simulated server metrics for testing purposes.

        Creates realistic-looking metrics with some variability:
        - CPU usage: 10-90% with occasional spikes
        - Memory usage: 30-80%
        - Response time: 10-500ms
        - Request rate: 10-1000 req/s
        - Active connections: 1-500

        Returns:
            ServerMetrics instance with simulated values
        """
        # Add some patterns/variability to make metrics more realistic
        base_time = time.time()
        cycle_factor = 0.1 * (1 + ((base_time % 60) / 60))  # Slow oscillation

        cpu_usage = max(5.0, min(95.0,
            30.0 + cycle_factor * 100 +
            random.gauss(0, 10) +
            (20 if random.random() < 0.1 else 0)  # Occasional spike
        ))

        memory_usage = max(20.0, min(90.0,
            45.0 + random.gauss(0, 8)
        ))

        response_time = max(5.0,
            50.0 + cycle_factor * 200 +
            random.gauss(0, 30) +
            (200 if random.random() < 0.05 else 0)  # Rare latency spike
        )

        request_rate = max(5.0,
            200.0 + random.gauss(0, 50) +
            (random.uniform(-100, 100) * ((base_time % 30) / 30))
        )

        active_connections = max(0, int(
            100 + random.gauss(0, 30) +
            (50 if random.random() < 0.2 else 0)
        ))

        return ServerMetrics(
            cpu_usage=round(cpu_usage, 2),
            memory_usage=round(memory_usage, 2),
            response_time=round(response_time, 2),
            request_rate=round(request_rate, 2),
            active_connections=active_connections,
            timestamp=base_time
        )

    def generate_batch(self, count: int) -> list[ServerMetrics]:
        """
        Generate a batch of simulated metrics at once.

        Args:
            count: Number of metrics to generate

        Returns:
            List of ServerMetrics instances
        """
        return [self.generate_simulated_metric() for _ in range(count)]


def create_monitor(history_size: int = 1000) -> MonitoringSystem:
    """
    Factory function to create a new MonitoringSystem instance.

    Args:
        history_size: Maximum history buffer size

    Returns:
        Configured MonitoringSystem instance
    """
    return MonitoringSystem(history_size=history_size)