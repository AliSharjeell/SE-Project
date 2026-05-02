# AI-Driven Autonomous Infrastructure Manager

> Intelligent Load Balancing and Auto-Scaling System with ML-Powered Predictions

**University SE Project** - Group 23K

| Member | Roll Number |
|--------|------------|
| Ali Sharjeel | 23K-0904 |
| Mujtaba Khan | 23K-0668 |
| Muhammad Saim | 23K-0708 |

---

## System Architecture

### Monolithic (Original)
```
python infra_tui.py          # Interactive TUI
python main.py               # CLI simulation
streamlit run src/dashboard/app.py  # Dashboard
```

### Microservices (Docker-based)
```
docker-compose up            # Full stack with 7 containers
```

---

## Docker Microservices Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              docker-compose.yml                               │
└─────────────────────────────────────────────────────────────────────────────┘
           │                    │                    │                   │
           ▼                    ▼                    ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐
│   backend-1      │  │   backend-2      │  │   backend-3      │  │ gateway  │
│   (FastAPI)      │  │   (FastAPI)      │  │   (FastAPI)      │  │  (LB)    │
│   0.25 CPU       │  │   0.25 CPU       │  │   0.25 CPU       │  │ 0.5 CPU  │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────┘
                                                                    │
           ┌─────────────────────────────────────────────────────────┘
           ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   ml-service     │  │   autoscaler     │  │   dashboard     │
│   (Scikit-learn) │  │   (Docker SDK)   │  │   (Streamlit)    │
│   0.5 CPU        │  │   0.25 CPU       │  │   0.5 CPU       │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## Services

### Backend Servers
- **3 FastAPI instances** for request processing
- Resource limits: 0.25 CPU, 128MB RAM per container
- Endpoints: `/health`, `/process`, `/metrics`

### Gateway (Load Balancer)
- **Round Robin**: Sequential rotation through servers
- **Least Connections**: Routes to server with fewest connections
- **AI-Powered**: Weighted selection based on health scores
- Port: 8000

### ML Service
- **TrafficPredictor**: Random Forest-based traffic forecasting
- **AnomalyDetector**: Isolation Forest for anomaly detection
- CPU-only inference (Scikit-learn, no GPU required)
- Port: 8001

### Auto-Scaler
- Docker SDK-based container management
- Threshold-based scaling: CPU > 70% (scale up), CPU < 30% (scale down)
- 60-second cooldown between scaling actions
- Dynamic server registration with gateway

### Dashboard (Streamlit)
- Real-time metrics visualization
- Apple/Linear-inspired dark theme
- Live Demo Control Panel with Presets and Manual modes
- Port: 8501

---

## Quick Start

### 1. Monolithic Mode (Original)
```bash
# Install dependencies
pip install -r requirements.txt

# Interactive TUI
python infra_tui.py

# CLI Simulation
python main.py --scenario spike --iterations 50

# Streamlit Dashboard (original)
streamlit run src/dashboard/app.py
```

### 2. Docker Mode (Microservices)
```bash
# Build and start all services
docker-compose up --build

# Access points:
# - Gateway API:    http://localhost:8000
# - ML Service:     http://localhost:8001
# - Dashboard:      http://localhost:8501

# Stop services
docker-compose down
```

### 3. Run Tests
```bash
pytest tests/ -v
```

---

## API Endpoints

### Gateway (Port 8000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/route` | Route request via specified strategy |
| GET | `/servers` | List all registered servers |
| POST | `/servers/register` | Register a new server |
| DELETE | `/servers/{id}` | Remove a server |
| GET | `/stats` | Routing statistics |
| GET | `/health` | Gateway health check |

### ML Service (Port 8001)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predict/traffic` | Traffic prediction with confidence intervals |
| POST | `/detect/anomaly` | Anomaly detection on metrics |
| GET | `/model/info` | Model metadata and feature importance |
| GET | `/health` | Service health check |

### Orchestrator (Live Demo Control)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/set_traffic` | Set traffic pattern and intensity |
| POST | `/api/set_strategy` | Set load balancing strategy |
| POST | `/api/inject_chaos` | Kill a backend container (chaos testing) |
| GET | `/api/status` | Current system status |

---

## Traffic Patterns

| Pattern | Description |
|---------|-------------|
| `constant` | Fixed request rate |
| `ramp` | Gradual increase/decrease |
| `spike` | Sudden burst of traffic |
| `sine_wave` | Periodic oscillations |
| `burst` | Multiple simultaneous requests |

---

## Routing Strategies

| Strategy | Algorithm |
|----------|-----------|
| `round_robin` | Sequential rotation |
| `least_connections` | Fewest active connections |
| `ai_powered` | Health-score weighted selection |

---

## Configuration

### Docker Compose Resource Limits
```yaml
deploy:
  resources:
    limits:
      cpus: '0.25'      # 25% of one CPU core
      memory: 128M       # 128MB RAM
```

### Auto-Scaler Thresholds
- Scale Up: CPU > 70%
- Scale Down: CPU < 30%
- Min Servers: 1
- Max Servers: 10
- Cooldown: 60 seconds

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Containerization | Docker, Docker Compose |
| ML (CPU-only) | Scikit-learn |
| Data Processing | Pandas, NumPy |
| Dashboard | Streamlit, Plotly |
| Testing | Pytest |
| Orchestration | Python |

---

## Project Structure

```
.
├── docker-compose.yml         # Microservices orchestration
├── infra_tui.py              # Interactive TUI (original)
├── main.py                   # CLI simulation (original)
├── requirements.txt           # Core dependencies
├── src/                      # Original monolithic source
│   ├── components/           # System components
│   ├── models/              # ML models
│   ├── dashboard/           # Original Streamlit
│   └── orchestrator.py      # System coordinator
├── services/                # Microservices
│   ├── backend/             # FastAPI backend servers
│   ├── gateway/             # Load balancer gateway
│   ├── ml-service/          # ML prediction service
│   ├── autoscaler/          # Docker SDK auto-scaler
│   └── dashboard/           # Streamlit dashboard
└── tests/                   # Unit tests (85 tests)
```

---

## Testing Summary

| Test Suite | Count | Status |
|------------|-------|--------|
| Component Tests | 42 | PASS |
| Model Tests | 43 | PASS |
| **Total** | **85** | **PASS** |

---

## Live Demo Control Panel

The Streamlit dashboard includes a **Live Demo Control Panel** with two modes:

### Presets (Automated Demos)
| Button | Effect |
|--------|--------|
| Black Friday Rush | Massive ramp pattern, 10,000+ RPS |
| DDoS Attack | Severe erratic spikes, chaos injection |
| Normal Operations | Reset to constant 100 RPS baseline |

### Manual (Deep Control)
- **Routing Strategy**: Dropdown to switch between Round Robin, Least Connections, AI-Powered
- **Traffic Intensity**: Slider from 10 to 10,000 RPS
- **Traffic Shape**: Dropdown for constant, ramp, spike, sine_wave
- **Inject Chaos**: Kill a random backend container to test system recovery

---

## License

Academic Project - SE Department