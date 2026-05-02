"""
ML Prediction Service - FastAPI Application

Provides traffic prediction and anomaly detection endpoints.
"""

from datetime import datetime
from typing import List, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from predictor import TrafficPredictor
from anomaly import AnomalyDetector

app = FastAPI(title="ML Prediction Service", version="1.0.0")

# Initialize models
traffic_predictor = TrafficPredictor()
anomaly_detector = AnomalyDetector()


# Request/Response Models
class TrafficDataPoint(BaseModel):
    timestamp: str
    request_count: int


class TrafficPredictionRequest(BaseModel):
    historical_data: List[TrafficDataPoint]


class PredictionResult(BaseModel):
    predictions: List[float]
    lower_bound: List[float]
    upper_bound: List[float]
    confidence_level: float = 0.95


class AnomalyDetectionRequest(BaseModel):
    cpu_usage: float = Field(ge=0, le=100)
    memory_usage: float = Field(ge=0, le=100)
    response_time: float = Field(ge=0)
    active_connections: int = Field(ge=0)


class AnomalyDetectionResult(BaseModel):
    is_anomaly: bool
    anomaly_score: float
    features: Dict[str, float]


class ModelInfo(BaseModel):
    name: str
    version: str
    type: str
    features: List[str]
    feature_importance: Dict[str, float]


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/predict/traffic", response_model=PredictionResult)
async def predict_traffic(request: TrafficPredictionRequest) -> PredictionResult:
    """
    Predict traffic based on historical data.

    Trains the model if needed and returns predictions with 95% confidence intervals.
    """
    # Convert request to DataFrame format
    data = [
        {"timestamp": point.timestamp, "request_count": point.request_count}
        for point in request.historical_data
    ]

    predictions, lower_bound, upper_bound = traffic_predictor.predict_with_history(data)

    return PredictionResult(
        predictions=predictions,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        confidence_level=0.95
    )


@app.post("/detect/anomaly", response_model=AnomalyDetectionResult)
async def detect_anomaly(request: AnomalyDetectionRequest) -> AnomalyDetectionResult:
    """
    Detect anomalies in system metrics.

    Uses Isolation Forest to identify anomalous behavior based on
    CPU usage, memory usage, response time, and active connections.
    """
    features = {
        "cpu_usage": request.cpu_usage,
        "memory_usage": request.memory_usage,
        "response_time": request.response_time,
        "active_connections": request.active_connections
    }

    is_anomaly = anomaly_detector.detect(features)
    anomaly_score = anomaly_detector.get_anomaly_scores([features])[0]

    return AnomalyDetectionResult(
        is_anomaly=is_anomaly,
        anomaly_score=anomaly_score,
        features=features
    )


@app.get("/model/info", response_model=ModelInfo)
async def get_model_info() -> ModelInfo:
    """
    Get model metadata and feature importance.

    Returns information about the traffic prediction model including
    feature names and their importance scores.
    """
    model_info = traffic_predictor.get_model_info()

    return ModelInfo(
        name=model_info["name"],
        version=model_info["version"],
        type=model_info["type"],
        features=model_info["features"],
        feature_importance=model_info["feature_importance"]
    )
