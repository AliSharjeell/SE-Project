"""
ML Health Prediction Service

Collects metrics from infrastructure and predicts server health scores
using a weighted model trained on historical data.
"""

import time
import threading
import os
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional
import requests
import random

from flask import Flask, jsonify
from anomaly import AnomalyDetector

app = Flask(__name__)

# Configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8000")
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8002")
BACKEND_URLS = [
    "http://backend-1:8000",
    "http://backend-2:8000",
    "http://backend-3:8000",
]

# Metrics history (time-series for training)
METRICS_WINDOW = 100
metrics_history: Dict[str, deque] = {url: deque(maxlen=METRICS_WINDOW) for url in BACKEND_URLS}

# Model weights (simulating trained model)
# In production, load from pickled sklearn/xgboost model
MODEL_WEIGHTS = {
    'cpu_weight': -0.3,
    'memory_weight': -0.2,
    'connections_weight': -0.1,
    'error_rate_weight': -0.5,
    'success_rate_weight': 0.3,
    'latency_weight': -0.1,
}

HIGH_CPU_THRESHOLD = 80.0
HIGH_MEMORY_THRESHOLD = 85.0
HIGH_ERROR_RATE_THRESHOLD = 0.05

# Anomaly detector instance (lazily fitted on first call)
_anomaly_detector = AnomalyDetector(contamination=0.1, random_state=42)
_anomaly_detector_fitted = False


def collect_gateway_stats() -> Dict:
    """Fetch routing statistics from gateway."""
    try:
        response = requests.get(f"{GATEWAY_URL}/stats", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"servers": {}}


def collect_orchestrator_metrics() -> Dict:
    """Fetch container CPU metrics from orchestrator."""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/metrics", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"metrics": {}}


def check_backend_health(url: str) -> Optional[Dict]:
    """Check individual backend health."""
    try:
        start = time.time()
        response = requests.get(f"{url}/health", timeout=1)
        latency = (time.time() - start) * 1000
        return {
            "healthy": response.status_code == 200,
            "latency_ms": latency,
            "status_code": response.status_code
        }
    except:
        return {"healthy": False, "latency_ms": 9999, "status_code": 503}


def collect_all_metrics() -> Dict[str, Dict]:
    """Collect metrics from all sources for all servers."""
    gateway_stats = collect_gateway_stats()
    container_metrics = collect_orchestrator_metrics()
    all_metrics = {}

    for url in BACKEND_URLS:
        server_id = url.replace("http://", "").replace(":8000", "")
        server_stats = gateway_stats.get("servers", {}).get(url, {})
        cpu_percent = container_metrics.get("metrics", {}).get(server_id, 50.0)

        health_check = check_backend_health(url)

        total_requests = server_stats.get("total_requests", 0)
        successful = server_stats.get("successful_requests", 0)
        failed = server_stats.get("failed_requests", 0)
        active_conn = server_stats.get("active_connections", 0)

        error_rate = failed / total_requests if total_requests > 0 else 0
        success_rate = successful / total_requests if total_requests > 0 else 1.0

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": random.uniform(40, 70),  # Simulated
            "active_connections": active_conn,
            "total_requests": total_requests,
            "successful_requests": successful,
            "failed_requests": failed,
            "error_rate": error_rate,
            "success_rate": success_rate,
            "latency_ms": health_check.get("latency_ms", 100),
            "healthy": health_check.get("healthy", False),
            "status_code": health_check.get("status_code", 503),
        }

        all_metrics[url] = metrics
        metrics_history[url].append(metrics)

    return all_metrics


def predict_health_score(metrics: Dict) -> float:
    """
    Predict health score (0.0 to 1.0) using the declared MODEL_WEIGHTS.
    Higher score = healthier server.
    """
    if not metrics.get("healthy", False):
        return 0.05

    # Normalize each feature to 0..1 (0 = worst, 1 = best)
    cpu = metrics.get("cpu_percent", 50)
    cpu_norm = max(0.0, 1.0 - (cpu / 100.0))

    memory = metrics.get("memory_percent", 50)
    memory_norm = max(0.0, 1.0 - (memory / 100.0))

    connections = metrics.get("active_connections", 0)
    connections_norm = max(0.0, 1.0 - (connections / 100.0))

    error_rate = metrics.get("error_rate", 0)
    error_norm = max(0.0, 1.0 - min(error_rate * 20, 1.0))  # 5% error -> 0

    success_rate = metrics.get("success_rate", 1.0)
    success_norm = min(success_rate, 1.0)

    latency = metrics.get("latency_ms", 100)
    latency_norm = max(0.0, 1.0 - min(latency / 1000.0, 1.0))

    # Weighted sum using MODEL_WEIGHTS
    score = (
        1.0
        + MODEL_WEIGHTS['cpu_weight'] * (1 - cpu_norm)
        + MODEL_WEIGHTS['memory_weight'] * (1 - memory_norm)
        + MODEL_WEIGHTS['connections_weight'] * (1 - connections_norm)
        + MODEL_WEIGHTS['error_rate_weight'] * (1 - error_norm)
        + MODEL_WEIGHTS['success_rate_weight'] * success_norm
        + MODEL_WEIGHTS['latency_weight'] * (1 - latency_norm)
    )

    # Hard-floor for unhealthy thresholds (penalty overrides model)
    if cpu > HIGH_CPU_THRESHOLD:
        score -= 0.15 * ((cpu - HIGH_CPU_THRESHOLD) / (100 - HIGH_CPU_THRESHOLD))
    if memory > HIGH_MEMORY_THRESHOLD:
        score -= 0.10 * ((memory - HIGH_MEMORY_THRESHOLD) / (100 - HIGH_MEMORY_THRESHOLD))
    if error_rate > HIGH_ERROR_RATE_THRESHOLD:
        score -= 0.25 * (error_rate / HIGH_ERROR_RATE_THRESHOLD)
    if latency > 500:
        score -= 0.15
    elif latency > 200:
        score -= 0.05

    return max(0.0, min(1.0, score))


def get_all_health_scores() -> Dict[str, float]:
    """Get health scores for all servers."""
    all_metrics = collect_all_metrics()
    return {url: predict_health_score(metrics) for url, metrics in all_metrics.items()}


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "ml-service"})


@app.route("/metrics")
def metrics():
    """Return current metrics for all servers."""
    all_metrics = collect_all_metrics()
    return jsonify({"metrics": all_metrics, "timestamp": datetime.now().isoformat()})


@app.route("/scores")
def scores():
    """Return predicted health scores for all servers."""
    health_scores = get_all_health_scores()
    return jsonify({
        "scores": health_scores,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/scores/<path:server_url>")
def server_score(server_url: str):
    """Return health score for specific server."""
    if not server_url.startswith("http"):
        server_url = f"http://{server_url}"

    all_metrics = collect_all_metrics()
    if server_url in all_metrics:
        score = predict_health_score(all_metrics[server_url])
        return jsonify({
            "server": server_url,
            "health_score": round(score, 3),
            "metrics": all_metrics[server_url]
        })
    return jsonify({"error": "Server not found"}), 404


@app.route("/info")
def model_info():
    """Return model metadata and feature importance."""
    return jsonify({
        "name": "HealthScorePredictor",
        "version": "1.0.0",
        "type": "weighted_ensemble",
        "features": [
            "cpu_percent",
            "memory_percent",
            "active_connections",
            "error_rate",
            "success_rate",
            "latency_ms"
        ],
        "feature_importance": MODEL_WEIGHTS,
        "thresholds": {
            "high_cpu": HIGH_CPU_THRESHOLD,
            "high_memory": HIGH_MEMORY_THRESHOLD,
            "high_error_rate": HIGH_ERROR_RATE_THRESHOLD
        }
    })


def _ensure_anomaly_detector_fitted():
    """Lazily fit anomaly detector on accumulated metrics history."""
    global _anomaly_detector_fitted
    if _anomaly_detector_fitted:
        return

    # Gather enough normal data points from history
    normal_data = []
    for url, history in metrics_history.items():
        for m in history:
            normal_data.append({
                "cpu_usage": m.get("cpu_percent", 50),
                "memory_usage": m.get("memory_percent", 50),
                "response_time": m.get("latency_ms", 100),
                "active_connections": m.get("active_connections", 0),
            })

    if len(normal_data) >= 10:
        try:
            _anomaly_detector.fit(normal_data)
            _anomaly_detector_fitted = True
        except Exception as e:
            print(f"[ML] Anomaly detector fit failed: {e}")


@app.route("/anomalies")
def anomalies():
    """Return anomaly detection results for current metrics."""
    _ensure_anomaly_detector_fitted()
    all_metrics = collect_all_metrics()
    results = {}

    for url, metrics in all_metrics.items():
        features = {
            "cpu_usage": metrics.get("cpu_percent", 50),
            "memory_usage": metrics.get("memory_percent", 50),
            "response_time": metrics.get("latency_ms", 100),
            "active_connections": metrics.get("active_connections", 0),
        }
        is_anomaly = _anomaly_detector.detect(features) if _anomaly_detector_fitted else False
        score = _anomaly_detector.get_anomaly_scores([features])[0] if _anomaly_detector_fitted else 0.0
        results[url] = {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(score, 4),
            "features": features
        }

    return jsonify({
        "anomalies": results,
        "detector_fitted": _anomaly_detector_fitted,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/history/<path:server_url>")
def history(server_url: str):
    """Return metrics history for a server."""
    if not server_url.startswith("http"):
        server_url = f"http://{server_url}"

    if server_url in metrics_history:
        return jsonify({
            "server": server_url,
            "history": list(metrics_history[server_url])
        })
    return jsonify({"error": "Server not found"}), 404


def metrics_collector():
    """Continuously collect metrics in background."""
    while True:
        try:
            collect_all_metrics()
        except:
            pass
        time.sleep(5)


if __name__ == "__main__":
    collector_thread = threading.Thread(target=metrics_collector, daemon=True)
    collector_thread.start()

    print("ML Service starting...")
    print(f"Monitoring: {BACKEND_URLS}")
    print("Endpoints: /health /metrics /scores /scores/{server} /info /history/{server}")

    app.run(host="0.0.0.0", port=8000)