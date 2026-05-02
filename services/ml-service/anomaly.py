"""
Anomaly Detection Model using Isolation Forest.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """
    Anomaly detector using Isolation Forest algorithm.

    Detects anomalous system behavior based on:
    - CPU usage
    - Memory usage
    - Response time
    - Active connections
    """

    FEATURE_NAMES = ["cpu_usage", "memory_usage", "response_time", "active_connections"]

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            n_jobs=-1
        )
        self.is_fitted = False
        self._normal_stats: Dict[str, float] = {}

    def fit(self, normal_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Fit the anomaly detector on normal data.

        Args:
            normal_data: List of data points that represent normal behavior

        Returns:
            Statistics of the training data
        """
        if len(normal_data) < 10:
            raise ValueError("Need at least 10 samples to train anomaly detector")

        # Extract features
        X = np.array([
            [d["cpu_usage"], d["memory_usage"], d["response_time"], d["active_connections"]]
            for d in normal_data
        ])

        # Fit the model
        self.model.fit(X)

        # Calculate statistics
        self._normal_stats = {
            "mean_cpu": float(np.mean(X[:, 0])),
            "mean_memory": float(np.mean(X[:, 1])),
            "mean_response_time": float(np.mean(X[:, 2])),
            "mean_connections": float(np.mean(X[:, 3])),
            "std_cpu": float(np.std(X[:, 0])),
            "std_memory": float(np.std(X[:, 1])),
            "std_response_time": float(np.std(X[:, 2])),
            "std_connections": float(np.std(X[:, 3])),
        }

        self.is_fitted = True
        return self._normal_stats

    def detect(self, features: Dict[str, Any]) -> bool:
        """
        Detect if the given features represent an anomaly.

        Args:
            features: Dictionary with cpu_usage, memory_usage, response_time, active_connections

        Returns:
            True if the data is anomalous, False otherwise
        """
        if not self.is_fitted:
            return False

        X = np.array([[
            features["cpu_usage"],
            features["memory_usage"],
            features["response_time"],
            features["active_connections"]
        ]])

        # -1 for anomaly, 1 for normal
        prediction = self.model.predict(X)
        return bool(prediction[0] == -1)

    def get_anomaly_scores(self, data: List[Dict[str, Any]]) -> List[float]:
        """
        Get anomaly scores for a batch of data points.

        Args:
            data: List of feature dictionaries

        Returns:
            List of anomaly scores (lower = more anomalous)
        """
        if not self.is_fitted or not data:
            return [0.0] * len(data) if data else []

        X = np.array([
            [d["cpu_usage"], d["memory_usage"], d["response_time"], d["active_connections"]]
            for d in data
        ])

        # Get decision function scores
        scores = self.model.decision_function(X)
        return [float(s) for s in scores]

    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata."""
        return {
            "name": "AnomalyDetector",
            "version": "1.0.0",
            "type": "IsolationForest",
            "features": self.FEATURE_NAMES,
            "contamination": self.model.contamination,
            "n_estimators": self.model.n_estimators,
            "is_fitted": self.is_fitted,
            "normal_stats": self._normal_stats
        }