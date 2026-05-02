# AI-Driven Autonomous Infrastructure Manager

> Intelligent Load Balancing and Auto-Scaling System with ML-Powered Predictions

**University SE Project** - Group 23K

| Member | Roll Number |
|--------|------------|
| Ali Sharjeel | 23K-0904 |
| Mujtaba Khan | 23K-0668 |
| Muhammad Saim | 23K-0708 |

---

## Overview

This project implements an AI-driven infrastructure management system that uses machine learning to optimize distributed system performance. It demonstrates how ML can enhance traditional load balancing with predictive and adaptive behavior.

### Key Features

- **Traffic Generator**: Simulates realistic user requests with multiple patterns (constant, ramp, spike, sine wave)
- **Monitoring System**: Real-time metrics collection with aggregation and statistics
- **Intelligent Load Balancer**: Three routing strategies - Round Robin, Least Connections, and AI-Powered
- **Auto-Scaler**: Predictive scaling based on ML forecasts and configurable thresholds
- **ML Models**: Traffic prediction with confidence intervals and anomaly detection
- **Dashboard**: Real-time visualization with Streamlit or interactive TUI

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

For dashboard dependencies:
```bash
pip install -r requirements-dashboard.txt
```

### 2. Run the TUI Testing Interface (Recommended First Test)

```bash
python test_tui.py
```

This interactive terminal interface tests all components:
- Traffic Generator (all patterns)
- Monitoring System (metrics collection)
- Load Balancer (all 3 strategies)
- Auto-Scaler (scaling decisions)
- ML Models (prediction & anomaly detection)
- Orchestrator (full system integration)

### 3. Run Unit Tests

```bash
pytest tests/ -v
```

**85 tests** covering all components with detailed assertions.

### 4. Run the Simulation

```bash
# Basic simulation (10 iterations)
python main.py

# Custom scenario with more iterations
python main.py --scenario spike --iterations 50

# With detailed logging
python main.py --log-level DEBUG

# Available scenarios: normal, spike, ramp, sine_wave
```

### 5. Launch the Streamlit Dashboard

```bash
streamlit run src/dashboard/app.py
```

The dashboard provides:
- **Overview**: System status cards
- **Real-time Metrics**: CPU, memory, response time charts
- **Load Balancer**: Strategy distribution visualization
- **AI Predictions**: Predicted vs actual traffic
- **Auto-Scaling**: Scaling events timeline
- **Comparison**: Strategy performance metrics

---

## Project Structure

```
.
├── main.py                    # Entry point
├── test_tui.py                # Interactive testing TUI
├── requirements.txt           # Core dependencies
├── requirements-dashboard.txt # Dashboard dependencies
├── configs/
│   └── config.yaml            # System configuration
├── src/
│   ├── __init__.py
│   ├── orchestrator.py        # System coordinator
│   ├── components/
│   │   ├── traffic_generator.py   # Traffic simulation
│   │   ├── monitoring_system.py    # Metrics collection
│   │   ├── load_balancer.py        # 3 routing strategies
│   │   ├── auto_scaler.py          # Predictive scaling
│   │   └── backend_server.py       # Server simulation
│   ├── models/
│   │   ├── traffic_predictor.py    # ML traffic forecasting
│   │   └── anomaly_detector.py      # Anomaly detection
│   └── dashboard/
│       └── app.py                  # Streamlit dashboard
└── tests/
    ├── test_components.py     # Component unit tests
    └── test_models.py         # ML model tests
```

---

## Architecture

### Load Balancing Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| **Round Robin** | Distributes requests equally in rotation | Uniform workloads |
| **Least Connections** | Routes to server with fewest active connections | Variable workload lengths |
| **AI-Powered** | Weights routing by ML-predicted health scores | Dynamic, unpredictable traffic |

### Auto-Scaling Configuration

Default thresholds in `configs/config.yaml`:
- **Scale Up**: CPU > 70%
- **Scale Down**: CPU < 30%
- **Cooldowns**: 60s (up), 120s (down)
- **Limits**: 1-10 servers

### ML Models

- **TrafficPredictor**: Random Forest-based forecasting with confidence intervals
- **AnomalyDetector**: Isolation Forest for multivariate anomaly detection

---

## Configuration

Edit `configs/config.yaml` to customize:

```yaml
orchestrator:
  simulation:
    interval_seconds: 1.0
    max_iterations: 100
    scenario: "normal"

traffic_generator:
  base_rate: 10
  max_rate: 100

auto_scaler:
  min_servers: 1
  max_servers: 10
  scale_up_threshold: 70.0
  scale_down_threshold: 30.0

ai_prediction:
  predictor:
    n_estimators: 100
  anomaly_detector:
    method: "isolation_forest"
```

---

## Command Line Options

```bash
python main.py [OPTIONS]

Options:
  --config FILE         Path to config file (default: configs/config.yaml)
  --scenario SCENARIO   Traffic pattern: normal, spike, ramp, sine_wave
  --iterations N        Number of simulation iterations
  --log-level LEVEL     Logging: DEBUG, INFO, WARNING, ERROR
  --dashboard          Launch Streamlit dashboard after simulation
```

---

## Testing

### TUI Tests (Interactive)
```bash
python test_tui.py
```

### Unit Tests
```bash
pytest tests/ -v           # Verbose output
pytest tests/ --cov=src    # With coverage
pytest tests/ -k "traffic" # Run specific tests
```

---

## Tech Stack

- **Python 3.10+**
- **Flask** - Backend server simulation
- **Scikit-learn** - Machine learning models
- **Pandas/NumPy** - Data processing
- **Streamlit** - Dashboard visualization
- **Pytest** - Testing framework

---

## Expected Outcomes

This project demonstrates:

1. **Comparison of Load Balancing Strategies** - Traditional vs AI-powered routing
2. **ML-Based Traffic Prediction** - Forecasting with confidence intervals
3. **Anomaly Detection** - Identifying abnormal server behavior
4. **Predictive Auto-Scaling** - Proactive resource management
5. **Real-time Visualization** - Dashboard for system monitoring

---

## License

Academic Project - SE Department