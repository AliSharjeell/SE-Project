"""
Unit tests for ML Models.

Tests TrafficPredictor and AnomalyDetector models.
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.traffic_predictor import TrafficPredictor
from models.anomaly_detector import AnomalyDetector


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_traffic_data():
    """Create sample traffic data for training and testing."""
    # Create 100 data points over 100 minutes
    np.random.seed(42)
    n_points = 100

    base_time = datetime(2024, 1, 1, 0, 0)
    timestamps = [base_time + timedelta(minutes=i) for i in range(n_points)]

    # Generate realistic traffic with daily patterns
    hours = np.array([ts.hour for ts in timestamps])
    base_traffic = 100 + 50 * np.sin(2 * np.pi * hours / 24)

    # Add some noise
    noise = np.random.normal(0, 10, n_points)

    # Add some trend
    trend = np.linspace(0, 20, n_points)

    request_counts = np.maximum(0, base_traffic + noise + trend).astype(int)

    return pd.DataFrame({
        'timestamp': timestamps,
        'request_count': request_counts,
        'cpu_usage': np.random.uniform(30, 70, n_points),
        'memory_usage': np.random.uniform(40, 80, n_points),
        'response_time': np.random.uniform(50, 150, n_points)
    })


@pytest.fixture
def trained_traffic_predictor(sample_traffic_data):
    """Create a trained TrafficPredictor."""
    predictor = TrafficPredictor(n_estimators=10, random_state=42)
    predictor.train(sample_traffic_data)
    return predictor


@pytest.fixture
def sample_metrics_data():
    """Create sample metrics data for anomaly detection."""
    # Normal metrics with some variation
    np.random.seed(42)
    n_normal = 100

    data = {
        'cpu_usage': np.random.normal(50, 10, n_normal),
        'response_time': np.random.normal(100, 20, n_normal),
        'request_count': np.random.normal(150, 30, n_normal),
        'connection_count': np.random.normal(50, 10, n_normal)
    }

    return pd.DataFrame(data)


@pytest.fixture
def trained_anomaly_detector(sample_metrics_data):
    """Create a trained AnomalyDetector."""
    detector = AnomalyDetector(method='isolation_forest', contamination=0.1)
    detector.fit(sample_metrics_data)
    return detector


# ============================================================================
# TrafficPredictor Tests
# ============================================================================

class TestTrafficPredictor:
    """Tests for TrafficPredictor model."""

    def test_initialization(self):
        """Test TrafficPredictor initializes correctly."""
        predictor = TrafficPredictor(n_estimators=50, confidence_level=0.95)
        assert predictor.n_estimators == 50
        assert predictor.confidence_level == 0.95
        assert predictor.random_state == 42
        assert predictor._is_trained is False

    def test_train_success(self, sample_traffic_data):
        """Test training the predictor successfully."""
        predictor = TrafficPredictor(n_estimators=10, random_state=42)
        result = predictor.train(sample_traffic_data)
        assert result is predictor  # Should return self
        assert predictor._is_trained is True

    def test_train_missing_columns(self):
        """Test training fails with missing required columns."""
        predictor = TrafficPredictor()
        invalid_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'cpu_usage': [50.0]  # Missing request_count
        })
        with pytest.raises(ValueError, match="Missing required columns"):
            predictor.train(invalid_data)

    def test_train_insufficient_data(self):
        """Test training fails with insufficient data."""
        predictor = TrafficPredictor()
        small_data = pd.DataFrame({
            'timestamp': [datetime.now()] * 5,
            'request_count': [100] * 5
        })
        with pytest.raises(ValueError, match="Insufficient data"):
            predictor.train(small_data)

    def test_predict_without_training(self):
        """Test predict raises error when not trained."""
        predictor = TrafficPredictor()
        with pytest.raises(RuntimeError, match="not been trained"):
            predictor.predict(5)

    def test_predict_with_history(self, trained_traffic_predictor, sample_traffic_data):
        """Test prediction with historical data."""
        predictions, lower, upper = trained_traffic_predictor.predict_with_history(
            sample_traffic_data.tail(20),
            next_steps=5
        )
        assert len(predictions) == 5
        assert len(lower) == 5
        assert len(upper) == 5
        # Predictions should be non-negative
        assert all(p >= 0 for p in predictions)
        # Lower bound should be <= predictions
        assert all(l <= p for l, p in zip(lower, predictions))
        # Upper bound should be >= predictions
        assert all(u >= p for u, p in zip(upper, predictions))

    def test_feature_creation(self, trained_traffic_predictor, sample_traffic_data):
        """Test that features are created correctly."""
        features_df = trained_traffic_predictor._create_features(sample_traffic_data)

        # Check time-based features
        assert 'hour_of_day' in features_df.columns
        assert 'day_of_week' in features_df.columns
        assert 'is_weekend' in features_df.columns

        # Check cyclical features
        assert 'hour_sin' in features_df.columns
        assert 'hour_cos' in features_df.columns

        # Check lag features
        assert 'lag_1' in features_df.columns
        assert 'lag_7' in features_df.columns

        # Check rolling features
        assert 'rolling_mean_3' in features_df.columns
        assert 'rolling_mean_10' in features_df.columns
        assert 'rolling_std_3' in features_df.columns

    def test_feature_importance(self, trained_traffic_predictor):
        """Test getting feature importance scores."""
        importance = trained_traffic_predictor.get_feature_importance()
        assert isinstance(importance, dict)
        assert len(importance) > 0
        # Feature names should be present
        assert 'hour_of_day' in importance or 'lag_1' in importance
        # All values should be positive
        assert all(v >= 0 for v in importance.values())
        # Sum should be approximately 1
        assert abs(sum(importance.values()) - 1.0) < 0.01

    def test_confidence_score(self, trained_traffic_predictor):
        """Test confidence score calculation."""
        score = trained_traffic_predictor.get_confidence_score(100.0)
        assert 0 <= score <= 1

    def test_confidence_score_untrained(self):
        """Test confidence score returns 0 for untrained model."""
        predictor = TrafficPredictor()
        score = predictor.get_confidence_score(100.0)
        assert score == 0.0


# ============================================================================
# AnomalyDetector Tests
# ============================================================================

class TestAnomalyDetector:
    """Tests for AnomalyDetector model."""

    def test_initialization(self):
        """Test AnomalyDetector initializes correctly."""
        detector = AnomalyDetector(method='zscore', z_threshold=2.5)
        assert detector.method == 'zscore'
        assert detector.z_threshold == 2.5
        assert detector._is_fitted is False

    def test_supported_methods(self):
        """Test supported detection methods."""
        assert 'isolation_forest' in AnomalyDetector.SUPPORTED_METHODS
        assert 'zscore' in AnomalyDetector.SUPPORTED_METHODS

    def test_invalid_method(self):
        """Test initialization with invalid method raises error."""
        with pytest.raises(ValueError, match="not supported"):
            AnomalyDetector(method='invalid_method')

    def test_invalid_contamination(self):
        """Test initialization with invalid contamination raises error."""
        with pytest.raises(ValueError, match="Contamination"):
            AnomalyDetector(contamination=0.6)
        with pytest.raises(ValueError, match="Contamination"):
            AnomalyDetector(contamination=0.0)

    def test_invalid_z_threshold(self):
        """Test initialization with invalid z_threshold raises error."""
        with pytest.raises(ValueError, match="positive"):
            AnomalyDetector(method='zscore', z_threshold=0)

    def test_fit_isolation_forest(self, sample_metrics_data):
        """Test fitting with Isolation Forest."""
        detector = AnomalyDetector(method='isolation_forest', contamination=0.1)
        result = detector.fit(sample_metrics_data)
        assert result is detector  # Should return self
        assert detector._is_fitted is True
        assert detector._model is not None

    def test_fit_zscore(self, sample_metrics_data):
        """Test fitting with Z-score method."""
        detector = AnomalyDetector(method='zscore', z_threshold=3.0)
        detector.fit(sample_metrics_data)
        assert detector._is_fitted is True
        assert detector._feature_means is not None
        assert detector._feature_stds is not None

    def test_fit_empty_data(self):
        """Test fitting with empty data raises error."""
        detector = AnomalyDetector()
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError, match="Training data cannot be empty"):
            detector.fit(empty_df)

    def test_fit_insufficient_samples(self):
        """Test fitting with insufficient samples raises error."""
        detector = AnomalyDetector()
        small_data = pd.DataFrame({
            'cpu_usage': [50, 60, 70],
            'response_time': [100, 110, 120]
        })
        with pytest.raises(ValueError, match="Insufficient training samples"):
            detector.fit(small_data)

    def test_detect_without_fit(self):
        """Test detect raises error when not fitted."""
        detector = AnomalyDetector()
        test_data = pd.DataFrame({
            'cpu_usage': [50],
            'response_time': [100]
        })
        with pytest.raises(RuntimeError, match="not been fitted"):
            detector.detect(test_data)

    def test_detect_isolation_forest(self, trained_anomaly_detector, sample_metrics_data):
        """Test anomaly detection with Isolation Forest."""
        # Test on training data (should detect some anomalies)
        labels = trained_anomaly_detector.detect(sample_metrics_data)
        assert len(labels) == len(sample_metrics_data)
        assert labels.dtype == np.int64
        # Labels should be 0 (normal) or 1 (anomaly)
        assert set(labels).issubset({0, 1})

    def test_detect_zscore(self, sample_metrics_data):
        """Test anomaly detection with Z-score method."""
        detector = AnomalyDetector(method='zscore', z_threshold=3.0)
        detector.fit(sample_metrics_data)
        labels = detector.detect(sample_metrics_data)
        assert len(labels) == len(sample_metrics_data)
        assert labels.dtype == np.int64

    def test_get_anomaly_scores(self, trained_anomaly_detector, sample_metrics_data):
        """Test getting anomaly scores."""
        scores = trained_anomaly_detector.get_anomaly_scores(sample_metrics_data)
        assert len(scores) == len(sample_metrics_data)
        assert scores.dtype == np.float64
        # Scores should be non-negative
        assert all(s >= 0 for s in scores)

    def test_get_anomaly_details(self, sample_metrics_data):
        """Test getting detailed anomaly information."""
        # get_anomaly_details only works with zscore method
        detector = AnomalyDetector(method='zscore', z_threshold=3.0)
        detector.fit(sample_metrics_data)
        details = detector.get_anomaly_details(sample_metrics_data)
        assert len(details) == len(sample_metrics_data)

        # Check structure of first detail
        first = details[0]
        assert 'index' in first
        assert 'is_anomaly' in first
        assert 'score' in first
        assert 'feature_contributions' in first
        assert 'top_contributing_features' in first

    def test_compute_z_scores(self, sample_metrics_data):
        """Test Z-score computation."""
        detector = AnomalyDetector(method='zscore')
        detector.fit(sample_metrics_data)

        z_scores = detector._compute_z_scores(sample_metrics_data.head())
        assert z_scores is not None
        assert len(z_scores) == 5

    def test_feature_importance_zscore(self, sample_metrics_data):
        """Test feature importance for Z-score method."""
        detector = AnomalyDetector(method='zscore')
        detector.fit(sample_metrics_data)

        importance = detector.get_feature_importance()
        assert isinstance(importance, dict)
        assert len(importance) == len(sample_metrics_data.columns)
        # Values should be positive
        assert all(v >= 0 for v in importance.values())

    def test_feature_importance_invalid_method(self, sample_metrics_data):
        """Test feature importance raises error for non-zscore method."""
        detector = AnomalyDetector(method='isolation_forest')
        detector.fit(sample_metrics_data)

        with pytest.raises(RuntimeError, match="only available for Z-score"):
            detector.get_feature_importance()

    def test_repr(self, trained_anomaly_detector):
        """Test string representation."""
        repr_str = repr(trained_anomaly_detector)
        assert 'AnomalyDetector' in repr_str
        assert 'method=' in repr_str
        assert 'fitted=' in repr_str


# ============================================================================
# Integration Tests
# ============================================================================

class TestModelIntegration:
    """Integration tests for models working together."""

    def test_predictor_and_detector_pipeline(self, sample_traffic_data, sample_metrics_data):
        """Test pipeline of predictor -> detector."""
        # Train predictor
        predictor = TrafficPredictor(n_estimators=10, random_state=42)
        predictor.train(sample_traffic_data)

        # Get predictions
        predictions, lower, upper = predictor.predict_with_history(
            sample_traffic_data.tail(20),
            next_steps=10
        )

        # Create detection data from predictions
        detection_data = pd.DataFrame({
            'cpu_usage': predictions * 0.5,
            'response_time': predictions * 0.8,
            'request_count': predictions,
            'connection_count': predictions * 0.3
        })

        # Train anomaly detector
        detector = AnomalyDetector(method='zscore', z_threshold=3.0)

        # Need normal data first
        normal_data = pd.DataFrame({
            'cpu_usage': np.random.normal(50, 10, 50),
            'response_time': np.random.normal(100, 20, 50),
            'request_count': np.random.normal(150, 30, 50),
            'connection_count': np.random.normal(50, 10, 50)
        })
        detector.fit(normal_data)

        # Detect anomalies in prediction data
        labels = detector.detect(detection_data)
        scores = detector.get_anomaly_scores(detection_data)

        assert len(labels) == len(predictions)
        assert len(scores) == len(predictions)

    def test_feature_consistency(self, sample_traffic_data):
        """Test that feature creation is consistent."""
        predictor = TrafficPredictor(n_estimators=10, random_state=42)

        features1 = predictor._create_features(sample_traffic_data)
        features2 = predictor._create_features(sample_traffic_data.copy())

        # Column names should match
        assert list(features1.columns) == list(features2.columns)

        # Data should match for same seed
        np.random.seed(42)
        features1_repeat = predictor._create_features(sample_traffic_data)
        # Reset seed again
        np.random.seed(42)
        features2_repeat = predictor._create_features(sample_traffic_data)

        # Should produce same features with same seed
        pd.testing.assert_frame_equal(features1_repeat, features2_repeat)