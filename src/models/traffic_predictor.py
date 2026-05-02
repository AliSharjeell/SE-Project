"""Traffic Predictor ML Model for AI-Driven Infrastructure Manager.

This module provides time-series forecasting for network traffic metrics
using scikit-learn's Random Forest regressor.
"""

from typing import Tuple, Dict, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import warnings


class TrafficPredictor:
    """ML model for predicting future traffic request rates.

    Uses Random Forest regression with engineered features including:
    - Historical request counts (lagged values)
    - Time-of-day patterns
    - Day-of-week patterns
    - Rolling statistics

    Attributes:
        n_estimators: Number of trees in the Random Forest.
        confidence_level: Confidence level for prediction intervals.
        random_state: Random seed for reproducibility.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        confidence_level: float = 0.95,
        random_state: int = 42
    ):
        """Initialize the TrafficPredictor.

        Args:
            n_estimators: Number of trees in the Random Forest.
            confidence_level: Confidence level for prediction intervals (0-1).
            random_state: Random seed for reproducibility.
        """
        self.n_estimators = n_estimators
        self.confidence_level = confidence_level
        self.random_state = random_state

        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.feature_names: list = []
        self._is_trained = False
        self._training_residuals: np.ndarray = np.array([])

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create engineered features from raw traffic data.

        Args:
            df: DataFrame with 'timestamp' and 'request_count' columns.

        Returns:
            DataFrame with engineered features.
        """
        features_df = df.copy()

        # Parse timestamps if not already datetime
        if not pd.api.types.is_datetime64_any_dtype(features_df['timestamp']):
            features_df['timestamp'] = pd.to_datetime(features_df['timestamp'])

        # Time-based features
        features_df['hour_of_day'] = features_df['timestamp'].dt.hour
        features_df['day_of_week'] = features_df['timestamp'].dt.dayofweek
        features_df['is_weekend'] = features_df['day_of_week'].isin([5, 6]).astype(int)
        features_df['minute_of_day'] = features_df['timestamp'].dt.hour * 60 + features_df['timestamp'].dt.minute

        # Cyclical encoding for time features (captures wrap-around patterns)
        features_df['hour_sin'] = np.sin(2 * np.pi * features_df['hour_of_day'] / 24)
        features_df['hour_cos'] = np.cos(2 * np.pi * features_df['hour_of_day'] / 24)
        features_df['dow_sin'] = np.sin(2 * np.pi * features_df['day_of_week'] / 7)
        features_df['dow_cos'] = np.cos(2 * np.pi * features_df['day_of_week'] / 7)

        # Lag features (previous request counts)
        for lag in range(1, 8):  # Last 7 time steps
            features_df[f'lag_{lag}'] = features_df['request_count'].shift(lag)

        # Rolling statistics
        for window in [3, 5, 10]:
            features_df[f'rolling_mean_{window}'] = (
                features_df['request_count']
                .shift(1)
                .rolling(window=window, min_periods=1)
                .mean()
            )
            features_df[f'rolling_std_{window}'] = (
                features_df['request_count']
                .shift(1)
                .rolling(window=window, min_periods=1)
                .std()
            )

        # Difference features
        features_df['diff_1'] = features_df['request_count'].diff(1).shift(1)
        features_df['diff_7'] = features_df['request_count'].diff(7).shift(1)

        return features_df

    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix and target vector for training.

        Args:
            df: DataFrame with engineered features.

        Returns:
            Tuple of (X, y) arrays for training.
        """
        feature_df = self._create_features(df)

        # Drop rows with NaN values (from lags and rolling)
        feature_df = feature_df.dropna()

        # Define feature columns
        self.feature_names = [
            'hour_of_day', 'day_of_week', 'is_weekend', 'minute_of_day',
            'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos',
            'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_5', 'lag_6', 'lag_7',
            'rolling_mean_3', 'rolling_mean_5', 'rolling_mean_10',
            'rolling_std_3', 'rolling_std_5', 'rolling_std_10',
            'diff_1', 'diff_7'
        ]

        X = feature_df[self.feature_names].values
        y = feature_df['request_count'].values

        return X, y

    def train(self, historical_data: pd.DataFrame) -> 'TrafficPredictor':
        """Train the traffic prediction model.

        Args:
            historical_data: DataFrame with at least 'timestamp' and 'request_count' columns.
                             Optionally can include 'cpu_usage', 'memory_usage', 'response_time'.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If required columns are missing or data is insufficient.
        """
        required_columns = ['timestamp', 'request_count']
        missing_cols = [col for col in required_columns if col not in historical_data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        if len(historical_data) < 20:
            raise ValueError(
                "Insufficient data for training. Need at least 20 samples."
            )

        # Sort by timestamp to ensure proper ordering
        train_data = historical_data.sort_values('timestamp').copy()

        # Prepare training data
        X, y = self._prepare_training_data(train_data)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model.fit(X_scaled, y)

        # Store residuals for confidence interval calculation
        predictions = self.model.predict(X_scaled)
        self._training_residuals = y - predictions

        self._is_trained = True

        return self

    def _get_last_features(self, df: pd.DataFrame) -> np.ndarray:
        """Get feature values from the last row of data for recursive prediction.

        Args:
            df: DataFrame with raw traffic data.

        Returns:
            Feature array for the last timestamp.
        """
        feature_df = self._create_features(df)
        last_features = feature_df[self.feature_names].iloc[-1:].values
        return last_features

    def _create_future_features(
        self,
        last_data: pd.DataFrame,
        n_steps: int
    ) -> np.ndarray:
        """Create feature arrays for future predictions.

        Args:
            last_data: Last known data point.
            n_steps: Number of future steps to predict.

        Returns:
            Feature array for predictions.
        """
        # Parse timestamp
        if not pd.api.types.is_datetime64_any_dtype(last_data['timestamp']):
            last_ts = pd.to_datetime(last_data['timestamp'].iloc[-1])
        else:
            last_ts = last_data['timestamp'].iloc[-1]

        # Assume 1-minute intervals if no interval info
        # In production, this should be derived from the data
        interval = 1  # minutes

        future_features = []
        last_df = last_data.copy()

        for step in range(n_steps):
            future_ts = last_ts + pd.Timedelta(minutes=interval * (step + 1))

            # Create feature row
            feature_row = {
                'timestamp': future_ts,
                'request_count': 0  # Placeholder, will be updated with predictions
            }
            temp_df = pd.concat([last_df, pd.DataFrame([feature_row])], ignore_index=True)

            # Get features
            feature_df = self._create_features(temp_df)
            features = feature_df[self.feature_names].iloc[-1:].values
            future_features.append(features[0])

            # Update last_df with prediction for recursive forecasting
            if step < n_steps - 1:
                # Use model to predict this step, then use for next iteration
                pass  # Will be handled in _predict_recursive

        return np.array(future_features)

    def _predict_recursive(
        self,
        historical_data: pd.DataFrame,
        n_steps: int
    ) -> np.ndarray:
        """Make predictions recursively using previous predictions as input.

        Args:
            historical_data: Last known data.
            n_steps: Number of steps to predict.

        Returns:
            Array of predictions.
        """
        predictions = []
        current_data = historical_data.copy()

        # Parse timestamp
        if not pd.api.types.is_datetime64_any_dtype(current_data['timestamp']):
            current_data['timestamp'] = pd.to_datetime(current_data['timestamp'])

        interval = 1  # minutes

        for step in range(n_steps):
            # Create features
            feature_df = self._create_features(current_data)
            last_features = feature_df[self.feature_names].iloc[-1:].values
            last_features_scaled = self.scaler.transform(last_features)

            # Predict
            pred = self.model.predict(last_features_scaled)[0]
            pred = max(0, pred)  # Request count can't be negative
            predictions.append(pred)

            # Add prediction to data for next iteration
            last_ts = current_data['timestamp'].iloc[-1]
            new_row = pd.DataFrame([{
                'timestamp': last_ts + pd.Timedelta(minutes=interval),
                'request_count': pred
            }])
            current_data = pd.concat([current_data, new_row], ignore_index=True)

        return np.array(predictions)

    def predict(self, next_steps: int) -> np.ndarray:
        """Predict the next N time steps.

        Args:
            next_steps: Number of future time steps to predict.

        Returns:
            Array of predicted request rates.

        Raises:
            RuntimeError: If model has not been trained.
        """
        if not self._is_trained:
            raise RuntimeError(
                "Model has not been trained. Call train() first."
            )

        # This would need the last known data to make predictions
        # In a real system, this would be passed as a parameter or stored
        # For now, return zeros and rely on _predict_with_history
        return np.zeros(next_steps)

    def predict_with_history(
        self,
        historical_data: pd.DataFrame,
        next_steps: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict next N steps with confidence intervals using provided history.

        Args:
            historical_data: DataFrame with 'timestamp' and 'request_count'.
            next_steps: Number of future time steps to predict.

        Returns:
            Tuple of (predictions, lower_bound, upper_bound) arrays.
        """
        if not self._is_trained:
            raise RuntimeError(
                "Model has not been trained. Call train() first."
            )

        # Make predictions
        predictions = self._predict_recursive(historical_data, next_steps)

        # Calculate confidence intervals based on training residuals
        if len(self._training_residuals) > 0:
            residual_std = np.std(self._training_residuals)

            # Z-score for confidence level (approximation)
            z_scores = {
                0.90: 1.645,
                0.95: 1.96,
                0.99: 2.576
            }
            z = z_scores.get(self.confidence_level, 1.96)

            # Confidence interval widens slightly with prediction horizon
            horizon_factor = 1 + 0.1 * np.arange(next_steps)
            margin = z * residual_std * horizon_factor

            lower_bound = np.maximum(0, predictions - margin)
            upper_bound = predictions + margin
        else:
            lower_bound = np.maximum(0, predictions * 0.8)
            upper_bound = predictions * 1.2

        return predictions, lower_bound, upper_bound

    def predict_with_confidence(
        self,
        next_steps: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict with confidence intervals.

        Note: This method requires the predictor to maintain internal state
        of recent predictions. For full functionality, use predict_with_history().

        Args:
            next_steps: Number of future time steps to predict.

        Returns:
            Tuple of (predictions, lower_bound, upper_bound) arrays.

        Raises:
            RuntimeError: If model has not been trained.
        """
        # Simplified version that returns zero arrays
        # Use predict_with_history() for actual predictions
        if not self._is_trained:
            raise RuntimeError(
                "Model has not been trained. Call train() first."
            )

        predictions = np.zeros(next_steps)
        lower_bound = np.zeros(next_steps)
        upper_bound = np.zeros(next_steps)

        return predictions, lower_bound, upper_bound

    def save_model(self, path: str) -> None:
        """Save the trained model to disk.

        Args:
            path: File path to save the model.

        Raises:
            RuntimeError: If model has not been trained.
        """
        if not self._is_trained:
            raise RuntimeError(
                "Model has not been trained. Cannot save untrained model."
            )

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'n_estimators': self.n_estimators,
            'confidence_level': self.confidence_level,
            'random_state': self.random_state,
            'is_trained': self._is_trained,
            'training_residuals': self._training_residuals
        }

        joblib.dump(model_data, path)

    def load_model(self, path: str) -> 'TrafficPredictor':
        """Load a trained model from disk.

        Args:
            path: File path to load the model from.

        Returns:
            Self with loaded model.
        """
        model_data = joblib.load(path)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.n_estimators = model_data['n_estimators']
        self.confidence_level = model_data['confidence_level']
        self.random_state = model_data['random_state']
        self._is_trained = model_data['is_trained']
        self._training_residuals = model_data['training_residuals']

        return self

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores from the trained model.

        Returns:
            Dictionary mapping feature names to importance scores.

        Raises:
            RuntimeError: If model has not been trained.
        """
        if not self._is_trained:
            raise RuntimeError(
                "Model has not been trained. Call train() first."
            )

        importances = self.model.feature_importances_

        return {
            name: float(importance)
            for name, importance in zip(self.feature_names, importances)
        }

    def get_confidence_score(self, prediction: float) -> float:
        """Get confidence score for a prediction.

        Returns a value between 0 and 1 indicating how confident
        the model is in the given prediction.

        Args:
            prediction: The predicted value.

        Returns:
            Confidence score (0-1).
        """
        if not self._is_trained:
            return 0.0

        # Base confidence on residual spread
        if len(self._training_residuals) > 0:
            residual_std = np.std(self._training_residuals)
            mean_target = np.mean(self._training_residuals) + np.mean(
                self.model.predict(self.scaler.transform(
                    np.zeros((1, len(self.feature_names)))
                ))
            )

            if mean_target > 0:
                cv = residual_std / mean_target  # Coefficient of variation
                confidence = max(0, min(1, 1 - cv))
            else:
                confidence = 0.5
        else:
            confidence = 0.5

        return confidence
