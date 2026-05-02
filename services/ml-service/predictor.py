"""
Traffic Prediction Model using Random Forest.

Feature engineering includes temporal features and lag/rolling statistics.
"""

from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split


class TrafficPredictor:
    """
    Traffic predictor using Random Forest Regressor.

    Features engineered:
    - Temporal: hour, day_of_week
    - Lag features: lag_1 to lag_7
    - Rolling statistics: rolling_mean_3/5/10, rolling_std_3/5/10
    """

    FEATURE_NAMES = [
        "hour", "day_of_week",
        "lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "lag_6", "lag_7",
        "rolling_mean_3", "rolling_mean_5", "rolling_mean_10",
        "rolling_std_3", "rolling_std_5", "rolling_std_10"
    ]

    def __init__(self):
        self.model: Optional[RandomForestRegressor] = None
        self.is_trained: bool = False
        self._feature_importance: Dict[str, float] = {}

    def _parse_timestamp(self, timestamp: str) -> datetime:
        """Parse timestamp string to datetime object."""
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(timestamp, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse timestamp: {timestamp}")

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create feature engineering columns."""
        df = df.copy()

        # Temporal features
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek

        # Lag features (lag_1 to lag_7)
        for i in range(1, 8):
            df[f"lag_{i}"] = df["request_count"].shift(i)

        # Rolling mean features
        for window in [3, 5, 10]:
            df[f"rolling_mean_{window}"] = df["request_count"].shift(1).rolling(window=window).mean()

        # Rolling std features
        for window in [3, 5, 10]:
            df[f"rolling_std_{window}"] = df["request_count"].shift(1).rolling(window=window).std()

        return df

    def _prepare_data(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert input data to DataFrame with features."""
        df = pd.DataFrame(data)
        df["timestamp"] = df["timestamp"].apply(self._parse_timestamp)
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Create features
        df = self._create_features(df)

        # Drop rows with NaN values (first rows due to lags)
        df = df.dropna()

        return df

    def train(self, data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Train the Random Forest model."""
        df = self._prepare_data(data)

        X = df[self.FEATURE_NAMES]
        y = df["request_count"]

        # Train-test split for evaluation
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train Random Forest model
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)

        # Calculate feature importance
        importance = self.model.feature_importances_
        self._feature_importance = {
            name: float(imp) for name, imp in zip(self.FEATURE_NAMES, importance)
        }

        # Evaluate on test set
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        self.is_trained = True

        return {
            "train_r2": float(train_score),
            "test_r2": float(test_score)
        }

    def predict_with_history(
        self,
        data: List[Dict[str, Any]],
        horizon: int = 7,
        confidence_level: float = 0.95
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Predict future traffic with confidence intervals.

        Args:
            data: Historical traffic data
            horizon: Number of future periods to predict
            confidence_level: Confidence level for intervals (default 0.95)

        Returns:
            Tuple of (predictions, lower_bound, upper_bound)
        """
        # Train model if not already trained
        if not self.is_trained:
            self.train(data)

        df = self._prepare_data(data)

        # Get last rows for initial features
        last_rows = df.tail(10).copy()

        predictions = []
        lower_bounds = []
        upper_bounds = []

        # Calculate prediction interval using rolling statistics
        y_std = df["request_count"].std()
        z_score = 1.96 if confidence_level == 0.95 else 1.65  # 95% or 90%

        # Use tree prediction variance for intervals
        for _ in range(horizon):
            # Get the last known row features
            features = last_rows[self.FEATURE_NAMES].tail(1).values

            # Predict
            pred = self.model.predict(features)[0]
            predictions.append(float(pred))

            # Calculate interval width based on historical variance
            interval_width = z_score * y_std / np.sqrt(len(df))
            lower_bounds.append(float(pred - interval_width))
            upper_bounds.append(float(pred + interval_width))

            # Update last_rows for next prediction (for temporal features)
            last_row = last_rows.iloc[-1].copy()
            last_row["hour"] = (last_row["hour"] + 1) % 24
            if last_row["hour"] == 0:
                last_row["day_of_week"] = (last_row["day_of_week"] + 1) % 7

            # Shift lags
            for i in range(7, 1, -1):
                last_row[f"lag_{i}"] = last_row[f"lag_{i-1}"]
            last_row["lag_1"] = pred

            # Update rolling stats
            for window in [3, 5, 10]:
                recent = last_rows[f"rolling_mean_{window}"].tail(window).tolist() + [pred]
                last_row[f"rolling_mean_{window}"] = np.mean(recent[-window:])
                last_row[f"rolling_std_{window}"] = np.std(recent[-window:])

            # Append new row
            last_rows = pd.concat([last_rows, last_row.to_frame().T], ignore_index=True)
            last_rows = last_rows.tail(10)

        return predictions, lower_bounds, upper_bounds

    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata and feature importance."""
        if not self.is_trained:
            return {
                "name": "TrafficPredictor",
                "version": "1.0.0",
                "type": "RandomForestRegressor",
                "features": self.FEATURE_NAMES,
                "feature_importance": {}
            }

        return {
            "name": "TrafficPredictor",
            "version": "1.0.0",
            "type": "RandomForestRegressor",
            "features": self.FEATURE_NAMES,
            "feature_importance": self._feature_importance
        }
