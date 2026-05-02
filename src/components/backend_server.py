"""
Backend Server Component for AI-Driven Infrastructure Manager.

Simulates a backend application server with configurable response times,
CPU usage simulation, connection tracking, and health monitoring.
"""

import json
import random
import threading
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class Request:
    """
    Represents a simulated request to the backend server.

    Attributes:
        request_id: Unique identifier for the request
        timestamp: Unix timestamp when request was created
        payload_size: Size of request payload in bytes
        endpoint: The API endpoint being accessed
    """
    request_id: str
    timestamp: float
    payload_size: int
    endpoint: str = "/api/default"


@dataclass
class Response:
    """
    Represents the server's response to a request.

    Attributes:
        request_id: ID matching the original request
        status_code: HTTP status code (200, 500, etc.)
        response_time: Time taken to process in milliseconds
        data: Response payload data
        timestamp: Unix timestamp when response was generated
    """
    request_id: str
    status_code: int
    response_time: float
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert response to dictionary format."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert response to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ServerMetrics:
    """
    Represents current server metrics at a point in time.

    Attributes:
        cpu_usage: CPU usage percentage (0-100)
        memory_usage: Memory usage percentage (0-100)
        response_time: Average response time in milliseconds
        active_connections: Number of currently active connections
        request_count: Total requests processed
        healthy: Server health status
        timestamp: Unix timestamp when metrics were collected
    """
    cpu_usage: float
    memory_usage: float
    response_time: float
    active_connections: int
    request_count: int
    healthy: bool
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


class BackendServer:
    """
    Simulates a backend application server with realistic behavior.

    Features:
        - Configurable base response time with load-based scaling
        - CPU usage simulation that increases with connections
        - Thread-safe operations using locks
        - Request ID tracking for debugging
        - Health status endpoint with configurable thresholds

    The server simulates Flask/FastAPI-like behavior with:
        - Request processing with configurable delays
        - Metrics collection and reporting
        - Load factor adjustment for stress testing
        - Connection and request counting
    """

    def __init__(
        self,
        name: str = "backend-server-1",
        base_response_time: float = 50.0,
        base_cpu_usage: float = 10.0,
        base_memory_usage: float = 30.0,
        max_connections: int = 1000
    ) -> None:
        """
        Initialize the BackendServer.

        Args:
            name: Server identifier name
            base_response_time: Base response time in milliseconds
            base_cpu_usage: Base CPU usage percentage
            base_memory_usage: Base memory usage percentage
            max_connections: Maximum concurrent connections allowed
        """
        self.name = name
        self.base_response_time = base_response_time
        self.base_cpu_usage = base_cpu_usage
        self.base_memory_usage = base_memory_usage
        self.max_connections = max_connections

        # Internal state
        self._lock = threading.RLock()
        self._request_count = 0
        self._active_connections = 0
        self._response_times: list[float] = []
        self._load_factor = 1.0
        self._is_healthy = True
        self._total_response_time = 0.0
        self._start_time = time.time()
        self._request_ids: set[str] = set()

    @property
    def request_count(self) -> int:
        """Get total number of requests processed (thread-safe)."""
        with self._lock:
            return self._request_count

    @property
    def active_connections(self) -> int:
        """Get current active connections (thread-safe)."""
        with self._lock:
            return self._active_connections

    @property
    def load_factor(self) -> float:
        """Get current load factor (thread-safe)."""
        with self._lock:
            return self._load_factor

    @property
    def is_healthy(self) -> bool:
        """Get server health status (thread-safe)."""
        with self._lock:
            return self._is_healthy

    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return f"req-{uuid4()}"

    def _simulate_processing_delay(self, load_factor: float) -> float:
        """
        Simulate realistic processing delay based on load.

        Args:
            load_factor: Current load multiplier

        Returns:
            Processing delay in milliseconds
        """
        base_delay = self.base_response_time * load_factor

        # Add realistic variation (±20%)
        variation = random.uniform(0.8, 1.2)

        # Add occasional spikes under high load
        if load_factor > 2.0 and random.random() < 0.1:
            variation *= random.uniform(1.5, 2.5)

        return base_delay * variation

    def _calculate_cpu_usage(self, active_connections: int, load_factor: float) -> float:
        """
        Calculate CPU usage based on connections and load.

        Args:
            active_connections: Number of active connections
            load_factor: Current load multiplier

        Returns:
            CPU usage percentage (0-100)
        """
        # Base usage + scaled by connections (up to 40% from connections)
        connection_factor = min(active_connections / self.max_connections, 1.0) * 40.0

        # Load factor adds additional pressure (up to 30% more)
        load_factor_addition = min((load_factor - 1.0) * 15.0, 30.0) if load_factor > 1.0 else 0.0

        # Random variation ±5%
        variation = random.gauss(0, 5)

        cpu = self.base_cpu_usage + connection_factor + load_factor_addition + variation

        return max(0.0, min(100.0, cpu))

    def _calculate_memory_usage(self, active_connections: int, load_factor: float) -> float:
        """
        Calculate memory usage based on connections and load.

        Args:
            active_connections: Number of active connections
            load_factor: Current load multiplier

        Returns:
            Memory usage percentage (0-100)
        """
        # Base usage + scaled by connections
        connection_factor = min(active_connections / self.max_connections, 1.0) * 30.0

        # Load factor adds pressure
        load_factor_addition = min((load_factor - 1.0) * 10.0, 20.0) if load_factor > 1.0 else 0.0

        # Small random variation
        variation = random.gauss(0, 3)

        memory = self.base_memory_usage + connection_factor + load_factor_addition + variation

        return max(0.0, min(100.0, memory))

    def _calculate_response_time(self, load_factor: float, active_connections: int) -> float:
        """
        Calculate response time based on load and connections.

        Args:
            load_factor: Current load multiplier
            active_connections: Number of active connections

        Returns:
            Response time in milliseconds
        """
        base_time = self._simulate_processing_delay(load_factor)

        # Connection pressure: more connections = slower response
        connection_pressure = min(active_connections / self.max_connections, 1.0) * 50.0

        return base_time + connection_pressure

    def _update_health_status(self, response_time: float, active_connections: int) -> bool:
        """
        Determine server health based on current metrics.

        Args:
            response_time: Current response time in milliseconds
            response_time_threshold: Threshold for response time health check

        Returns:
            True if server is healthy, False otherwise
        """
        # Unhealthy if response time exceeds 500ms
        if response_time > 500.0:
            return False

        # Unhealthy if over 90% capacity
        if active_connections > self.max_connections * 0.9:
            return False

        # 95% healthy under normal conditions
        return random.random() < 0.95

    def handle_request(self, request: Optional[Request] = None) -> Response:
        """
        Process a request and return a response.

        Simulates request processing with:
        - Configurable response delay based on load
        - CPU/memory pressure simulation
        - Connection tracking
        - Response time measurement

        Args:
            request: Request object to process. If None, generates a default request.

        Returns:
            Response object with status, timing, and data
        """
        # Generate request if not provided
        if request is None:
            request = Request(
                request_id=self._generate_request_id(),
                timestamp=time.time(),
                payload_size=random.randint(1024, 102400),
                endpoint="/api/default"
            )

        with self._lock:
            # Track request
            self._request_count += 1
            self._active_connections += 1
            self._request_ids.add(request.request_id)

            # Calculate metrics before processing
            response_time = self._calculate_response_time(
                self._load_factor,
                self._active_connections
            )

            # Simulate processing delay
            processing_delay = response_time / 1000.0  # Convert to seconds
            time.sleep(processing_delay)

            # Update state
            self._active_connections -= 1
            self._request_ids.discard(request.request_id)
            self._response_times.append(response_time)
            self._total_response_time += response_time

            # Keep only last 1000 response times
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-1000:]

            # Determine status
            if response_time > 500.0:
                status_code = 503  # Service Unavailable
            elif response_time > 200.0:
                status_code = 200  # Still OK but slow
            else:
                status_code = 200  # OK

            # Update health status
            self._is_healthy = self._update_health_status(response_time, self._active_connections)

            return Response(
                request_id=request.request_id,
                status_code=status_code,
                response_time=round(response_time, 2),
                data={
                    "message": f"Processed by {self.name}",
                    "endpoint": request.endpoint,
                    "processed_at": datetime.now().isoformat()
                },
                timestamp=time.time()
            )

    def health_check(self) -> dict:
        """
        Check server health status.

        Returns:
            Dictionary with health status and related metrics
        """
        with self._lock:
            return {
                "server": self.name,
                "healthy": self._is_healthy,
                "active_connections": self._active_connections,
                "request_count": self._request_count,
                "cpu_usage": round(self._calculate_cpu_usage(
                    self._active_connections,
                    self._load_factor
                ), 2),
                "memory_usage": round(self._calculate_memory_usage(
                    self._active_connections,
                    self._load_factor
                ), 2),
                "uptime_seconds": round(time.time() - self._start_time, 2)
            }

    def get_metrics(self) -> ServerMetrics:
        """
        Get current server metrics (thread-safe).

        Returns:
            ServerMetrics instance with current state
        """
        with self._lock:
            # Calculate average response time
            avg_response_time = (
                self._total_response_time / self._request_count
                if self._request_count > 0
                else self.base_response_time
            )

            return ServerMetrics(
                cpu_usage=round(self._calculate_cpu_usage(
                    self._active_connections,
                    self._load_factor
                ), 2),
                memory_usage=round(self._calculate_memory_usage(
                    self._active_connections,
                    self._load_factor
                ), 2),
                response_time=round(avg_response_time, 2),
                active_connections=self._active_connections,
                request_count=self._request_count,
                healthy=self._is_healthy,
                timestamp=time.time()
            )

    def set_load_factor(self, factor: float) -> None:
        """
        Set the load factor to simulate different load conditions.

        Args:
            factor: Load multiplier (1.0 = normal, 2.0 = double load, etc.)
        """
        with self._lock:
            self._load_factor = max(0.1, min(10.0, factor))

    def reset(self) -> None:
        """
        Reset server state to initial values (thread-safe).

        Resets:
            - Request count to 0
            - Active connections to 0
            - Response times history
            - Total response time
            - Request IDs tracking
            - Health status to True
            - Load factor to 1.0
        """
        with self._lock:
            self._request_count = 0
            self._active_connections = 0
            self._response_times.clear()
            self._total_response_time = 0.0
            self._request_ids.clear()
            self._is_healthy = True
            self._load_factor = 1.0
            self._start_time = time.time()

    def get_uptime(self) -> float:
        """
        Get server uptime in seconds.

        Returns:
            Uptime in seconds since server creation or last reset
        """
        with self._lock:
            return time.time() - self._start_time

    def __repr__(self) -> str:
        """String representation of the server."""
        with self._lock:
            return (
                f"BackendServer(name={self.name!r}, "
                f"requests={self._request_count}, "
                f"connections={self._active_connections}, "
                f"load_factor={self._load_factor}, "
                f"healthy={self._is_healthy})"
            )


def create_backend_server(
    name: str = "backend-server-1",
    base_response_time: float = 50.0,
    base_cpu_usage: float = 10.0,
    base_memory_usage: float = 30.0
) -> BackendServer:
    """
    Factory function to create a configured BackendServer instance.

    Args:
        name: Server identifier name
        base_response_time: Base response time in milliseconds
        base_cpu_usage: Base CPU usage percentage
        base_memory_usage: Base memory usage percentage

    Returns:
        Configured BackendServer instance
    """
    return BackendServer(
        name=name,
        base_response_time=base_response_time,
        base_cpu_usage=base_cpu_usage,
        base_memory_usage=base_memory_usage
    )
