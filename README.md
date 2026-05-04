# AI-Driven Autonomous Infrastructure Manager

> Intelligent Load Balancing and Auto-Scaling System with ML-Powered Predictions

**University SE Project** - Group 23K

| Member | Roll Number |
|--------|------------|
| Ali Sharjeel | 23K-0904 |
| Mujtaba Khan | 23K-0668 |
| Muhammad Saim | 23K-0708 |

---

## 🚀 Quick Start

### 1. Install Docker (Windows)

If you have nothing installed, you need Docker Desktop. Choose one method:

**Option A: Winget (Recommended - Command Line)**
Open PowerShell and run:
```powershell
winget install Docker.DockerDesktop
```

**Option B: Manual Download**
1. Download from https://www.docker.com/products/docker-desktop/
2. Run the installer (`Docker Desktop Installer.exe`)

**Step 2:** Enable WSL 2 (required for Windows). Open PowerShell as Administrator and run:
```powershell
wsl --install
```
Restart your computer when prompted.

**Step 3:** Verify installation. Open Docker Desktop, wait for "running" status, then in terminal:
```bash
docker --version
docker compose version
```

### 2. Launch the Infrastructure

```bash
cd "C:\AppsNew\SE Project"
docker compose up --build
```

This starts all services: 3 backend servers, load balancer, ML service, auto-scaler, and Streamlit dashboard.

### 3. Access Points

| Service | URL |
|---------|-----|
| **Live Dashboard** | http://localhost:8501 |
| **Gateway API** | http://localhost:8000/docs |
| **ML Service** | http://localhost:8001/docs |
| **Live Demo Control API** | http://localhost:8002/docs |

### 4. Stop Services

```bash
docker compose down
```

---

## 🎬 How to Test Demo Flows

The Streamlit dashboard (http://localhost:8501) includes a **Live Demo Control Panel** with two modes:

### Preset Mode (One-Click Demos)

| Preset Button | What It Does |
|---------------|--------------|
| **Black Friday Rush** | Simulates massive traffic ramp (10,000+ RPS) to trigger auto-scaling |
| **DDoS Attack** | Generates erratic traffic spikes AND kills a backend container |
| **Normal Operations** | Resets to calm baseline (100 RPS constant) |

### Manual Mode (Fine-Grained Control)

- **Routing Strategy**: Switch between Round Robin, Least Connections, or AI-Powered
- **Traffic Intensity**: Slider from 10 to 10,000 RPS
- **Traffic Shape**: Choose `constant`, `ramp`, `spike`, `sine_wave`, or `burst`
- **Inject Chaos**: Click to kill a random backend container and watch graceful recovery

### Live Demo Control API

You can also control the system programmatically via the API at http://localhost:8002/docs:

```bash
# Set traffic pattern
curl -X POST http://localhost:8002/api/set_traffic \
  -H "Content-Type: application/json" \
  -d '{"pattern": "spike", "intensity": 5000}'

# Change routing strategy
curl -X POST http://localhost:8002/api/set_strategy \
  -H "Content-Type: application/json" \
  -d '{"strategy": "least_connections"}'

# Kill a random backend (chaos engineering)
curl -X POST http://localhost:8002/api/inject_chaos

# Check system status
curl http://localhost:8002/api/status
```

### What to Watch For

1. **Load Balancing**: Switch strategies and see requests distributed differently across backends
2. **Auto-Scaling**: Set high traffic intensity and watch new containers spin up
3. **Chaos Recovery**: Kill a container and see the load balancer gracefully route around failure
4. **ML Predictions**: Watch traffic forecasts and anomaly alerts in real-time

---

## System Architecture

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
                          ┌─────────────────────────────────────────────────┘
                          │ (health scores sync every 10s)
                          ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   ml-service     │  │   autoscaler     │  │   dashboard     │
│   (Flask)        │  │   (Docker SDK)   │  │   (Streamlit)    │
│   0.5 CPU        │  │   0.25 CPU       │  │   0.5 CPU       │
│   Port 8000      │  │                  │  │   Port 8501     │
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

### ML Service (Port 8000)
Health score prediction service using a weighted ensemble model.

**Features:**
- Collects metrics from gateway and orchestrator every 5 seconds
- Predicts server health scores (0.0-1.0) based on real-time data
- Synced to gateway every 10 seconds for AI-powered routing

**Health Score Model:**
| Factor | Weight | Threshold |
|--------|--------|-----------|
| CPU % | -0.3 | >80% high |
| Memory % | -0.2 | >85% high |
| Error Rate | -0.5 | >5% high |
| Success Rate | +0.3 | - |
| Latency | -0.1 | >200ms slow |
| Connections | -0.1 | >50 high |

**Endpoints:**
- `GET /scores` - All server health scores
- `GET /scores/{server}` - Single server score
- `GET /metrics` - Raw metrics data
- `GET /info` - Model metadata

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

### Orchestrator (Live Demo Control)
- API endpoints for traffic and strategy control
- Chaos injection (kill containers via Docker SDK)
- Port: 8002

---

## API Reference

### Gateway - Load Balancer (Port 8000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/route` | Route request via specified strategy |
| GET | `/servers` | List all registered servers |
| POST | `/servers/register` | Register a new server |
| DELETE | `/servers/{id}` | Remove a server |
| GET | `/stats` | Routing statistics |
| GET | `/health` | Gateway health check |

### ML Service (Port 8000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scores` | Health scores for all servers |
| GET | `/scores/{server}` | Single server health score |
| GET | `/metrics` | Raw metrics data |
| GET | `/info` | Model metadata and feature importance |
| GET | `/health` | Service health check |

### Orchestrator - Live Demo Control (Port 8002)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/set_traffic` | Set traffic pattern and intensity |
| POST | `/api/set_strategy` | Set load balancing strategy |
| POST | `/api/inject_chaos` | Kill a backend container (chaos testing) |
| GET | `/api/status` | Current system status |

---

## 🚀 How to Run the Project

### Prerequisites: Install Docker (Windows)

If you have nothing installed, you need Docker Desktop. Follow these steps:

**Step 1: Download Docker Desktop**
1. Go to https://www.docker.com/products/docker-desktop/
2. Click **Download for Windows**
3. Run the installer (`Docker Desktop Installer.exe`)

**Step 2: Enable WSL 2 (Required for Windows)**
1. Open **PowerShell as Administrator**
2. Run:
```powershell
wsl --install
```
3. Restart your computer when prompted

**Step 3: Verify Docker Installation**
1. Open **Docker Desktop** (search in Start menu)
2. Wait for it to say "Docker Desktop is running"
3. Open a new terminal and verify:
```bash
docker --version
docker compose version
```

You should see something like:
```
Docker version 27.x.x
Docker Compose version v2.x.x
```

---

### Launch the Infrastructure

**Step 4: Start All Services**
Navigate to the project folder and run:
```bash
cd "C:\AppsNew\SE Project"
docker compose up --build
```

This will:
- Build and start 3 backend server containers
- Start the load balancer gateway
- Start the ML prediction service
- Start the auto-scaler
- Start the Live Demo Control API
- Start the Streamlit dashboard

**Step 5: Access the Application**

| Service | URL |
|---------|-----|
| **Live Dashboard (Control Panel)** | http://localhost:8501 |
| **Gateway API (Load Balancer)** | http://localhost:8000/docs |
| **ML Prediction Service** | http://localhost:8001/docs |
| **Live Demo Control API** | http://localhost:8002/docs |

---

### Stop the Infrastructure

To shut down all services gracefully:
```bash
docker compose down
```

To stop AND remove all containers, networks, and volumes:
```bash
docker compose down -v
```

---

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `docker: command not found` | Docker Desktop isn't running. Open Docker Desktop and wait for "running" status. |
| `docker compose` fails | Use `docker-compose` (with hyphen) on older versions |
| Port already in use | Another application is using port 8501, 8000, or 8001. Stop the other app or edit `docker-compose.yml` |
| WSL 2 error | Run `wsl --update` in PowerShell as Administrator |

---

## Services

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
| **Scikit-learn** 🧠 | Not applicable anymore. We use a custom **weighted ensemble** model in Python that predicts server health (0-1) based on CPU, memory, error rate, success rate, latency, and active connections. |

---

## AI-Powered Load Balancing: How It Works

The `ai_powered` routing strategy uses **weighted probabilistic selection** based on real-time health scores from the ML service.

### Data Sources
1. **Gateway stats** - request counts, error counts, active connections per server
2. **Orchestrator metrics** - container CPU usage from Docker stats
3. **Health checks** - latency and availability per backend

### Health Score Algorithm
```
health_score = 1.0
  - penalties for: high CPU (>80%), high memory (>85%), high error rate (>5%), high latency, too many connections
  + bonuses for: high success rate, low connection count
```

### Selection Process
1. ML service collects metrics every 5 seconds
2. Gateway syncs health scores every 10 seconds
3. When a request comes in, servers are selected with probability proportional to their health score
4. Unhealthy servers (score < 0.3) are temporarily excluded

### Why It Works
- Traffic flows to servers that can handle it
- Failing servers naturally get less traffic
- Auto-scaler gets time to spin up new containers
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
                    │       🧠 ML SERVICE (Health Prediction)             │
                    │     • Weighted ensemble model                       │
                    │     • Predicts health scores based on metrics       │
                    │     • Synced to gateway every 10 seconds            │
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

## 📄 Software Requirements Specification (SRS)

This project includes a formal SRS document following IEEE 29148 standards.

| Document | Description |
|----------|-------------|
| `docs/SRS_IEEE_29148.md` | Markdown version of the SRS document |
| `docs/SRS_IEEE_SE_project.pdf` | PDF version for submission |

**Contents of the SRS:**
- Introduction (Purpose, Scope, Definitions)
- Overall Description (Product Perspective, User Classes)
- Specific Requirements (Functional, Non-Functional)
- Supporting Information (Appendices, References)

---

## License

Academic Project - SE Department