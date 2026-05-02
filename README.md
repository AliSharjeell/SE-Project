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

## Architecture Flow: How It Works

> *A beginner-friendly journey through your infrastructure management system*

---

### The Journey of a Request 📨

Imagine a user clicks a button on a website. That click creates a **request** — a digital message saying "give me this page." Here's how our system handles it:

```
User Click
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. STREAMLIT DASHBOARD (Control Center)                        │
│     User watches real-time metrics • Selects presets or manual │
│     controls • Injects chaos to test resilience                 │
└─────────────────────────────────────────────────────────────────┘
    │  (via HTTP)
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. GATEWAY (Load Balancer) — The Traffic Cop 🚦               │
│     FastAPI service that decides WHERE to send the request     │
│     • Tries 3 strategies: Round Robin, Least Connections,      │
│       or AI-Powered (based on server health scores)            │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. BACKEND SERVERS (The Workers) — Docker Containers 🐳      │
│     3 FastAPI servers running in isolated Docker containers    │
│     Each handles the request, returns a response              │
│     Limited to 0.25 CPU each (lightweight, laptop-friendly)   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
    Response sent back to user ✅
```

---

### Plain-English Technicals 🔧

| Technology | What It Does in This Project |
|------------|------------------------------|
| **Docker** 🐳 | Acts as the **physical metal**. Instead of needing 3 separate computers, Docker creates isolated "boxes" (containers) on one machine. Each backend server runs in its own box. |
| **FastAPI** ⚡ | The **language** the servers speak. Like how humans use English/French, computers use HTTP. FastAPI is a modern, fast framework for building APIs (web services). |
| **Scikit-learn** 🧠 | The **brain**. Uses Random Forest algorithm to predict traffic patterns 10 minutes into the future. Also uses Isolation Forest to detect anomalies (unusual behavior). |
| **Streamlit** 📊 | The **control center dashboard**. Displays real-time charts, lets you inject chaos (kill servers), and control traffic patterns without writing code. |
| **Docker SDK** 🔌 | The **automation layer**. Allows the auto-scaler to programmatically start/stop Docker containers based on CPU usage. |

---

### Step-by-Step System Lifecycle 🔄

#### Phase 1: User Sends a Request
```
Dashboard → Gateway (/route endpoint)
```
The user clicks "Send Test Request" on the Streamlit dashboard. This sends an HTTP request to the Gateway service.

#### Phase 2: Gateway Decides
```
Gateway Load Balancer
    │
    ├─ Round Robin: "You! Server 1. Take it."
    ├─ Least Connections: "Server with fewest work, take this."
    └─ AI-Powered: "Based on health scores, Server 3 is healthiest."
```

#### Phase 3: Request Arrives at Backend
```
Backend FastAPI (/process endpoint)
    │
    ├─ Records timestamp
    ├─ Simulates processing (50-200ms)
    └─ Returns response with server ID
```

#### Phase 4: Metrics Collected
```
Monitoring System
    │
    ├─ Collects: CPU %, Memory %, Response Time
    ├─ Stores in history
    └─ Used by ML models for predictions
```

#### Phase 5: ML Magic Happens
```
ML Service
    │
    ├─ TrafficPredictor: "Based on patterns, expect 10,000 RPS in 10 minutes"
    └─ AnomalyDetector: "This spike looks unusual — flag it!"
```

#### Phase 6: Auto-Scaling (if needed)
```
Auto-Scaler (Docker SDK)
    │
    ├─ CPU > 70%? → Start a new Docker container
    └─ CPU < 30%? → Stop an unnecessary container
```

---

### The Control Center: Streamlit Dashboard 🎛️

The Streamlit dashboard is your **mission control**. It offers two modes:

#### Preset Mode (Automated Demos) 🎬
| Button | What It Does |
|--------|--------------|
| **Black Friday Rush** | Simulates massive traffic ramp (10,000+ RPS). Watch the auto-scaler spin up new containers! |
| **DDoS Attack** | Generates erratic spikes AND kills a backend container simultaneously. Tests system resilience. |
| **Normal Operations** | Resets everything to a calm baseline (100 RPS constant). |

#### Manual Mode (Deep Control) 🔬
For engineers who want fine-grained control:

- **Routing Strategy**: Switch between Round Robin, Least Connections, or AI-Powered
- **Traffic Intensity**: Slider from 10 to 10,000 requests per second
- **Traffic Shape**: Choose patterns — constant, ramp, spike, sine wave, burst
- **Inject Chaos**: The **red-bordered button** that kills a random backend container. Watch the load balancer gracefully route around the failure!

---

### Visual: Request Flow Diagram

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   USER (Browser)                     │
                    └──────────────────────┬──────────────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────────────┐
                    │              📊 STREAMLIT DASHBOARD                │
                    │     • Real-time charts                              │
                    │     • Preset buttons (Black Friday, DDoS)           │
                    │     • Manual controls (sliders, dropdowns)           │
                    └──────────────────────┬──────────────────────────────┘
                                           │ HTTP
                    ┌──────────────────────▼──────────────────────────────┐
                    │           🚦 GATEWAY (Load Balancer)                │
                    │     • Round Robin (sequential)                      │
                    │     • Least Connections (fewest busy)               │
                    │     • AI-Powered (health-score weighted)            │
                    └──────────────────────┬──────────────────────────────┘
                                           │
           ┌───────────────────────────────┼───────────────────────────────┐
           │                               │                               │
           ▼                               ▼                               ▼
┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
│  🐳 Backend-1    │           │  🐳 Backend-2    │           │  🐳 Backend-3    │
│  (Docker)        │           │  (Docker)        │           │  (Docker)        │
│  FastAPI         │           │  FastAPI         │           │  FastAPI         │
│  Process request │           │  Process request │           │  Process request │
└──────────────────┘           └──────────────────┘           └──────────────────┘
           ▲                               ▲                               ▲
           │                               │                               │
           └───────────────────────────────┼───────────────────────────────┘
                                           │ Metrics
                    ┌──────────────────────▼──────────────────────────────┐
                    │            🧠 ML SERVICE (Scikit-learn)              │
                    │     • TrafficPredictor (Random Forest)              │
                    │     • AnomalyDetector (Isolation Forest)             │
                    └──────────────────────┬──────────────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────────────┐
                    │        🔌 AUTO-SCALER (Docker SDK)                 │
                    │     • Monitors CPU usage                           │
                    │     • Spins up/kills containers dynamically         │
                    └─────────────────────────────────────────────────────┘
```

---

### Key Concepts for Beginners 📚

| Term | Simple Explanation |
|------|-------------------|
| **Container** | A lightweight "box" that isolates an application. Like a virtual computer inside your computer. |
| **Load Balancer** | A traffic cop that distributes work evenly so no single server gets overwhelmed. |
| **Auto-Scaling** | The system automatically adds or removes servers based on demand — like adding cashiers during a busy rush. |
| **ML Prediction** | The computer learns patterns from past data to guess future traffic — like knowing rush hour is coming. |
| **Chaos Engineering** | Intentionally breaking things to test resilience. If you can gracefully handle failures, your system is robust. |

---

## License

Academic Project - SE Department