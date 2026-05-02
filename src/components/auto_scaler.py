"""
Auto-Scaler Component for AI-Driven Infrastructure Manager.

Provides intelligent auto-scaling decisions based on real-time metrics
and predictive load analysis for backend server infrastructure.
"""

import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


class ScalingActionType(Enum):
    """Enumeration of possible scaling actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_STABLE = "scale_stable"


@dataclass
class ScalingAction:
    """
    Represents a scaling decision made by the AutoScaler.

    Attributes:
        action_type: The type of scaling action (SCALE_UP, SCALE_DOWN, SCALE_STABLE)
        servers_added_removed: Number of servers to add (positive) or remove (negative)
        reason: Human-readable explanation for the scaling decision
        timestamp: Unix timestamp when the decision was made
    """
    action_type: ScalingActionType
    servers_added_removed: int
    reason: str
    timestamp: float

    def to_dict(self) -> dict:
        """Convert scaling action to dictionary format."""
        return {
            'action_type': self.action_type.value,
            'servers_added_removed': self.servers_added_removed,
            'reason': self.reason,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
        }

    def __repr__(self) -> str:
        """String representation of the scaling action."""
        return (
            f"ScalingAction(type={self.action_type.value}, "
            f"servers={self.servers_added_removed:+d}, reason='{self.reason}')"
        )


@dataclass
class AutoScalerConfig:
    """
    Configuration settings for the AutoScaler.

    Attributes:
        min_servers: Minimum number of servers allowed (safety floor)
        max_servers: Maximum number of servers allowed (capacity ceiling)
        scale_up_threshold: CPU percentage threshold to trigger scale up (e.g., 70.0)
        scale_down_threshold: CPU percentage threshold to trigger scale down (e.g., 30.0)
        scale_up_cooldown: Seconds to wait after a scale-up before another scale-up
        scale_down_cooldown: Seconds to wait after a scale-down before another scale-down
    """
    min_servers: int = 1
    max_servers: int = 10
    scale_up_threshold: float = 70.0
    scale_down_threshold: float = 30.0
    scale_up_cooldown: int = 60
    scale_down_cooldown: int = 120

    def __post_init__(self):
        """Validate configuration values."""
        if self.min_servers < 1:
            raise ValueError("min_servers must be at least 1")
        if self.max_servers < self.min_servers:
            raise ValueError("max_servers must be >= min_servers")
        if self.scale_up_threshold <= self.scale_down_threshold:
            raise ValueError("scale_up_threshold must be > scale_down_threshold")
        if self.scale_up_cooldown < 0:
            raise ValueError("scale_up_cooldown cannot be negative")
        if self.scale_down_cooldown < 0:
            raise ValueError("scale_down_cooldown cannot be negative")


class AutoScaler:
    """
    Intelligent auto-scaling component with predictive capabilities.

    The AutoScaler makes scaling decisions based on:
    - Current system metrics (CPU, memory, etc.)
    - Predicted future load
    - Configured thresholds and cooldown periods

    Features:
        - Predictive scaling based on load forecasts
        - Configurable thresholds for scale up/down decisions
        - Cooldown periods to prevent rapid scaling oscillations
        - Scaling history tracking for analysis and auditing
        - Respects min/max server limits

    Decision Logic:
        1. If predicted_load > scale_up_threshold: SCALE_UP
        2. If predicted_load < scale_down_threshold: SCALE_DOWN
        3. Otherwise: SCALE_STABLE

        Cooldown periods are respected to prevent thrashing.
        Server count never exceeds configured min/max limits.
    """

    def __init__(self, config: Optional[AutoScalerConfig] = None):
        """
        Initialize the AutoScaler with optional configuration.

        Args:
            config: AutoScalerConfig instance. Uses defaults if None.
        """
        self.config = config or AutoScalerConfig()
        self._current_servers: int = self.config.min_servers
        self._scaling_history: list[ScalingAction] = []
        self._last_scale_up_time: float = 0.0
        self._last_scale_down_time: float = 0.0
        self._total_scale_ups: int = 0
        self._total_scale_downs: int = 0

    @property
    def current_servers(self) -> int:
        """Get the current number of servers."""
        return self._current_servers

    @current_servers.setter
    def current_servers(self, value: int) -> None:
        """Set the current number of servers within configured limits."""
        self._current_servers = max(self.config.min_servers, min(self.config.max_servers, value))

    @property
    def scaling_history(self) -> list[ScalingAction]:
        """Get a copy of the scaling history."""
        return list(self._scaling_history)

    def evaluate(self, metrics: dict, prediction: float) -> ScalingAction:
        """
        Evaluate scaling needs based on current metrics and load prediction.

        This is a convenience method that extracts the relevant metric
        (cpu_usage) and delegates to make_scaling_decision.

        Args:
            metrics: Dictionary containing server metrics (expects 'cpu_usage' key)
            prediction: Predicted future load value (0-100 scale for CPU percentage)

        Returns:
            ScalingAction representing the recommended action
        """
        cpu_usage = metrics.get('cpu_usage', 50.0)
        return self.make_scaling_decision(self._current_servers, cpu_usage, prediction)

    def make_scaling_decision(
        self,
        current_servers: int,
        metrics: float,
        predicted_load: float
    ) -> ScalingAction:
        """
        Make a scaling decision based on metrics and predicted load.

        Decision Logic:
            - SCALE_UP: If predicted_load > scale_up_threshold
            - SCALE_DOWN: If predicted_load < scale_down_threshold
            - SCALE_STABLE: Otherwise

        Cooldown rules:
            - Cannot scale up within scale_up_cooldown seconds of last scale up
            - Cannot scale down within scale_down_cooldown seconds of last scale down

        Server limit rules:
            - Never scale up beyond max_servers
            - Never scale down below min_servers

        Args:
            current_servers: Current number of active servers
            metrics: Current CPU usage percentage (0-100)
            predicted_load: Predicted CPU usage percentage (0-100)

        Returns:
            ScalingAction with the recommended scaling decision
        """
        self._current_servers = current_servers
        current_time = time.time()
        action: ScalingAction

        # Determine scaling direction based on predicted load
        if predicted_load > self.config.scale_up_threshold:
            # Check if scale up is allowed (cooldown and server limits)
            can_scale_up = (
                current_time - self._last_scale_up_time >= self.config.scale_up_cooldown
            ) and self._current_servers < self.config.max_servers

            if can_scale_up:
                self._current_servers += 1
                self._last_scale_up_time = current_time
                self._total_scale_ups += 1
                action = ScalingAction(
                    action_type=ScalingActionType.SCALE_UP,
                    servers_added_removed=1,
                    reason=(
                        f"Predicted load ({predicted_load:.1f}%) exceeds threshold "
                        f"({self.config.scale_up_threshold:.1f}%). "
                        f"Adding server to handle increased demand. "
                        f"Current servers: {current_servers} -> {self._current_servers}"
                    ),
                    timestamp=current_time
                )
            else:
                # Cooldown active or at max servers
                cooldown_remaining = max(
                    0, self.config.scale_up_cooldown - (current_time - self._last_scale_up_time)
                )
                action = ScalingAction(
                    action_type=ScalingActionType.SCALE_STABLE,
                    servers_added_removed=0,
                    reason=(
                        f"Scale up blocked: {'at maximum capacity' if self._current_servers >= self.config.max_servers else f'cooldown active ({cooldown_remaining:.0f}s remaining)'}. "
                        f"Predicted load: {predicted_load:.1f}%"
                    ),
                    timestamp=current_time
                )

        elif predicted_load < self.config.scale_down_threshold:
            # Check if scale down is allowed (cooldown and server limits)
            can_scale_down = (
                current_time - self._last_scale_down_time >= self.config.scale_down_cooldown
            ) and self._current_servers > self.config.min_servers

            if can_scale_down:
                self._current_servers -= 1
                self._last_scale_down_time = current_time
                self._total_scale_downs += 1
                action = ScalingAction(
                    action_type=ScalingActionType.SCALE_DOWN,
                    servers_added_removed=-1,
                    reason=(
                        f"Predicted load ({predicted_load:.1f}%) below threshold "
                        f"({self.config.scale_down_threshold:.1f}%). "
                        f"Removing server to optimize resource usage. "
                        f"Current servers: {current_servers} -> {self._current_servers}"
                    ),
                    timestamp=current_time
                )
            else:
                # Cooldown active or at min servers
                cooldown_remaining = max(
                    0, self.config.scale_down_cooldown - (current_time - self._last_scale_down_time)
                )
                action = ScalingAction(
                    action_type=ScalingActionType.SCALE_STABLE,
                    servers_added_removed=0,
                    reason=(
                        f"Scale down blocked: {'at minimum capacity' if self._current_servers <= self.config.min_servers else f'cooldown active ({cooldown_remaining:.0f}s remaining)'}. "
                        f"Predicted load: {predicted_load:.1f}%"
                    ),
                    timestamp=current_time
                )

        else:
            # Load is within stable range
            action = ScalingAction(
                action_type=ScalingActionType.SCALE_STABLE,
                servers_added_removed=0,
                reason=(
                    f"Load stable. Predicted: {predicted_load:.1f}%, "
                    f"Range: [{self.config.scale_down_threshold:.1f}%, {self.config.scale_up_threshold:.1f}%]"
                ),
                timestamp=current_time
            )

        # Record action in history
        self._scaling_history.append(action)

        # Keep history size manageable (last 1000 actions)
        if len(self._scaling_history) > 1000:
            self._scaling_history = self._scaling_history[-1000:]

        return action

    def get_status(self) -> dict:
        """
        Get current status of the AutoScaler.

        Returns:
            Dictionary containing current state, configuration, and statistics
        """
        current_time = time.time()

        # Calculate remaining cooldowns
        scale_up_cooldown_remaining = max(
            0, self.config.scale_up_cooldown - (current_time - self._last_scale_up_time)
        )
        scale_down_cooldown_remaining = max(
            0, self.config.scale_down_cooldown - (current_time - self._last_scale_down_time)
        )

        # Get recent actions (last 5)
        recent_actions = [action.to_dict() for action in self._scaling_history[-5:]]

        return {
            'current_servers': self._current_servers,
            'config': {
                'min_servers': self.config.min_servers,
                'max_servers': self.config.max_servers,
                'scale_up_threshold': self.config.scale_up_threshold,
                'scale_down_threshold': self.config.scale_down_threshold,
                'scale_up_cooldown': self.config.scale_up_cooldown,
                'scale_down_cooldown': self.config.scale_down_cooldown,
            },
            'cooldowns': {
                'scale_up_remaining_seconds': round(scale_up_cooldown_remaining, 1),
                'scale_down_remaining_seconds': round(scale_down_cooldown_remaining, 1),
                'can_scale_up': scale_up_cooldown_remaining == 0 and self._current_servers < self.config.max_servers,
                'can_scale_down': scale_down_cooldown_remaining == 0 and self._current_servers > self.config.min_servers,
            },
            'statistics': {
                'total_scale_ups': self._total_scale_ups,
                'total_scale_downs': self._total_scale_downs,
                'total_actions': len(self._scaling_history),
                'last_action': self._scaling_history[-1].to_dict() if self._scaling_history else None,
            },
            'recent_actions': recent_actions,
            'timestamp': datetime.now().isoformat()
        }

    def reset_cooldowns(self) -> None:
        """
        Reset all cooldown timers.

        Use this method to allow immediate scaling decisions
        after configuration changes or manual intervention.
        """
        self._last_scale_up_time = 0.0
        self._last_scale_down_time = 0.0

    def get_scaling_history(self, limit: Optional[int] = None) -> list[dict]:
        """
        Get scaling history as list of dictionaries.

        Args:
            limit: Maximum number of entries to return (most recent first).
                  If None, returns all entries.

        Returns:
            List of scaling action dictionaries
        """
        history = self._scaling_history
        if limit:
            history = history[-limit:]
        return [action.to_dict() for action in history]

    def reset_statistics(self) -> None:
        """Reset scaling statistics (total_scale_ups, total_scale_downs, history)."""
        self._total_scale_ups = 0
        self._total_scale_downs = 0
        self._scaling_history.clear()


def create_auto_scaler(
    min_servers: int = 1,
    max_servers: int = 10,
    scale_up_threshold: float = 70.0,
    scale_down_threshold: float = 30.0,
    scale_up_cooldown: int = 60,
    scale_down_cooldown: int = 120
) -> AutoScaler:
    """
    Factory function to create a new AutoScaler with custom configuration.

    Args:
        min_servers: Minimum number of servers allowed
        max_servers: Maximum number of servers allowed
        scale_up_threshold: CPU percentage to trigger scale up
        scale_down_threshold: CPU percentage to trigger scale down
        scale_up_cooldown: Seconds between scale up actions
        scale_down_cooldown: Seconds between scale down actions

    Returns:
        Configured AutoScaler instance
    """
    config = AutoScalerConfig(
        min_servers=min_servers,
        max_servers=max_servers,
        scale_up_threshold=scale_up_threshold,
        scale_down_threshold=scale_down_threshold,
        scale_up_cooldown=scale_up_cooldown,
        scale_down_cooldown=scale_down_cooldown
    )
    return AutoScaler(config=config)