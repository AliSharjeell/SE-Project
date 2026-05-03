import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    AI_POWERED = "ai_powered"
    OFF = "off"


@dataclass
class Server:
    """Represents a backend server in the load balancer pool."""
    url: str
    server_id: str
    healthy: bool = True
    active_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_selected: float = field(default_factory=time.time)
    health_score: float = 1.0  # Used by AI-powered strategy (0.0 to 1.0)


@dataclass
class StrategyStats:
    """Tracks usage statistics for each routing strategy."""
    round_robin: int = 0
    least_connections: int = 0
    ai_powered: int = 0
    off: int = 0


class LoadBalancer:
    """
    Thread-safe load balancer with multiple routing strategies.

    Strategies:
    - round_robin: Sequential rotation through available servers
    - least_connections: Routes to server with fewest active connections
    - ai_powered: Weighted selection based on health scores from ML service
    """

    def __init__(self):
        self._servers: Dict[str, Server] = {}
        self._server_order: List[str] = []  # For round-robin ordering
        self._last_round_robin_index: int = -1
        self._lock = threading.RLock()
        self._stats = StrategyStats()
        self._total_requests: int = 0

    def add_server(self, url: str, server_id: Optional[str] = None) -> bool:
        """
        Add a new server to the load balancer pool.
        Returns False if server already exists.
        """
        with self._lock:
            if server_id is None:
                server_id = url

            if server_id in self._servers:
                return False

            server = Server(url=url, server_id=server_id)
            self._servers[server_id] = server
            self._server_order.append(server_id)
            return True

    def remove_server(self, server_id: str) -> bool:
        """Remove a server from the load balancer pool."""
        with self._lock:
            if server_id not in self._servers:
                return False

            del self._servers[server_id]
            self._server_order.remove(server_id)

            if self._last_round_robin_index >= len(self._server_order):
                self._last_round_robin_index = 0

            return True

    def get_servers(self) -> List[str]:
        """Get list of healthy server URLs."""
        with self._lock:
            return [
                server.url for server in self._servers.values()
                if server.healthy
            ]

    def get_server_by_id(self, server_id: str) -> Optional[Server]:
        """Get server object by ID."""
        with self._lock:
            return self._servers.get(server_id)

    def get_server_info(self) -> List[Dict[str, Any]]:
        """Get detailed information about all servers."""
        with self._lock:
            return [
                {
                    "server_id": server.server_id,
                    "host": server.url.split("://")[1].split(":")[0] if "://" in server.url else server.url,
                    "port": int(server.url.split(":")[-1]) if ":" in server.url else 80,
                    "url": server.url,
                    "healthy": server.healthy,
                    "active_connections": server.active_connections,
                }
                for server in self._servers.values()
            ]

    def select_server(self, strategy: RoutingStrategy) -> Optional[str]:
        """
        Select a server based on the specified routing strategy.
        """
        with self._lock:
            # Use _server_order to maintain deterministic ordering
            healthy_servers = [
                self._servers[sid] for sid in self._server_order
                if sid in self._servers and self._servers[sid].healthy
            ]
            if not healthy_servers:
                return None

            if strategy == RoutingStrategy.ROUND_ROBIN:
                return self._select_round_robin(healthy_servers)
            elif strategy == RoutingStrategy.LEAST_CONNECTIONS:
                return self._select_least_connections(healthy_servers)
            elif strategy == RoutingStrategy.AI_POWERED:
                return self._select_ai_powered(healthy_servers)
            elif strategy == RoutingStrategy.OFF:
                return self._select_off(healthy_servers)

            return None

    def _select_round_robin(self, healthy_servers: List[Server]) -> str:
        """Round Robin: Sequential rotation through available servers."""
        self._stats.round_robin += 1
        self._total_requests += 1

        self._last_round_robin_index = (self._last_round_robin_index + 1) % len(healthy_servers)
        selected = healthy_servers[self._last_round_robin_index]
        selected.last_selected = time.time()
        return selected.url

    def _select_least_connections(self, healthy_servers: List[Server]) -> str:
        """Least Connections: Route to server with fewest active connections."""
        self._stats.least_connections += 1
        self._total_requests += 1

        selected = min(healthy_servers, key=lambda s: s.active_connections)
        selected.last_selected = time.time()
        return selected.url

    def _select_ai_powered(self, healthy_servers: List[Server]) -> str:
        """
        AI-Powered: Weighted selection based on health scores.
        Higher health score = higher probability of selection.
        """
        self._stats.ai_powered += 1
        self._total_requests += 1

        # Normalize health scores for weighted selection
        total_score = sum(s.health_score for s in healthy_servers)
        if total_score <= 0:
            # Fallback to round-robin if all scores are zero
            return self._select_round_robin(healthy_servers)

        # Simple weighted random selection based on health scores
        import random
        rand_val = random.uniform(0, total_score)
        cumulative = 0.0

        for server in healthy_servers:
            cumulative += server.health_score
            if rand_val <= cumulative:
                server.last_selected = time.time()
                return server.url

        # Fallback to first server
        healthy_servers[0].last_selected = time.time()
        return healthy_servers[0].url

    def _select_off(self, healthy_servers: List[Server]) -> str:
        """
        Off: No load balancing - route ALL traffic to the first healthy server.
        This effectively disables distribution and sends every request to a
        single target (backend-1 unless it is unhealthy).
        """
        self._stats.off += 1
        self._total_requests += 1

        selected = healthy_servers[0]
        selected.last_selected = time.time()
        return selected.url

    def increment_connections(self, url: str) -> None:
        """Increment active connection count for a server."""
        with self._lock:
            for server in self._servers.values():
                if server.url == url:
                    server.active_connections += 1
                    break

    def decrement_connections(self, url: str) -> None:
        """Decrement active connection count for a server."""
        with self._lock:
            for server in self._servers.values():
                if server.url == url:
                    server.active_connections = max(0, server.active_connections - 1)
                    break

    def mark_unhealthy(self, url: str) -> None:
        """Mark a server as unhealthy."""
        with self._lock:
            for server in self._servers.values():
                if server.url == url:
                    server.healthy = False
                    server.failed_requests += 1
                    break

    def mark_healthy(self, url: str) -> None:
        """Mark a server as healthy."""
        with self._lock:
            for server in self._servers.values():
                if server.url == url:
                    server.healthy = True
                    break

    def update_health_score(self, url: str, score: float) -> None:
        """
        Update the health score for AI-powered routing.
        Score should be between 0.0 and 1.0.
        """
        with self._lock:
            for server in self._servers.values():
                if server.url == url:
                    server.health_score = max(0.0, min(1.0, score))
                    break

    def record_request(self, url: str, status_code: int) -> None:
        """Record request statistics for a server."""
        with self._lock:
            for server in self._servers.values():
                if server.url == url:
                    server.total_requests += 1
                    if 200 <= status_code < 400:
                        server.successful_requests += 1
                    else:
                        server.failed_requests += 1
                    break

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive routing statistics."""
        with self._lock:
            return {
                "strategy_distribution": {
                    "round_robin": self._stats.round_robin,
                    "least_connections": self._stats.least_connections,
                    "ai_powered": self._stats.ai_powered,
                    "off": self._stats.off,
                },
                "total_requests": self._total_requests,
                "servers": {
                    server_id: {
                        "url": server.url,
                        "healthy": server.healthy,
                        "active_connections": server.active_connections,
                        "total_requests": server.total_requests,
                        "successful_requests": server.successful_requests,
                        "failed_requests": server.failed_requests,
                        "health_score": server.health_score,
                        "last_selected": server.last_selected,
                    }
                    for server_id, server in self._servers.items()
                },
            }