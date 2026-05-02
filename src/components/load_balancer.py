"""
Load Balancer Component for AI-Driven Infrastructure Manager.

This module provides load balancing strategies for distributing incoming
requests across multiple backend servers with support for traditional
and AI-powered routing algorithms.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import threading
import random
from datetime import datetime


class LoadBalancerStrategy(Enum):
    """Enumeration of available load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    AI_POWERED = "ai_powered"


@dataclass
class BackendServer:
    """
    Represents a backend server in the load balancer pool.

    Attributes:
        id: Unique identifier for the server.
        host: Server hostname or IP address.
        port: Server port number.
        cpu_usage: Current CPU usage percentage (0-100).
        active_connections: Number of currently active connections.
        avg_response_time: Average response time in milliseconds.
    """
    id: str
    host: str
    port: int
    cpu_usage: float = 0.0
    active_connections: int = 0
    avg_response_time: float = 0.0


@dataclass
class RoutingEntry:
    """Records a single routing decision for historical analysis."""
    timestamp: datetime
    server_id: str
    strategy: LoadBalancerStrategy
    prediction_score: Optional[float] = None


class LoadBalancer:
    """
    Load balancer supporting multiple routing strategies including AI-powered predictions.

    Provides thread-safe operations for managing backend servers and routing
    requests according to the selected strategy.

    Attributes:
        max_history: Maximum number of routing entries to retain.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize the load balancer.

        Args:
            max_history: Maximum number of routing history entries to retain.
        """
        self._servers: Dict[str, BackendServer] = {}
        self._lock = threading.RLock()
        self._current_index: int = 0
        self._routing_history: List[RoutingEntry] = []
        self._max_history = max_history

    def add_server(self, server_info: BackendServer) -> bool:
        """
        Add a new backend server to the load balancer pool.

        Args:
            server_info: BackendServer instance containing server configuration.

        Returns:
            True if server was added successfully, False if server_id already exists.

        Thread-safe operation.
        """
        with self._lock:
            if server_info.id in self._servers:
                return False
            self._servers[server_info.id] = server_info
            return True

    def remove_server(self, server_id: str) -> bool:
        """
        Remove a backend server from the load balancer pool.

        Args:
            server_id: Unique identifier of the server to remove.

        Returns:
            True if server was removed, False if server_id not found.

        Thread-safe operation.
        """
        with self._lock:
            if server_id not in self._servers:
                return False
            del self._servers[server_id]
            # Reset index if we removed the server at current position
            if self._current_index >= len(self._servers):
                self._current_index = 0
            return True

    def get_server(self, server_id: str) -> Optional[BackendServer]:
        """
        Retrieve a backend server by ID.

        Args:
            server_id: Unique identifier of the server.

        Returns:
            BackendServer instance if found, None otherwise.
        """
        with self._lock:
            return self._servers.get(server_id)

    def get_all_servers(self) -> List[BackendServer]:
        """
        Get all registered backend servers.

        Returns:
            List of all BackendServer instances.
        """
        with self._lock:
            return list(self._servers.values())

    def _get_next_round_robin_index(self) -> int:
        """
        Get the next server index using round-robin algorithm.

        Returns:
            Index of the next server in round-robin order.
        """
        if not self._servers:
            raise ValueError("No servers available for routing")

        index = self._current_index
        self._current_index = (self._current_index + 1) % len(self._servers)
        return index

    def _select_least_connections_server(self) -> BackendServer:
        """
        Select server with the least active connections.

        Returns:
            BackendServer with minimum active connections.

        Raises:
            ValueError: If no servers are available.
        """
        if not self._servers:
            raise ValueError("No servers available for routing")

        # Find servers with minimum connections
        min_connections = min(s.active_connections for s in self._servers.values())
        candidates = [s for s in self._servers.values() if s.active_connections == min_connections]

        # If tie, use round-robin to break
        return random.choice(candidates)

    def _select_ai_powered_server(self, prediction_scores: Optional[Dict[str, float]]) -> BackendServer:
        """
        Select server using AI-powered weighted routing.

        Args:
            prediction_scores: Optional dict mapping server_id to health score (0-1).
                              Higher scores indicate better server health.

        Returns:
            BackendServer selected based on weighted probability.

        Raises:
            ValueError: If no servers are available.
        """
        if not self._servers:
            raise ValueError("No servers available for routing")

        # Fall back to round-robin if no prediction scores
        if prediction_scores is None:
            server_ids = list(self._servers.keys())
            selected_id = server_ids[self._get_next_round_robin_index()]
            return self._servers[selected_id]

        # Filter scores to only include available servers
        available_scores = {
            server_id: prediction_scores.get(server_id, 0.0)
            for server_id in self._servers.keys()
        }

        # Calculate cumulative weights for weighted random selection
        weights = list(available_scores.values())
        total_weight = sum(weights)

        # If all scores are zero or negative, fall back to round-robin
        if total_weight <= 0:
            server_ids = list(self._servers.keys())
            selected_id = server_ids[self._get_next_round_robin_index()]
            return self._servers[selected_id]

        # Weighted random selection
        rand_value = random.random() * total_weight
        cumulative = 0.0
        for server_id, score in available_scores.items():
            cumulative += score
            if rand_value <= cumulative:
                return self._servers[server_id]

        # Fallback (should not reach here normally)
        return random.choice(list(self._servers.values()))

    def route_request(
        self,
        strategy: LoadBalancerStrategy,
        prediction_scores: Optional[Dict[str, float]] = None
    ) -> BackendServer:
        """
        Route a request to a backend server using the specified strategy.

        Args:
            strategy: LoadBalancerStrategy to use for routing.
            prediction_scores: Optional dict mapping server_id to health score (0-1).
                             Required for AI_POWERED strategy.

        Returns:
            Selected BackendServer instance.

        Raises:
            ValueError: If no servers are available or strategy is invalid.
        """
        if not self._servers:
            raise ValueError("No servers available for routing")

        # Select server based on strategy
        if strategy == LoadBalancerStrategy.ROUND_ROBIN:
            server_ids = list(self._servers.keys())
            index = self._get_next_round_robin_index()
            server_id = server_ids[index]
        elif strategy == LoadBalancerStrategy.LEAST_CONNECTIONS:
            selected_server = self._select_least_connections_server()
            server_id = selected_server.id
        elif strategy == LoadBalancerStrategy.AI_POWERED:
            selected_server = self._select_ai_powered_server(prediction_scores)
            server_id = selected_server.id
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Get the selected server
        server = self._servers[server_id]

        # Record routing decision in history
        prediction_score = prediction_scores.get(server_id) if prediction_scores else None
        entry = RoutingEntry(
            timestamp=datetime.now(),
            server_id=server_id,
            strategy=strategy,
            prediction_score=prediction_score
        )

        with self._lock:
            self._routing_history.append(entry)
            # Trim history if exceeds max
            if len(self._routing_history) > self._max_history:
                self._routing_history = self._routing_history[-self._max_history:]

        return server

    def get_server_stats(self, server_id: str) -> Optional[Dict]:
        """
        Get statistics for a specific server.

        Args:
            server_id: Unique identifier of the server.

        Returns:
            Dict containing server statistics, or None if server not found.
        """
        with self._lock:
            if server_id not in self._servers:
                return None

            server = self._servers[server_id]

            # Count routing occurrences for this server
            route_count = sum(1 for entry in self._routing_history if entry.server_id == server_id)

            return {
                "id": server.id,
                "host": server.host,
                "port": server.port,
                "cpu_usage": server.cpu_usage,
                "active_connections": server.active_connections,
                "avg_response_time": server.avg_response_time,
                "total_requests_routed": route_count
            }

    def get_all_stats(self) -> Dict:
        """
        Get statistics for all servers in the pool.

        Returns:
            Dict mapping server IDs to their statistics.
        """
        with self._lock:
            stats = {}
            for server_id in self._servers.keys():
                stats[server_id] = self.get_server_stats(server_id)
            return stats

    def get_routing_history(
        self,
        limit: Optional[int] = None,
        strategy_filter: Optional[LoadBalancerStrategy] = None
    ) -> List[Dict]:
        """
        Get routing history for analysis.

        Args:
            limit: Maximum number of entries to return (most recent first).
            strategy_filter: Optional filter to only include specific strategy.

        Returns:
            List of routing entries as dicts.
        """
        with self._lock:
            history = self._routing_history

            if strategy_filter:
                history = [e for e in history if e.strategy == strategy_filter]

            # Convert to list of dicts, most recent first
            entries = [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "server_id": entry.server_id,
                    "strategy": entry.strategy.value,
                    "prediction_score": entry.prediction_score
                }
                for entry in reversed(history)
            ]

            if limit:
                entries = entries[:limit]

            return entries

    def update_server_metrics(
        self,
        server_id: str,
        cpu_usage: Optional[float] = None,
        active_connections: Optional[int] = None,
        avg_response_time: Optional[float] = None
    ) -> bool:
        """
        Update metrics for an existing server.

        Args:
            server_id: Unique identifier of the server to update.
            cpu_usage: New CPU usage value (0-100).
            active_connections: New active connection count.
            avg_response_time: New average response time in milliseconds.

        Returns:
            True if update successful, False if server not found.
        """
        with self._lock:
            if server_id not in self._servers:
                return False

            server = self._servers[server_id]
            if cpu_usage is not None:
                server.cpu_usage = cpu_usage
            if active_connections is not None:
                server.active_connections = active_connections
            if avg_response_time is not None:
                server.avg_response_time = avg_response_time
            return True

    @property
    def server_count(self) -> int:
        """Get the number of registered servers."""
        with self._lock:
            return len(self._servers)

    @property
    def history_count(self) -> int:
        """Get the number of routing history entries."""
        with self._lock:
            return len(self._routing_history)