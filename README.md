# AI-Driven Autonomous Infrastructure Manager

> Intelligent Load Balancing and Auto-Scaling System with ML-Powered Predictions

**University SE Project** - Group 23K

| Member | Roll Number |
|--------|------------|
| Ali Sharjeel | 23K-0904 |
| Mujtaba Khan | 23K-0668 |
| Muhammad Saim | 23K-0708 |

---

## System Capabilities

### Traffic Generator
- Generate requests with **5 patterns**: Constant, Ramp, Spike, Sine Wave, Burst
- Simulates realistic user traffic at varying rates
- Configurable base and max rates

### Load Balancer
- **Round Robin**: Sequential request distribution
- **Least Connections**: Routes to server with fewest active connections
- **AI-Powered**: ML-predicted health scores for intelligent routing
- Add/remove servers dynamically

### Auto-Scaler
- Predictive scaling based on CPU thresholds
- Scale Up: CPU > 70% (default)
- Scale Down: CPU < 30% (default)
- Configurable cooldown periods (60s up, 120s down)
- Server limits: 1-10 (configurable)

### ML Traffic Predictor
- Random Forest-based forecasting
- 10-minute prediction horizon
- 95% confidence intervals
- Feature importance analysis

### ML Anomaly Detector
- Isolation Forest algorithm
- Detects abnormal CPU, response time, connections
- Real-time scoring

### Monitoring System
- Real-time metrics collection
- CPU, Memory, Response Time, Active Connections
- Statistics: Average, Max, Min, Percentiles (P50, P90, P95, P99)

---

## User Interfaces

### Interactive TUI (`python infra_tui.py`)
Full-featured terminal interface with 8 options:

| Option | Feature |
|--------|---------|
| **1** | Traffic Generator - Generate test requests |
| **2** | Load Balancer - Route requests with 3 strategies |
| **3** | Auto-Scaler - View config & test scaling decisions |
| **4** | ML Predictions - Train model & predict traffic |
| **5** | Anomaly Detection - Detect abnormal behavior |
| **6** | System Metrics - View collected metrics history |
| **7** | Auto-Simulation - Step-through simulation |
| **8** | Full Demo - Complete system demonstration |

### Streamlit Dashboard (`streamlit run src/dashboard/app.py`)

| Section | Features |
|---------|----------|
| **Overview** | System status cards, active servers, traffic rate |
| **Real-time Metrics** | CPU/Memory charts, Response Time, Connections |
| **Load Balancer** | Strategy distribution, Server selection pie chart |
| **AI Predictions** | Predicted vs Actual traffic, Confidence intervals |
| **Auto-Scaling** | Server count history, Scaling events timeline |
| **Comparison** | Strategy performance metrics comparison |

Dashboard features:
- Dark/Light theme toggle
- Auto-refresh (5s interval)
- Load scenario selection
- Configurable alert thresholds

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Interactive TUI
```bash
python infra_tui.py
```

### 3. Run Unit Tests
```bash
pytest tests/ -v
```
**85 tests** covering all components.

### 4. Run Simulation via CLI
```bash
# Basic simulation
python main.py

# With custom scenario
python main.py --scenario spike --iterations 50

# With debugging
python main.py --log-level DEBUG
```

### 5. Launch Streamlit Dashboard
```bash
streamlit run src/dashboard/app.py
```

---

## Project Structure

```
.
├── infra_tui.py               # Interactive TUI (recommended)
├── test_tui.py                # Component testing TUI
├── main.py                    # CLI simulation runner
├── requirements.txt           # Core dependencies
├── requirements-dashboard.txt  # Dashboard dependencies
├── configs/config.yaml        # System configuration
├── src/
│   ├── orchestrator.py         # System coordinator
│   ├── components/
│   │   ├── traffic_generator.py   # Traffic simulation
│   │   ├── monitoring_system.py  # Metrics collection
│   │   ├── load_balancer.py        # 3 routing strategies
│   │   ├── auto_scaler.py          # Predictive scaling
│   │   └── backend_server.py       # Server simulation
│   ├── models/
│   │   ├── traffic_predictor.py    # ML traffic forecasting
│   │   └── anomaly_detector.py     # Anomaly detection
│   └── dashboard/app.py             # Streamlit dashboard
└── tests/
    ├── test_components.py     # Component tests (42 tests)
    └── test_models.py         # ML model tests (43 tests)
```

---

## Configuration

Edit `configs/config.yaml`:

```yaml
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

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| ML | Scikit-learn |
| Data | Pandas, NumPy |
| Dashboard | Streamlit, Plotly |
| Testing | Pytest |
| Backend | Flask |

---

## Testing Summary

| Test Suite | Count | Status |
|------------|-------|--------|
| Component Tests | 42 | PASS |
| Model Tests | 43 | PASS |
| **Total** | **85** | **PASS** |

---

## Expected Outcomes

This project demonstrates:

1. **Comparison of Load Balancing Strategies** - Traditional vs AI-powered routing
2. **ML-Based Traffic Prediction** - Forecasting with confidence intervals
3. **Anomaly Detection** - Identifying abnormal server behavior
4. **Predictive Auto-Scaling** - Proactive resource management
5. **Real-time Visualization** - Dashboard and TUI for system monitoring

---

## License

Academic Project - SE Department