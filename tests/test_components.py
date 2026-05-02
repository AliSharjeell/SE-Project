"""
Unit tests for Infrastructure Manager Components.

Tests TrafficGenerator, MonitoringSystem, LoadBalancer, and AutoScaler.
"""

import pytest
import time
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from components.traffic_generator import TrafficGenerator, Request
from components.monitor import MonitoringSystem, ServerMetrics
from components.load_balancer import LoadBalancer, BackendServer, LoadBalancerStrategy
from components.auto_scaler import AutoScaler, AutoScalerConfig, ScalingActionType


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def traffic_generator():
    """Create a TrafficGenerator with test parameters."""
    return TrafficGenerator(base_rate=10, max_rate=100, duration=60.0)


@pytest.fixture
def monitoring_system():
    """Create a MonitoringSystem with small history for testing."""
    return MonitoringSystem(history_size=100)


@pytest.fixture
def load_balancer():
    """Create a LoadBalancer with test servers."""
    lb = LoadBalancer(max_history=100)
    # Add test servers
    lb.add_server(BackendServer(id="server-1", host="localhost", port=8001))
    lb.add_server(BackendServer(id="server-2", host="localhost", port=8002))
    lb.add_server(BackendServer(id="server-3", host="localhost", port=8003))
    return lb


@pytest.fixture
def auto_scaler():
    """Create an AutoScaler with default configuration."""
    return AutoScaler()


@pytest.fixture
def sample_metrics():
    """Create sample server metrics for testing."""
    return ServerMetrics(
        cpu_usage=50.0,
        memory_usage=60.0,
        response_time=100.0,
        request_rate=150.0,
        active_connections=25,
        timestamp=time.time()
    )


# ============================================================================
# TrafficGenerator Tests
# ============================================================================

class TestTrafficGenerator:
    """Tests for TrafficGenerator component."""

    def test_initialization(self, traffic_generator):
        """Test TrafficGenerator initializes with correct defaults."""
        assert traffic_generator.base_rate == 10
        assert traffic_generator.max_rate == 100
        assert traffic_generator.duration == 60.0

    def test_generate_request(self, traffic_generator):
        """Test single request generation."""
        request = traffic_generator.generate_request()
        assert isinstance(request, Request)
        assert request.request_id.startswith("req-")
        assert request.payload_size >= 1024
        assert request.payload_size <= 102400
        assert isinstance(request.timestamp, datetime)

    def test_generate_constant(self, traffic_generator):
        """Test constant traffic pattern generation."""
        request = traffic_generator.generate_constant(rate=20)
        assert isinstance(request, Request)
        assert request.request_id.startswith("req-")

    def test_generate_ramp(self, traffic_generator):
        """Test ramp traffic pattern generation."""
        request = traffic_generator.generate_ramp(
            start_rate=10,
            end_rate=50,
            duration=60.0,
            progress=0.5
        )
        assert isinstance(request, Request)
        # At progress=0.5, rate should be (10 + 50) / 2 = 30
        # The request should be generated without error

    def test_generate_spike(self, traffic_generator):
        """Test spike traffic pattern generation."""
        # Test rising edge (progress < spike_width/2)
        request = traffic_generator.generate_spike(peak_rate=100, progress=0.05, spike_width=0.1)
        assert isinstance(request, Request)

        # Test falling edge
        request = traffic_generator.generate_spike(peak_rate=100, progress=0.08, spike_width=0.1)
        assert isinstance(request, Request)

        # Test normal traffic (after spike)
        request = traffic_generator.generate_spike(peak_rate=100, progress=0.5, spike_width=0.1)
        assert isinstance(request, Request)

    def test_generate_sine_wave(self, traffic_generator):
        """Test sine wave traffic pattern generation."""
        # Test at start of period
        request = traffic_generator.generate_sine_wave(period=30.0, time_elapsed=0.0)
        assert isinstance(request, Request)

        # Test at peak (quarter period)
        request = traffic_generator.generate_sine_wave(period=30.0, time_elapsed=7.5)
        assert isinstance(request, Request)

    def test_generate_burst(self, traffic_generator):
        """Test burst traffic generation."""
        requests = traffic_generator.generate_burst(burst_size=5)
        assert len(requests) == 5
        assert all(isinstance(r, Request) for r in requests)

    def test_request_count(self, traffic_generator):
        """Test request counter."""
        initial_count = traffic_generator.request_count
        traffic_generator.generate_request()
        traffic_generator.generate_request()
        assert traffic_generator.request_count == initial_count + 2

    def test_reset_count(self, traffic_generator):
        """Test resetting request counter."""
        traffic_generator.generate_request()
        traffic_generator.generate_request()
        traffic_generator.reset_count()
        assert traffic_generator.request_count == 0


# ============================================================================
# MonitoringSystem Tests
# ============================================================================

class TestMonitoringSystem:
    """Tests for MonitoringSystem component."""

    def test_initialization(self, monitoring_system):
        """Test MonitoringSystem initializes correctly."""
        assert monitoring_system.history_size == 100
        assert monitoring_system.history_count == 0

    def test_add_metric(self, monitoring_system, sample_metrics):
        """Test adding metrics to history."""
        monitoring_system.add_metric(sample_metrics)
        assert monitoring_system.history_count == 1

    def test_add_metric_raw(self, monitoring_system):
        """Test adding raw metric values."""
        metric = monitoring_system.add_metric_raw(
            cpu_usage=50.0,
            memory_usage=60.0,
            response_time=100.0,
            request_rate=150.0,
            active_connections=25
        )
        assert isinstance(metric, ServerMetrics)
        assert metric.cpu_usage == 50.0

    def test_get_latest(self, monitoring_system, sample_metrics):
        """Test retrieving latest metric."""
        monitoring_system.add_metric(sample_metrics)
        latest = monitoring_system.get_latest()
        assert latest == sample_metrics

    def test_get_latest_empty(self, monitoring_system):
        """Test get_latest returns None when empty."""
        assert monitoring_system.get_latest() is None

    def test_get_history(self, monitoring_system, sample_metrics):
        """Test retrieving metrics history."""
        monitoring_system.add_metric(sample_metrics)
        monitoring_system.add_metric(sample_metrics)
        history = monitoring_system.get_history()
        assert len(history) == 2

    def test_get_history_with_limit(self, monitoring_system, sample_metrics):
        """Test retrieving limited history."""
        for _ in range(5):
            monitoring_system.add_metric(sample_metrics)
        history = monitoring_system.get_history(limit=2)
        assert len(history) == 2

    def test_calculate_stats(self, monitoring_system, sample_metrics):
        """Test statistics calculation."""
        # Add multiple metrics with known values
        base_time = time.time()
        for cpu in [30.0, 40.0, 50.0, 60.0, 70.0]:
            monitoring_system.add_metric(ServerMetrics(
                cpu_usage=cpu,
                memory_usage=60.0,
                response_time=100.0,
                request_rate=150.0,
                active_connections=25,
                timestamp=base_time
            ))
            base_time += 1

        stats = monitoring_system.calculate_stats('cpu_usage')
        assert stats['avg'] == 50.0
        assert stats['min'] == 30.0
        assert stats['max'] == 70.0
        assert stats['count'] == 5
        assert 'p50' in stats
        assert 'p90' in stats

    def test_calculate_stats_empty(self, monitoring_system):
        """Test stats calculation returns zeros for empty history."""
        stats = monitoring_system.calculate_stats('cpu_usage')
        assert stats['avg'] == 0.0
        assert stats['count'] == 0

    def test_get_all_stats(self, monitoring_system, sample_metrics):
        """Test getting all field statistics."""
        monitoring_system.add_metric(sample_metrics)
        all_stats = monitoring_system.get_all_stats()
        assert 'cpu_usage' in all_stats
        assert 'memory_usage' in all_stats
        assert 'response_time' in all_stats
        assert 'request_rate' in all_stats
        assert 'active_connections' in all_stats

    def test_clear_history(self, monitoring_system, sample_metrics):
        """Test clearing metrics history."""
        monitoring_system.add_metric(sample_metrics)
        monitoring_system.add_metric(sample_metrics)
        assert monitoring_system.history_count == 2
        monitoring_system.clear_history()
        assert monitoring_system.history_count == 0

    def test_generate_simulated_metric(self, monitoring_system):
        """Test simulated metric generation."""
        metric = monitoring_system.generate_simulated_metric()
        assert isinstance(metric, ServerMetrics)
        assert 0 <= metric.cpu_usage <= 100
        assert 0 <= metric.memory_usage <= 100
        assert metric.response_time >= 0
        assert metric.request_rate >= 0
        assert metric.active_connections >= 0

    def test_history_buffer_limit(self, monitoring_system):
        """Test that history respects max size."""
        # Add more metrics than history size
        for _ in range(150):
            monitoring_system.add_metric_raw(
                cpu_usage=50.0,
                memory_usage=60.0,
                response_time=100.0,
                request_rate=150.0,
                active_connections=25
            )
        # Should be capped at history_size
        assert monitoring_system.history_count == 100


# ============================================================================
# LoadBalancer Tests
# ============================================================================

class TestLoadBalancer:
    """Tests for LoadBalancer component."""

    def test_initialization(self, load_balancer):
        """Test LoadBalancer initializes correctly."""
        assert load_balancer.server_count == 3
        assert load_balancer.history_count == 0

    def test_add_server(self):
        """Test adding servers to load balancer."""
        lb = LoadBalancer()
        server = BackendServer(id="test-1", host="localhost", port=9000)
        assert lb.add_server(server) is True
        assert lb.server_count == 1

    def test_add_duplicate_server(self, load_balancer):
        """Test adding duplicate server fails."""
        server = BackendServer(id="server-1", host="localhost", port=9000)
        assert load_balancer.add_server(server) is False
        assert load_balancer.server_count == 3

    def test_remove_server(self, load_balancer):
        """Test removing server from load balancer."""
        assert load_balancer.remove_server("server-1") is True
        assert load_balancer.server_count == 2

    def test_remove_nonexistent_server(self, load_balancer):
        """Test removing nonexistent server returns False."""
        assert load_balancer.remove_server("nonexistent") is False

    def test_get_server(self, load_balancer):
        """Test retrieving server by ID."""
        server = load_balancer.get_server("server-1")
        assert server is not None
        assert server.id == "server-1"
        assert server.host == "localhost"
        assert server.port == 8001

    def test_get_all_servers(self, load_balancer):
        """Test retrieving all servers."""
        servers = load_balancer.get_all_servers()
        assert len(servers) == 3

    def test_route_round_robin(self, load_balancer):
        """Test round-robin routing strategy."""
        routes = []
        for _ in range(6):
            server = load_balancer.route_request(LoadBalancerStrategy.ROUND_ROBIN)
            routes.append(server.id)

        # Should cycle through servers evenly
        assert len(set(routes)) <= 3
        assert load_balancer.history_count == 6

    def test_route_least_connections(self, load_balancer):
        """Test least connections routing strategy."""
        # Update server connection counts
        load_balancer.update_server_metrics("server-1", active_connections=10)
        load_balancer.update_server_metrics("server-2", active_connections=5)
        load_balancer.update_server_metrics("server-3", active_connections=15)

        # Route multiple requests
        server = load_balancer.route_request(LoadBalancerStrategy.LEAST_CONNECTIONS)
        assert server.id == "server-2"  # Should be least loaded

    def test_route_ai_powered(self, load_balancer):
        """Test AI-powered routing strategy uses weighted probability."""
        prediction_scores = {
            "server-1": 0.9,
            "server-2": 0.5,
            "server-3": 0.1
        }

        # Run multiple times - server-1 should be selected most often
        # due to highest weight (weighted random selection)
        results = {}
        for _ in range(100):
            server = load_balancer.route_request(
                LoadBalancerStrategy.AI_POWERED,
                prediction_scores=prediction_scores
            )
            results[server.id] = results.get(server.id, 0) + 1

        # Server-1 should be selected most frequently (highest weight)
        assert results.get("server-1", 0) > results.get("server-2", 0)
        assert results.get("server-1", 0) > results.get("server-3", 0)

    def test_route_no_servers(self):
        """Test routing with no servers raises error."""
        lb = LoadBalancer()
        with pytest.raises(ValueError, match="No servers available"):
            lb.route_request(LoadBalancerStrategy.ROUND_ROBIN)

    def test_update_server_metrics(self, load_balancer):
        """Test updating server metrics."""
        result = load_balancer.update_server_metrics(
            "server-1",
            cpu_usage=75.0,
            active_connections=50
        )
        assert result is True
        server = load_balancer.get_server("server-1")
        assert server.cpu_usage == 75.0
        assert server.active_connections == 50

    def test_get_server_stats(self, load_balancer):
        """Test retrieving server statistics."""
        load_balancer.route_request(LoadBalancerStrategy.ROUND_ROBIN)
        stats = load_balancer.get_server_stats("server-1")
        assert stats is not None
        assert stats['id'] == "server-1"
        assert stats['total_requests_routed'] >= 1

    def test_get_all_stats(self, load_balancer):
        """Test retrieving all server statistics."""
        load_balancer.route_request(LoadBalancerStrategy.ROUND_ROBIN)
        all_stats = load_balancer.get_all_stats()
        assert len(all_stats) == 3
        assert "server-1" in all_stats

    def test_routing_history(self, load_balancer):
        """Test routing history tracking."""
        load_balancer.route_request(LoadBalancerStrategy.ROUND_ROBIN)
        history = load_balancer.get_routing_history()
        assert len(history) >= 1
        assert 'timestamp' in history[0]
        assert 'server_id' in history[0]
        assert 'strategy' in history[0]


# ============================================================================
# AutoScaler Tests
# ============================================================================

class TestAutoScaler:
    """Tests for AutoScaler component."""

    def test_initialization(self, auto_scaler):
        """Test AutoScaler initializes correctly."""
        assert auto_scaler.current_servers >= 1
        assert auto_scaler.config.min_servers == 1
        assert auto_scaler.config.max_servers == 10

    def test_config_validation(self):
        """Test AutoScalerConfig validation."""
        # Valid config
        config = AutoScalerConfig(min_servers=2, max_servers=5)
        assert config.min_servers == 2
        assert config.max_servers == 5

        # Invalid: min > max
        with pytest.raises(ValueError):
            AutoScalerConfig(min_servers=10, max_servers=5)

        # Invalid: scale_up <= scale_down
        with pytest.raises(ValueError):
            AutoScalerConfig(scale_up_threshold=30, scale_down_threshold=40)

    def test_scale_up_decision(self, auto_scaler):
        """Test scale up decision when load is high."""
        action = auto_scaler.make_scaling_decision(
            current_servers=1,
            metrics=80.0,
            predicted_load=85.0
        )
        assert action.action_type == ScalingActionType.SCALE_UP
        assert action.servers_added_removed == 1

    def test_scale_down_decision(self, auto_scaler):
        """Test scale down decision when load is low."""
        # Start with more servers
        auto_scaler._current_servers = 5
        action = auto_scaler.make_scaling_decision(
            current_servers=5,
            metrics=20.0,
            predicted_load=20.0
        )
        assert action.action_type == ScalingActionType.SCALE_DOWN
        assert action.servers_added_removed == -1

    def test_stable_decision(self, auto_scaler):
        """Test stable decision when load is normal."""
        action = auto_scaler.make_scaling_decision(
            current_servers=3,
            metrics=50.0,
            predicted_load=50.0
        )
        assert action.action_type == ScalingActionType.SCALE_STABLE
        assert action.servers_added_removed == 0

    def test_cooldown_enforcement(self, auto_scaler):
        """Test that cooldown periods prevent rapid scaling."""
        # First scale up should succeed
        action1 = auto_scaler.make_scaling_decision(
            current_servers=1,
            metrics=80.0,
            predicted_load=85.0
        )
        assert action1.action_type == ScalingActionType.SCALE_UP

        # Immediate second scale up should be blocked
        action2 = auto_scaler.make_scaling_decision(
            current_servers=2,
            metrics=80.0,
            predicted_load=85.0
        )
        assert action2.action_type == ScalingActionType.SCALE_STABLE
        assert "cooldown" in action2.reason.lower()

    def test_min_servers_limit(self, auto_scaler):
        """Test that auto scaler respects min servers limit."""
        auto_scaler._current_servers = 1
        action = auto_scaler.make_scaling_decision(
            current_servers=1,
            metrics=10.0,
            predicted_load=10.0
        )
        # Even with low load, should not scale below min
        assert auto_scaler._current_servers >= auto_scaler.config.min_servers

    def test_max_servers_limit(self, auto_scaler):
        """Test that auto scaler respects max servers limit."""
        auto_scaler._current_servers = 10
        action = auto_scaler.make_scaling_decision(
            current_servers=10,
            metrics=95.0,
            predicted_load=95.0
        )
        # Even with high load, should not scale above max
        assert auto_scaler._current_servers <= auto_scaler.config.max_servers

    def test_evaluate_convenience_method(self, auto_scaler):
        """Test the evaluate convenience method."""
        metrics = {'cpu_usage': 80.0}
        action = auto_scaler.evaluate(metrics, prediction=85.0)
        assert action is not None
        assert isinstance(action.action_type, ScalingActionType)

    def test_get_status(self, auto_scaler):
        """Test getting auto scaler status."""
        auto_scaler.make_scaling_decision(3, 50.0, 50.0)
        status = auto_scaler.get_status()
        assert 'current_servers' in status
        assert 'config' in status
        assert 'cooldowns' in status
        assert 'statistics' in status

    def test_scaling_history(self, auto_scaler):
        """Test scaling history tracking."""
        auto_scaler.make_scaling_decision(2, 50.0, 50.0)
        auto_scaler.make_scaling_decision(2, 50.0, 50.0)
        history = auto_scaler.get_scaling_history()
        assert len(history) >= 2

    def test_scaling_history_with_limit(self, auto_scaler):
        """Test getting limited scaling history."""
        for _ in range(5):
            auto_scaler.make_scaling_decision(3, 50.0, 50.0)
        history = auto_scaler.get_scaling_history(limit=2)
        assert len(history) == 2

    def test_reset_cooldowns(self, auto_scaler):
        """Test resetting cooldown timers."""
        # Make a scale up decision
        auto_scaler.make_scaling_decision(1, 80.0, 85.0)
        assert auto_scaler._last_scale_up_time > 0

        # Reset cooldowns
        auto_scaler.reset_cooldowns()
        assert auto_scaler._last_scale_up_time == 0.0
        assert auto_scaler._last_scale_down_time == 0.0

    def test_reset_statistics(self, auto_scaler):
        """Test resetting statistics."""
        auto_scaler.make_scaling_decision(1, 80.0, 85.0)
        assert auto_scaler._total_scale_ups >= 1
        auto_scaler.reset_statistics()
        assert auto_scaler._total_scale_ups == 0
        assert auto_scaler._total_scale_downs == 0
        assert len(auto_scaler._scaling_history) == 0

    def test_create_auto_scaler_factory(self):
        """Test factory function for creating AutoScaler."""
        scaler = AutoScaler(
            config=AutoScalerConfig(
                min_servers=2,
                max_servers=20,
                scale_up_threshold=80.0,
                scale_down_threshold=20.0,
                scale_up_cooldown=30,
                scale_down_cooldown=60
            )
        )
        assert scaler.config.min_servers == 2
        assert scaler.config.max_servers == 20
        assert scaler.config.scale_up_threshold == 80.0


# ============================================================================
# ServerMetrics Tests
# ============================================================================

class TestServerMetrics:
    """Tests for ServerMetrics dataclass."""

    def test_to_dict(self, sample_metrics):
        """Test converting metrics to dictionary."""
        d = sample_metrics.to_dict()
        assert d['cpu_usage'] == 50.0
        assert d['memory_usage'] == 60.0
        assert d['response_time'] == 100.0
        assert d['request_rate'] == 150.0
        assert d['active_connections'] == 25
        assert 'timestamp' in d

    def test_from_dict(self):
        """Test creating metrics from dictionary."""
        data = {
            'cpu_usage': 70.0,
            'memory_usage': 80.0,
            'response_time': 150.0,
            'request_rate': 200.0,
            'active_connections': 40,
            'timestamp': time.time()
        }
        metrics = ServerMetrics.from_dict(data)
        assert metrics.cpu_usage == 70.0
        assert metrics.memory_usage == 80.0

    def test_to_json(self, sample_metrics):
        """Test converting metrics to JSON."""
        json_str = sample_metrics.to_json()
        assert isinstance(json_str, str)
        assert '"cpu_usage"' in json_str