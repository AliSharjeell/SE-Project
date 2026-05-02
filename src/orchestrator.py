"""
System Orchestrator for AI-Driven Infrastructure Manager.

This module provides the InfrastructureOrchestrator class that coordinates
all system components including TrafficGenerator, MonitoringSystem,
LoadBalancer, AutoScaler, and AI Prediction modules.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from src.components.auto_scaler import (
    AutoScaler,
    AutoScalerConfig,
    ScalingAction,
)
from src.components.load_balancer import (
    BackendServer,
    LoadBalancer,
    LoadBalancerStrategy,
)
from src.components.monitor import MonitoringSystem, ServerMetrics
from src.components.traffic_generator import Request, TrafficGenerator
from src.models.anomaly_detector import AnomalyDetector
from src.models.traffic_predictor import TrafficPredictor


@dataclass
class IterationResult:
    """Results from a single simulation iteration."""

    iteration: int
    timestamp: float
    request: Optional[Request]
    metrics: Optional[ServerMetrics]
    route_decision: Optional[str]
    scaling_action: Optional[ScalingAction]
    anomaly_detected: bool
    anomaly_score: float
    prediction: float
    error: Optional[str] = None


@dataclass
class SystemStatus:
    """Current status of the entire system."""

    is_running: bool
    is_initialized: bool
    iteration: int
    timestamp: str
    traffic_generator: dict
    monitoring: dict
    load_balancer: dict
    auto_scaler: dict
    predictor_trained: bool
    anomaly_detector_trained: bool


class InfrastructureOrchestrator:
    """
    Main orchestrator that coordinates all infrastructure management components.

    This class manages the simulation lifecycle, coordinating:
    - Traffic generation for load testing
    - Real-time monitoring of system metrics
    - Load balancing across backend servers
    - Predictive auto-scaling based on AI analysis
    - Anomaly detection for security and reliability

    Attributes:
        config_path: Path to the YAML configuration file.
        logger: Logger instance for the orchestrator.
    """

    DEFAULT_CONFIG: dict = {
        "orchestrator": {
            "simulation": {
                "interval_seconds": 1.0,
                "max_iterations": 100,
                "scenario": "normal",
            }
        },
        "traffic_generator": {
            "base_rate": 10,
            "max_rate": 100,
            "duration": 60.0,
        },
        "monitoring": {"history_size": 1000, "collection_interval": 1.0},
        "load_balancer": {"max_history": 1000, "default_strategy": "ai_powered"},
        "auto_scaler": {
            "min_servers": 1,
            "max_servers": 10,
            "scale_up_threshold": 70.0,
            "scale_down_threshold": 30.0,
            "scale_up_cooldown": 60,
            "scale_down_cooldown": 120,
        },
        "ai_prediction": {
            "predictor": {"n_estimators": 100, "confidence_level": 0.95},
            "anomaly_detector": {"method": "isolation_forest", "contamination": 0.1},
        },
        "logging": {"level": "INFO"},
    }

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize the InfrastructureOrchestrator.

        Args:
            config_path: Path to the YAML configuration file. If None,
                        uses default config or looks for configs/config.yaml.
        """
        self._config: dict = {}
        self._traffic_generator: Optional[TrafficGenerator] = None
        self._monitoring_system: Optional[MonitoringSystem] = None
        self._load_balancer: Optional[LoadBalancer] = None
        self._auto_scaler: Optional[AutoScaler] = None
        self._traffic_predictor: Optional[TrafficPredictor] = None
        self._anomaly_detector: Optional[AnomalyDetector] = None

        self._is_initialized: bool = False
        self._is_running: bool = False
        self._current_iteration: int = 0
        self._iteration_results: list[IterationResult] = []

        # Setup logger
        self._logger: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

        # Load configuration
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[str] = None) -> None:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file. If None, searches for default locations.
        """
        if config_path is None:
            possible_paths = [
                Path("configs/config.yaml"),
                Path("C:/AppsNew/SE Project/configs/config.yaml"),
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f)
                self._logger.info(f"Loaded configuration from: {config_path}")
            except Exception as e:
                self._logger.warning(f"Failed to load config: {e}. Using defaults.")
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            self._logger.info("No config file found. Using default configuration.")
            self._config = self.DEFAULT_CONFIG.copy()

    def _setup_logging(self) -> None:
        """Configure logging based on configuration."""
        log_config = self._config.get("logging", {})
        level_name = log_config.get("level", "INFO")
        log_format = log_config.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        level = getattr(logging, level_name.upper(), logging.INFO)
        logging.basicConfig(level=level, format=log_format)

    def initialize(self) -> None:
        """
        Initialize all system components.

        Sets up TrafficGenerator, MonitoringSystem, LoadBalancer, AutoScaler,
        TrafficPredictor, and AnomalyDetector with configuration values.
        """
        if self._is_initialized:
            self._logger.warning("System already initialized. Skipping.")
            return

        self._logger.info("Initializing Infrastructure Orchestrator...")

        try:
            # Initialize Traffic Generator
            tg_config = self._config.get("traffic_generator", {})
            self._traffic_generator = TrafficGenerator(
                base_rate=tg_config.get("base_rate", 10),
                max_rate=tg_config.get("max_rate", 100),
                duration=tg_config.get("duration", 60.0),
            )
            self._logger.info(f"TrafficGenerator initialized with base_rate={tg_config.get('base_rate', 10)}")

            # Initialize Monitoring System
            mon_config = self._config.get("monitoring", {})
            self._monitoring_system = MonitoringSystem(
                history_size=mon_config.get("history_size", 1000)
            )
            self._logger.info(f"MonitoringSystem initialized with history_size={mon_config.get('history_size', 1000)}")

            # Initialize Load Balancer
            lb_config = self._config.get("load_balancer", {})
            self._load_balancer = LoadBalancer(
                max_history=lb_config.get("max_history", 1000)
            )
            self._logger.info("LoadBalancer initialized")

            # Add default servers to load balancer
            self._add_default_servers()

            # Initialize AutoScaler
            as_config = self._config.get("auto_scaler", {})
            auto_scaler_config = AutoScalerConfig(
                min_servers=as_config.get("min_servers", 1),
                max_servers=as_config.get("max_servers", 10),
                scale_up_threshold=as_config.get("scale_up_threshold", 70.0),
                scale_down_threshold=as_config.get("scale_down_threshold", 30.0),
                scale_up_cooldown=as_config.get("scale_up_cooldown", 60),
                scale_down_cooldown=as_config.get("scale_down_cooldown", 120),
            )
            self._auto_scaler = AutoScaler(config=auto_scaler_config)
            self._logger.info("AutoScaler initialized")

            # Initialize AI Prediction Components
            ai_config = self._config.get("ai_prediction", {})

            # Traffic Predictor
            pred_config = ai_config.get("predictor", {})
            self._traffic_predictor = TrafficPredictor(
                n_estimators=pred_config.get("n_estimators", 100),
                confidence_level=pred_config.get("confidence_level", 0.95),
            )
            self._logger.info("TrafficPredictor initialized")

            # Anomaly Detector
            anom_config = ai_config.get("anomaly_detector", {})
            self._anomaly_detector = AnomalyDetector(
                method=anom_config.get("method", "isolation_forest"),
                contamination=anom_config.get("contamination", 0.1),
                z_threshold=anom_config.get("z_threshold", 3.0),
            )
            self._logger.info("AnomalyDetector initialized")

            self._is_initialized = True
            self._logger.info("Infrastructure Orchestrator initialized successfully")

        except Exception as e:
            self._logger.error(f"Failed to initialize orchestrator: {e}")
            raise

    def _add_default_servers(self) -> None:
        """Add default backend servers to the load balancer."""
        default_servers = [
            BackendServer(id="server-1", host="192.168.1.10", port=8001),
            BackendServer(id="server-2", host="192.168.1.11", port=8002),
            BackendServer(id="server-3", host="192.168.1.12", port=8003),
        ]
        for server in default_servers:
            self._load_balancer.add_server(server)
        self._logger.info(f"Added {len(default_servers)} default servers to load balancer")

    def start(self) -> None:
        """
        Begin the simulation loop.

        Runs iterations based on configuration until max_iterations reached
        or stop() is called.
        """
        if not self._is_initialized:
            self.initialize()

        if self._is_running:
            self._logger.warning("Simulation already running. Skipping.")
            return

        self._logger.info("Starting simulation loop...")
        self._is_running = True

        sim_config = self._config.get("orchestrator", {}).get("simulation", {})
        max_iterations = sim_config.get("max_iterations", 100)
        interval = sim_config.get("interval_seconds", 1.0)

        try:
            while self._is_running and self._current_iteration < max_iterations:
                try:
                    self.run_iteration()
                    time.sleep(interval)
                except Exception as e:
                    self._logger.error(f"Error in iteration {self._current_iteration}: {e}")
                    # Continue running despite errors
                    self._iteration_results.append(
                        IterationResult(
                            iteration=self._current_iteration,
                            timestamp=time.time(),
                            request=None,
                            metrics=None,
                            route_decision=None,
                            scaling_action=None,
                            anomaly_detected=False,
                            anomaly_score=0.0,
                            prediction=0.0,
                            error=str(e),
                        )
                    )
                    time.sleep(interval)

            self._logger.info(f"Simulation completed after {self._current_iteration} iterations")

        except KeyboardInterrupt:
            self._logger.info("Simulation interrupted by user")
        finally:
            self._is_running = False

    def stop(self) -> None:
        """Gracefully shutdown the simulation."""
        self._logger.info("Stopping Infrastructure Orchestrator...")
        self._is_running = False

        # Stop monitoring collection if active
        if self._monitoring_system:
            self._monitoring_system.stop_collection()

        self._logger.info("Infrastructure Orchestrator stopped")

    def run_iteration(self) -> IterationResult:
        """
        Execute a single simulation iteration.

        Performs the following steps:
        1. Generate traffic request
        2. Collect metrics from monitoring system
        3. Detect anomalies in metrics
        4. Make traffic predictions (if trained)
        5. Route request via load balancer
        6. Evaluate and apply scaling decisions

        Returns:
            IterationResult containing all actions and decisions from this iteration.
        """
        self._current_iteration += 1
        iteration_start = time.time()
        result = IterationResult(
            iteration=self._current_iteration,
            timestamp=iteration_start,
            request=None,
            metrics=None,
            route_decision=None,
            scaling_action=None,
            anomaly_detected=False,
            anomaly_score=0.0,
            prediction=0.0,
        )

        try:
            # Step 1: Generate Traffic
            self._logger.debug(f"[Iteration {self._current_iteration}] Generating traffic...")
            result.request = self._traffic_generator.generate_request()
            self._logger.info(f"Generated request: {result.request.request_id}")

            # Step 2: Collect Metrics
            self._logger.debug("Collecting metrics...")
            metrics = self._monitoring_system.generate_simulated_metric()
            self._monitoring_system.add_metric(metrics)
            result.metrics = metrics
            self._logger.info(
                f"Metrics: CPU={metrics.cpu_usage:.1f}%, Memory={metrics.memory_usage:.1f}%, "
                f"Response={metrics.response_time:.1f}ms, Requests={metrics.request_rate:.0f}/s"
            )

            # Step 3: Anomaly Detection
            self._logger.debug("Running anomaly detection...")
            anomaly_detected, anomaly_score = self._detect_anomalies(metrics)
            result.anomaly_detected = anomaly_detected
            result.anomaly_score = anomaly_score
            if anomaly_detected:
                self._logger.warning(
                    f"Anomaly detected! Score: {anomaly_score:.3f}"
                )

            # Step 4: Traffic Prediction
            self._logger.debug("Making traffic predictions...")
            prediction = self._predict_traffic()
            result.prediction = prediction
            self._logger.info(f"Predicted load: {prediction:.1f}%")

            # Step 5: Route Request
            self._logger.debug("Routing request...")
            route_result = self._route_request()
            result.route_decision = route_result
            self._logger.info(f"Request routed to: {route_result}")

            # Step 6: Scaling Decision
            self._logger.debug("Evaluating scaling decision...")
            scaling_action = self._evaluate_scaling(metrics, prediction)
            result.scaling_action = scaling_action
            self._logger.info(
                f"Scaling action: {scaling_action.action_type.value} "
                f"({scaling_action.servers_added_removed:+d} servers) - {scaling_action.reason}"
            )

        except Exception as e:
            result.error = str(e)
            self._logger.error(f"Error in iteration {self._current_iteration}: {e}")

        # Store result
        self._iteration_results.append(result)

        # Keep history manageable
        if len(self._iteration_results) > 1000:
            self._iteration_results = self._iteration_results[-1000:]

        return result

    def _detect_anomalies(self, metrics: ServerMetrics) -> tuple[bool, float]:
        """
        Detect anomalies in server metrics.

        Args:
            metrics: ServerMetrics to analyze.

        Returns:
            Tuple of (anomaly_detected, anomaly_score).
        """
        # Check if detector is trained
        if self._anomaly_detector is None:
            return False, 0.0

        try:
            # Create DataFrame for detector
            import pandas as pd

            metric_data = pd.DataFrame(
                [
                    {
                        "cpu_usage": metrics.cpu_usage,
                        "memory_usage": metrics.memory_usage,
                        "response_time": metrics.response_time,
                        "request_rate": metrics.request_rate,
                        "active_connections": metrics.active_connections,
                    }
                ]
            )

            # Fit detector if not already (initial learning)
            if not hasattr(self._anomaly_detector, "_is_fitted") or not self._anomaly_detector._is_fitted:
                # Generate some training data
                history = self._monitoring_system.get_history(limit=20)
                if len(history) >= 10:
                    training_data = pd.DataFrame(
                        [
                            {
                                "cpu_usage": m.cpu_usage,
                                "memory_usage": m.memory_usage,
                                "response_time": m.response_time,
                                "request_rate": m.request_rate,
                                "active_connections": m.active_connections,
                            }
                            for m in history
                        ]
                    )
                    self._anomaly_detector.fit(training_data)

            # Detect anomalies
            scores = self._anomaly_detector.get_anomaly_scores(metric_data)
            score = float(scores[0]) if len(scores) > 0 else 0.0

            # Threshold for anomaly detection
            threshold = 0.5
            anomaly_detected = score > threshold

            return anomaly_detected, score

        except Exception as e:
            self._logger.debug(f"Anomaly detection skipped: {e}")
            return False, 0.0

    def _predict_traffic(self) -> float:
        """
        Make traffic predictions based on history.

        Returns:
            Predicted load value (0-100 scale).
        """
        if self._traffic_predictor is None:
            return 50.0  # Default moderate load

        try:
            # Get recent history for prediction
            history = self._monitoring_system.get_history(limit=30)
            if len(history) < 10:
                return 50.0

            import pandas as pd

            # Prepare data for predictor
            historical_data = pd.DataFrame(
                [
                    {
                        "timestamp": datetime.fromtimestamp(m.timestamp),
                        "request_count": m.request_rate,
                    }
                    for m in history
                ]
            )

            # Train predictor if not trained
            if not hasattr(self._traffic_predictor, "_is_trained") or not self._traffic_predictor._is_trained:
                self._traffic_predictor.train(historical_data)

            # Make prediction
            predictions, _, _ = self._traffic_predictor.predict_with_history(
                historical_data, next_steps=1
            )
            predicted_rate = float(predictions[0]) if len(predictions) > 0 else 100.0

            # Convert to CPU percentage estimate (simplified model)
            # Higher request rate suggests higher CPU utilization
            predicted_load = min(100.0, (predicted_rate / 500.0) * 100.0)

            return predicted_load

        except Exception as e:
            self._logger.debug(f"Traffic prediction skipped: {e}")
            # Fall back to current CPU as prediction
            latest = self._monitoring_system.get_latest()
            if latest:
                return latest.cpu_usage
            return 50.0

    def _route_request(self) -> str:
        """
        Route the current request through the load balancer.

        Returns:
            Server ID that received the request.
        """
        if self._load_balancer is None or self._load_balancer.server_count == 0:
            return "no-servers"

        try:
            # Get prediction scores for AI-powered routing
            scores = self._get_server_health_scores()

            # Determine strategy from config
            lb_config = self._config.get("load_balancer", {})
            strategy_name = lb_config.get("default_strategy", "ai_powered")

            strategy = LoadBalancerStrategy.AI_POWERED
            if strategy_name == "round_robin":
                strategy = LoadBalancerStrategy.ROUND_ROBIN
            elif strategy_name == "least_connections":
                strategy = LoadBalancerStrategy.LEAST_CONNECTIONS

            # Route request
            server = self._load_balancer.route_request(strategy, scores)
            return server.id

        except Exception as e:
            self._logger.error(f"Routing failed: {e}")
            return "routing-error"

    def _get_server_health_scores(self) -> dict[str, float]:
        """
        Calculate health scores for each server based on recent metrics.

        Returns:
            Dictionary mapping server_id to health score (0-1).
        """
        scores: dict[str, float] = {}
        servers = self._load_balancer.get_all_servers()

        for server in servers:
            # Simple health model: lower CPU = healthier
            # In production, would use more sophisticated metrics
            health_score = max(0.0, 1.0 - (server.cpu_usage / 100.0))
            scores[server.id] = health_score

        return scores

    def _evaluate_scaling(self, metrics: ServerMetrics, prediction: float) -> ScalingAction:
        """
        Evaluate and apply scaling decisions.

        Args:
            metrics: Current server metrics.
            prediction: Predicted future load.

        Returns:
            ScalingAction that was applied.
        """
        if self._auto_scaler is None:
            return ScalingAction(
                action_type="scale_stable",
                servers_added_removed=0,
                reason="AutoScaler not initialized",
                timestamp=time.time(),
            )

        try:
            # Get current number of servers from load balancer
            current_servers = self._load_balancer.server_count if self._load_balancer else 1

            # Make scaling decision
            metrics_dict = {
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "response_time": metrics.response_time,
            }

            action = self._auto_scaler.evaluate(metrics_dict, prediction)

            # Apply scaling action to load balancer
            if action.servers_added_removed > 0:
                self._add_server()
            elif action.servers_added_removed < 0:
                self._remove_server()

            return action

        except Exception as e:
            self._logger.error(f"Scaling evaluation failed: {e}")
            return ScalingAction(
                action_type="scale_stable",
                servers_added_removed=0,
                reason=f"Error: {e}",
                timestamp=time.time(),
            )

    def _add_server(self) -> bool:
        """Add a new server to the load balancer."""
        if self._load_balancer is None:
            return False

        try:
            # Generate a new server ID
            existing_ids = [s.id for s in self._load_balancer.get_all_servers()]
            new_id = f"server-{len(existing_ids) + 1}"

            # Avoid duplicates
            counter = 1
            while new_id in existing_ids:
                counter += 1
                new_id = f"server-{len(existing_ids) + counter}"

            new_server = BackendServer(
                id=new_id,
                host=f"192.168.1.{100 + len(existing_ids)}",
                port=8000 + len(existing_ids) + 1,
            )

            success = self._load_balancer.add_server(new_server)
            if success:
                self._logger.info(f"Added new server: {new_id}")
            return success

        except Exception as e:
            self._logger.error(f"Failed to add server: {e}")
            return False

    def _remove_server(self) -> bool:
        """Remove a server from the load balancer."""
        if self._load_balancer is None or self._load_balancer.server_count <= 1:
            return False

        try:
            # Remove the last server
            servers = self._load_balancer.get_all_servers()
            if servers:
                server_to_remove = servers[-1]
                success = self._load_balancer.remove_server(server_to_remove.id)
                if success:
                    self._logger.info(f"Removed server: {server_to_remove.id}")
                return success
            return False

        except Exception as e:
            self._logger.error(f"Failed to remove server: {e}")
            return False

    def get_system_status(self) -> SystemStatus:
        """
        Get the current status of the entire system.

        Returns:
            SystemStatus containing state of all components.
        """
        return SystemStatus(
            is_running=self._is_running,
            is_initialized=self._is_initialized,
            iteration=self._current_iteration,
            timestamp=datetime.now().isoformat(),
            traffic_generator={
                "request_count": self._traffic_generator.request_count
                if self._traffic_generator
                else 0,
                "base_rate": self._traffic_generator.base_rate
                if self._traffic_generator
                else 0,
                "max_rate": self._traffic_generator.max_rate
                if self._traffic_generator
                else 0,
            },
            monitoring={
                "samples_collected": self._monitoring_system.history_count
                if self._monitoring_system
                else 0,
                "history_size": self._monitoring_system.history_size
                if self._monitoring_system
                else 0,
            },
            load_balancer={
                "server_count": self._load_balancer.server_count
                if self._load_balancer
                else 0,
                "routing_history_count": self._load_balancer.history_count
                if self._load_balancer
                else 0,
            },
            auto_scaler=self._auto_scaler.get_status()
            if self._auto_scaler
            else {},
            predictor_trained=getattr(self._traffic_predictor, "_is_trained", False)
            if self._traffic_predictor
            else False,
            anomaly_detector_trained=getattr(self._anomaly_detector, "_is_fitted", False)
            if self._anomaly_detector
            else False,
        )

    def get_metrics_history(self, limit: Optional[int] = None) -> list[dict]:
        """
        Get the collected metrics history.

        Args:
            limit: Maximum number of entries to return. If None, returns all.

        Returns:
            List of metric dictionaries.
        """
        if self._monitoring_system is None:
            return []

        return self._monitoring_system.get_history_dicts(limit)

    def get_iteration_results(self, limit: Optional[int] = None) -> list[dict]:
        """
        Get the iteration results history.

        Args:
            limit: Maximum number of entries to return. If None, returns all.

        Returns:
            List of iteration result dictionaries.
        """
        results = self._iteration_results
        if limit:
            results = results[-limit:]

        return [
            {
                "iteration": r.iteration,
                "timestamp": r.timestamp,
                "request_id": r.request.request_id if r.request else None,
                "metrics": r.metrics.to_dict() if r.metrics else None,
                "route_decision": r.route_decision,
                "scaling_action": r.scaling_action.to_dict() if r.scaling_action else None,
                "anomaly_detected": r.anomaly_detected,
                "anomaly_score": r.anomaly_score,
                "prediction": r.prediction,
                "error": r.error,
            }
            for r in results
        ]

    def reset(self) -> None:
        """Reset the orchestrator to its initial state."""
        self._logger.info("Resetting Infrastructure Orchestrator...")

        self._is_running = False
        self._current_iteration = 0
        self._iteration_results.clear()

        if self._traffic_generator:
            self._traffic_generator.reset_count()

        if self._monitoring_system:
            self._monitoring_system.clear_history()

        if self._auto_scaler:
            self._auto_scaler.reset_statistics()
            self._auto_scaler.reset_cooldowns()

        self._logger.info("Infrastructure Orchestrator reset complete")

    def __enter__(self) -> "InfrastructureOrchestrator":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()