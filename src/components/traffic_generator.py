"""
Traffic Generator Component

Simulates user requests at varying rates for the AI-Driven Infrastructure Manager.
Supports multiple traffic patterns including constant, ramp, spike, and sine wave.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4
import threading
import time

import numpy as np


@dataclass
class Request:
    """
    Represents a simulated user request.

    Attributes:
        timestamp: When the request was generated
        request_id: Unique identifier for the request
        payload_size: Simulated payload size in bytes
    """
    timestamp: datetime
    request_id: str
    payload_size: int


class TrafficGenerator:
    """
    Generates simulated user requests with various traffic patterns.

    This class provides configurable request generation for load testing
    and infrastructure validation. It supports constant, ramp, spike,
    and sine wave traffic patterns with thread-safe operations.

    Attributes:
        base_rate: Base requests per second (default: 10)
        max_rate: Maximum allowed requests per second (default: 100)
        duration: Total duration in seconds (default: 60.0)
    """

    def __init__(
        self,
        base_rate: int = 10,
        max_rate: int = 100,
        duration: float = 60.0
    ) -> None:
        """
        Initialize the TrafficGenerator.

        Args:
            base_rate: Base requests per second
            max_rate: Maximum allowed requests per second
            duration: Total duration in seconds
        """
        self.base_rate = base_rate
        self.max_rate = max_rate
        self.duration = duration
        self._lock = threading.Lock()
        self._request_count = 0

    def _generate_request_id(self) -> str:
        """
        Generate a unique request ID in a thread-safe manner.

        Returns:
            A unique UUID string for the request.
        """
        with self._lock:
            self._request_count += 1
            return f"req-{uuid4()}"

    def _simulate_payload(self) -> int:
        """
        Simulate a realistic payload size using normal distribution.

        Returns:
            Payload size in bytes (range: 1024 to 102400)
        """
        mean_size = 51200  # 50KB average
        std_dev = 20000    # ~20KB deviation

        size = int(np.random.normal(mean_size, std_dev))

        # Clamp to realistic bounds (1KB to 100KB)
        return max(1024, min(102400, size))

    def generate_request(self) -> Request:
        """
        Generate a single request with current timestamp.

        Returns:
            A Request object with timestamp, ID, and payload size.
        """
        return Request(
            timestamp=datetime.now(),
            request_id=self._generate_request_id(),
            payload_size=self._simulate_payload()
        )

    def generate_constant(self, rate: Optional[int] = None) -> Request:
        """
        Generate a request at a constant rate.

        Args:
            rate: Requests per second (defaults to base_rate).

        Returns:
            A Request object.
        """
        current_rate = rate if rate is not None else self.base_rate
        self._simulate_inter_arrival(current_rate)

        return self.generate_request()

    def generate_ramp(
        self,
        start_rate: int,
        end_rate: int,
        duration: float,
        progress: float
    ) -> Request:
        """
        Generate a request with ramp pattern (gradual increase/decrease).

        The rate transitions linearly from start_rate to end_rate over duration.

        Args:
            start_rate: Initial requests per second
            end_rate: Final requests per second
            duration: Total duration of the ramp in seconds
            progress: Current progress through the ramp (0.0 to 1.0)

        Returns:
            A Request object.
        """
        rate = int(start_rate + (end_rate - start_rate) * progress)
        rate = max(1, min(self.max_rate, rate))

        self._simulate_inter_arrival(rate)

        return self.generate_request()

    def generate_spike(
        self,
        peak_rate: int,
        progress: float,
        spike_width: float = 0.1
    ) -> Request:
        """
        Generate a request during a traffic spike pattern.

        Creates a sudden spike in traffic that peaks and then subsides.

        Args:
            peak_rate: Maximum requests per second during spike
            progress: Current progress through the spike (0.0 to 1.0)
            spike_width: Width of the spike relative to its duration (0.0 to 1.0)

        Returns:
            A Request object.
        """
        # Calculate rate based on progress through spike
        if progress <= spike_width / 2:
            # Rising edge
            normalized = progress / (spike_width / 2)
            rate = int(self.base_rate + (peak_rate - self.base_rate) * normalized)
        elif progress <= spike_width:
            # Falling edge
            normalized = (progress - spike_width / 2) / (spike_width / 2)
            rate = int(peak_rate - (peak_rate - self.base_rate) * normalized)
        else:
            # Normal traffic
            rate = self.base_rate

        rate = max(1, min(self.max_rate, rate))

        self._simulate_inter_arrival(rate)

        return self.generate_request()

    def generate_sine_wave(
        self,
        amplitude: Optional[int] = None,
        period: float = 30.0,
        time_elapsed: float = 0.0
    ) -> Request:
        """
        Generate a request following a sine wave pattern.

        Simulates periodic traffic patterns like daily user behavior.

        Args:
            amplitude: Peak deviation from base rate (defaults to base_rate/2)
            period: Time in seconds for one complete cycle
            time_elapsed: Current time in the cycle (0 to period)

        Returns:
            A Request object.
        """
        if amplitude is None:
            amplitude = self.base_rate // 2

        # Normalize time to [0, 2*pi]
        phase = (time_elapsed / period) * 2 * np.pi

        # Calculate rate using sine wave
        rate = int(
            self.base_rate +
            amplitude * np.sin(phase)
        )

        rate = max(1, min(self.max_rate, rate))

        self._simulate_inter_arrival(rate)

        return self.generate_request()

    def _simulate_inter_arrival(self, rate: int) -> None:
        """
        Simulate the inter-arrival time based on Poisson distribution.

        Args:
            rate: Target requests per second
        """
        # Poisson distribution for realistic inter-arrival times
        expected_interval = 1.0 / rate if rate > 0 else 1.0
        interval = np.random.poisson(expected_interval)
        time.sleep(max(0, interval / 1000))  # Convert to seconds

    def generate_burst(
        self,
        burst_size: int,
        base_rate: Optional[int] = None
    ) -> list[Request]:
        """
        Generate a burst of requests.

        Simulates a group of users making requests simultaneously.

        Args:
            burst_size: Number of requests to generate in the burst
            base_rate: Baseline rate for inter-burst spacing

        Returns:
            List of Request objects
        """
        requests = []
        current_base = base_rate if base_rate is not None else self.base_rate

        for _ in range(burst_size):
            requests.append(self.generate_request())

        return requests

    def generate_pattern(
        self,
        pattern_type: str,
        duration: float,
        **kwargs
    ) -> list[Request]:
        """
        Generate a complete traffic pattern over a duration.

        Args:
            pattern_type: One of 'constant', 'ramp', 'spike', 'sine_wave'
            duration: Total duration in seconds
            **kwargs: Pattern-specific parameters

        Returns:
            List of all generated requests
        """
        requests = []
        start_time = time.time()

        if pattern_type == 'constant':
            rate = kwargs.get('rate', self.base_rate)
            while time.time() - start_time < duration:
                requests.append(self.generate_constant(rate))

        elif pattern_type == 'ramp':
            start_rate = kwargs.get('start_rate', self.base_rate)
            end_rate = kwargs.get('end_rate', self.max_rate)
            elapsed = 0.0
            while elapsed < duration:
                progress = elapsed / duration
                requests.append(self.generate_ramp(start_rate, end_rate, duration, progress))
                elapsed = time.time() - start_time

        elif pattern_type == 'spike':
            peak_rate = kwargs.get('peak_rate', self.max_rate)
            spike_width = kwargs.get('spike_width', 0.1)
            elapsed = 0.0
            while elapsed < duration:
                progress = elapsed / duration
                requests.append(self.generate_spike(peak_rate, progress, spike_width))
                elapsed = time.time() - start_time

        elif pattern_type == 'sine_wave':
            amplitude = kwargs.get('amplitude', self.base_rate // 2)
            period = kwargs.get('period', 30.0)
            elapsed = 0.0
            while elapsed < duration:
                requests.append(self.generate_sine_wave(amplitude, period, elapsed))
                elapsed = time.time() - start_time

        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")

        return requests

    @property
    def request_count(self) -> int:
        """Get the total number of requests generated (thread-safe)."""
        with self._lock:
            return self._request_count

    def reset_count(self) -> None:
        """Reset the request counter (thread-safe)."""
        with self._lock:
            self._request_count = 0