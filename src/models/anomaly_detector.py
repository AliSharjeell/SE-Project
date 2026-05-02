"""Anomaly Detector for Server Metrics.

Detects abnormal behavior in server metrics using Isolation Forest or Z-Score methods.
"""

import pickle
from typing import Literal, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """Detects anomalies in server metrics using machine learning.

    Supports two detection methods:
    - Isolation Forest: Multivariate anomaly detection using random forests
    - Z-Score: Threshold-based detection using standard deviations

    Attributes:
        method: Detection method ('isolation_forest' or 'zscore')
        contamination: Expected proportion of anomalies (for Isolation Forest)
        z_threshold: Z-score threshold for flagging anomalies (for Z-Score)
    """

    SUPPORTED_METHODS = ['isolation_forest', 'zscore']

    def __init__(
        self,
        method: Literal['isolation_forest', 'zscore'] = 'isolation_forest',
        contamination: float = 0.1,
        z_threshold: float = 3.0
    ) -> None:
        """Initialize the AnomalyDetector.

        Args:
            method: Detection method to use.
            contamination: Expected proportion of anomalies (0.0 to 0.5).
                Only used for 'isolation_forest' method.
            z_threshold: Z-score threshold for flagging anomalies.
                Only used for 'zscore' method.

        Raises:
            ValueError: If method is not supported.
        """
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(
                f"Method '{method}' not supported. "
                f"Choose from: {self.SUPPORTED_METHODS}"
            )
        if not 0 < contamination <= 0.5:
            raise ValueError("Contamination must be between 0 and 0.5")
        if z_threshold <= 0:
            raise ValueError("Z-threshold must be positive")

        self.method = method
        self.contamination = contamination
        self.z_threshold = z_threshold

        # Model components (initialized during fit)
        self._model: Optional[IsolationForest] = None
        self._feature_means: Optional[pd.Series] = None
        self._feature_stds: Optional[pd.Series] = None
        self._feature_names: Optional[list] = None
        self._is_fitted: bool = False

    def fit(self, metrics_data: pd.DataFrame) -> 'AnomalyDetector':
        """Train the anomaly detector on normal behavior data.

        Args:
            metrics_data: DataFrame containing training metrics.
                Expected columns: cpu_usage, response_time, request_count, connection_count

        Returns:
            self: The fitted detector instance.

        Raises:
            ValueError: If data is empty or has insufficient samples.
        """
        if metrics_data.empty:
            raise ValueError("Training data cannot be empty")

        if len(metrics_data) < 10:
            raise ValueError(
                "Insufficient training samples. Need at least 10 samples."
            )

        # Store feature names for reference
        self._feature_names = list(metrics_data.columns)

        if self.method == 'isolation_forest':
            self._fit_isolation_forest(metrics_data)
        else:
            self._fit_zscore(metrics_data)

        self._is_fitted = True
        return self

    def _fit_isolation_forest(self, data: pd.DataFrame) -> None:
        """Fit an Isolation Forest model."""
        self._model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100
        )
        self._model.fit(data)

    def _fit_zscore(self, data: pd.DataFrame) -> None:
        """Compute statistics for Z-score method."""
        self._feature_means = data.mean()
        self._feature_stds = data.std()

        # Handle zero standard deviations
        self._feature_stds = self._feature_stds.replace(0, 1e-10)

    def detect(self, metrics: pd.DataFrame) -> np.ndarray:
        """Detect anomalies in server metrics.

        Args:
            metrics: DataFrame containing metrics to analyze.

        Returns:
            numpy.ndarray: Binary labels where 0 = normal, 1 = anomaly.

        Raises:
            RuntimeError: If detector has not been fitted.
        """
        self._ensure_fitted()

        if self.method == 'isolation_forest':
            # Isolation Forest: -1 for anomalies, 1 for normal
            labels = self._model.predict(metrics)
            return (labels == -1).astype(int)
        else:
            # Z-Score: flag if any feature exceeds threshold
            z_scores = self._compute_z_scores(metrics)
            return (z_scores.abs().max(axis=1) > self.z_threshold).astype(int)

    def get_anomaly_scores(self, metrics: pd.DataFrame) -> np.ndarray:
        """Get continuous anomaly scores for metrics.

        Args:
            metrics: DataFrame containing metrics to analyze.

        Returns:
            numpy.ndarray: Anomaly scores (higher = more anomalous).

        Raises:
            RuntimeError: If detector has not been fitted.
        """
        self._ensure_fitted()

        if self.method == 'isolation_forest':
            # sklearn returns negative scores; more negative = more anomalous
            # Convert to positive scale for consistency
            raw_scores = self._model.score_samples(metrics)
            return -raw_scores
        else:
            # Z-Score: max absolute z-score per sample
            z_scores = self._compute_z_scores(metrics)
            return z_scores.abs().max(axis=1).values

    def get_anomaly_details(
        self,
        metrics: pd.DataFrame
    ) -> list[dict]:
        """Get detailed anomaly information with feature contributions.

        Args:
            metrics: DataFrame containing metrics to analyze.

        Returns:
            list[dict]: List of anomaly details for each sample.
                Each dict contains:
                - index: Row index in the original DataFrame
                - is_anomaly: Boolean indicating if sample is anomalous
                - score: Continuous anomaly score
                - feature_contributions: Dict mapping feature names to
                  their z-score contributions
                - top_contributing_features: List of feature names sorted
                  by contribution magnitude

        Raises:
            RuntimeError: If detector has not been fitted.
        """
        self._ensure_fitted()

        labels = self.detect(metrics)
        scores = self.get_anomaly_scores(metrics)
        z_scores = self._compute_z_scores(metrics)

        results = []
        for idx in range(len(metrics)):
            feature_contributions = {
                feat: float(z_scores.iloc[idx][feat])
                for feat in self._feature_names
            }

            # Sort features by absolute contribution
            sorted_features = sorted(
                feature_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            top_features = [f[0] for f in sorted_features[:3]]

            results.append({
                'index': int(metrics.index[idx]),
                'is_anomaly': bool(labels[idx]),
                'score': float(scores[idx]),
                'feature_contributions': feature_contributions,
                'top_contributing_features': top_features
            })

        return results

    def _compute_z_scores(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute Z-scores for the given data."""
        z_scores = (data - self._feature_means) / self._feature_stds
        return z_scores

    def _ensure_fitted(self) -> None:
        """Ensure the detector has been fitted before use."""
        if not self._is_fitted:
            raise RuntimeError(
                "Detector has not been fitted. Call fit() first."
            )

    def save_model(self, path: str) -> None:
        """Save the trained model to disk.

        Args:
            path: File path to save the model.

        Raises:
            RuntimeError: If detector has not been fitted.
        """
        self._ensure_fitted()

        state = {
            'method': self.method,
            'contamination': self.contamination,
            'z_threshold': self.z_threshold,
            'model': self._model,
            'feature_means': self._feature_means,
            'feature_stds': self._feature_stds,
            'feature_names': self._feature_names,
            'is_fitted': self._is_fitted
        }

        with open(path, 'wb') as f:
            pickle.dump(state, f)

    def load_model(self, path: str) -> 'AnomalyDetector':
        """Load a trained model from disk.

        Args:
            path: File path to load the model from.

        Returns:
            self: The loaded detector instance.

        Raises:
            FileNotFoundError: If model file does not exist.
        """
        with open(path, 'rb') as f:
            state = pickle.load(f)

        self.method = state['method']
        self.contamination = state['contamination']
        self.z_threshold = state['z_threshold']
        self._model = state['model']
        self._feature_means = state['feature_means']
        self._feature_stds = state['feature_stds']
        self._feature_names = state['feature_names']
        self._is_fitted = state['is_fitted']

        return self

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance scores (Z-score method only).

        Returns:
            dict: Feature names mapped to their importance scores
                  (based on standard deviation of training data).

        Raises:
            RuntimeError: If method is not 'zscore' or not fitted.
        """
        self._ensure_fitted()

        if self.method != 'zscore':
            raise RuntimeError(
                "Feature importance is only available for Z-score method"
            )

        # Use inverse of coefficient of variation as importance
        importance = {}
        for feat in self._feature_names:
            mean = self._feature_means[feat]
            std = self._feature_stds[feat]
            if mean != 0:
                importance[feat] = float(std / abs(mean))
            else:
                importance[feat] = float(std)

        # Normalize to sum to 1
        total = sum(importance.values())
        return {k: v / total for k, v in importance.items()}

    def __repr__(self) -> str:
        """Return string representation of the detector."""
        return (
            f"AnomalyDetector("
            f"method='{self.method}', "
            f"fitted={self._is_fitted})"
        )
