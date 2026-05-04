"""
Orchestrator Service - Live Demo Control API

Provides control endpoints for the Live Demo Control Panel.
"""

import random
import threading
import time
from typing import Optional
from datetime import datetime

import docker
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Orchestrator - Live Demo Control", version="1.0.0")

BACKEND_NAMES = ["backend-1", "backend-2", "backend-3"]
BACKEND_URLS = {name: f"http://{name}:8000" for name in BACKEND_NAMES}

# Docker client - lazy initialization
_docker_client = None

def get_docker_client():
    global _docker_client
    if _docker_client is None:
        import docker
        try:
            # Try Windows named pipe first
            _docker_client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
            _docker_client.ping()
        except Exception as e1:
            print(f"Named pipe failed: {e1}")
            try:
                # Fallback: TCP to host.docker.internal
                _docker_client = docker.DockerClient(base_url='tcp://host.docker.internal:2375')
                _docker_client.ping()
            except Exception as e2:
                print(f"TCP host.docker.internal failed: {e2}")
                try:
                    # Fallback: 127.0.0.1:2375
                    _docker_client = docker.DockerClient(base_url='tcp://127.0.0.1:2375')
                    _docker_client.ping()
                except Exception as e3:
                    print(f"All Docker connections failed: {e1}, {e2}, {e3}")
                    _docker_client = None
    return _docker_client


def simulate_chaos():
    """Simulate chaos injection (for Docker Desktop on Windows without TCP access)."""
    import random
    import subprocess

    # Try to get backend containers
    backend_ids = []
    try:
        result = subprocess.run(
            ["powershell", "-Command", "docker ps --filter 'name=backend-' --format '{{.Names}}'"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            backend_ids = [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
    except:
        pass

    # Try killing a container (may fail if no docker access)
    if backend_ids and len(backend_ids) > 1:
        try:
            # Pick a random backend that's not the first one
            victim = random.choice(backend_ids[1:]) if len(backend_ids) > 1 else backend_ids[0]
            subprocess.run(["powershell", "-Command", f"docker kill {victim}"],
                          capture_output=True, timeout=10)
            return victim, True
        except:
            pass

    # If all else fails, simulate the event
    return "backend-2", False  # Simulated


def list_backend_containers():
    """List running backend containers."""
    # Try Python Docker SDK first
    client = get_docker_client()
    if client:
        try:
            containers = client.containers.list()
            return [c.name for c in containers if c.name.startswith("backend-") and c.status == "running"]
        except Exception as e:
            print(f"Docker SDK error: {e}")

    # Fallback: try subprocess
    import subprocess
    try:
        result = subprocess.run(
            ["powershell", "-Command", "docker ps --filter 'name=backend-' --format '{{.Names}}'"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
    except Exception as e:
        print(f"Subprocess error: {e}")

    return []


def kill_container(name: str) -> bool:
    """Kill a container by name."""
    client = get_docker_client()
    if client:
        try:
            container = client.containers.get(name)
            container.kill()
            return True
        except Exception as e:
            print(f"Docker SDK kill error: {e}")

    # Try subprocess
    import subprocess
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"docker kill {name}"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Subprocess kill error: {e}")
        return False

# State
state = {
    "traffic_pattern": "constant",
    "traffic_intensity": 100,
    "routing_strategy": "ai_powered",
    "last_chaos": None,
    "degraded_backend": None,
    "degraded_until": 0.0,
}

# Event log (last 50 events)
event_log = []
MAX_EVENTS = 50

def log_event(event_type: str, message: str, details: dict = None):
    """Log a system event to the audit trail."""
    import threading
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "message": message,
        "details": details or {},
    }
    event_log.append(entry)
    if len(event_log) > MAX_EVENTS:
        event_log.pop(0)

def get_active_degraded_backend() -> Optional[str]:
    """Return the active degraded backend, clearing expired demo state."""
    if state.get("degraded_backend") and time.time() < state.get("degraded_until", 0):
        return state["degraded_backend"]
    state["degraded_backend"] = None
    state["degraded_until"] = 0.0
    return None

async def degrade_backend(name: str, duration_seconds: int = 120) -> bool:
    """Ask a backend to slow itself down for a visible routing demo."""
    url = BACKEND_URLS.get(name)
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(
                f"{url}/chaos/degrade",
                json={"duration_seconds": duration_seconds}
            )
        return response.status_code == 200
    except Exception as e:
        print(f"Backend degradation failed for {name}: {e}")
        return False

async def recover_backend(name: str) -> bool:
    url = BACKEND_URLS.get(name)
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(f"{url}/chaos/recover")
        return response.status_code == 200
    except Exception as e:
        print(f"Backend recovery failed for {name}: {e}")
        return False


class TrafficConfig(BaseModel):
    pattern: str  # constant, ramp, spike, sine_wave, burst
    intensity: int  # RPS (requests per second)


class StrategyConfig(BaseModel):
    strategy: str  # round_robin, least_connections, ai_powered


class ChaosResult(BaseModel):
    success: bool
    container_killed: Optional[str] = None
    message: str


@app.get("/api/status")
async def get_status():
    """Get current system status."""
    degraded_backend = get_active_degraded_backend()
    return {
        "traffic_pattern": state["traffic_pattern"],
        "traffic_intensity": state["traffic_intensity"],
        "routing_strategy": state["routing_strategy"],
        "last_chaos": state["last_chaos"],
        "degraded_backend": degraded_backend,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/set_traffic")
async def set_traffic(config: TrafficConfig):
    """Set traffic pattern and intensity."""
    valid_patterns = ["constant", "ramp", "spike", "sine_wave", "burst"]
    if config.pattern not in valid_patterns:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pattern. Must be one of: {valid_patterns}"
        )

    if config.intensity < 10 or config.intensity > 10000:
        raise HTTPException(
            status_code=400,
            detail="Intensity must be between 10 and 10000 RPS"
        )

    state["traffic_pattern"] = config.pattern
    state["traffic_intensity"] = config.intensity
    log_event("traffic_change", f"Traffic pattern set to {config.pattern}", {"pattern": config.pattern, "intensity": config.intensity})

    return {
        "success": True,
        "pattern": config.pattern,
        "intensity": config.intensity,
        "message": f"Traffic set to {config.pattern} at {config.intensity} RPS",
    }


@app.post("/api/set_strategy")
async def set_strategy(config: StrategyConfig):
    """Set load balancing strategy."""
    valid_strategies = ["round_robin", "least_connections", "ai_powered", "off"]
    if config.strategy not in valid_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Must be one of: {valid_strategies}"
        )

    state["routing_strategy"] = config.strategy
    log_event("strategy_change", f"Routing strategy changed to {config.strategy}", {"strategy": config.strategy})

    return {
        "success": True,
        "strategy": config.strategy,
        "message": f"Routing strategy set to {config.strategy}",
    }


@app.post("/api/inject_chaos", response_model=ChaosResult)
async def inject_chaos():
    """Degrade a random backend so AI routing has a visible advantage."""
    container_name = random.choice(BACKEND_NAMES)
    duration_seconds = 120

    if not await degrade_backend(container_name, duration_seconds):
        return ChaosResult(
            success=False,
            container_killed=container_name,
            message=f"Could not degrade {container_name}"
        )

    state["degraded_backend"] = container_name
    state["degraded_until"] = time.time() + duration_seconds
    state["last_chaos"] = {
        "container": container_name,
        "timestamp": datetime.now().isoformat(),
        "mode": "degraded"
    }
    log_event("chaos_injection", f"Backend {container_name} degraded for routing demo", {"container": container_name, "mode": "degraded"})

    return ChaosResult(
        success=True,
        container_killed=container_name,
        message=f"Backend {container_name} degraded for {duration_seconds}s. AI routing should prefer healthier servers."
    )


@app.post("/api/recover")
async def recover_all():
    """Recover all degraded backend demo state."""
    results = {name: await recover_backend(name) for name in BACKEND_NAMES}
    state["degraded_backend"] = None
    state["degraded_until"] = 0.0
    state["last_chaos"] = None
    log_event("recovery", "All backend degradation cleared", {"results": results})
    return {"success": all(results.values()), "results": results}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "orchestrator"}


@app.get("/api/metrics")
async def get_metrics():
    """Get metrics - uses traffic intensity as proxy for CPU load.
    Simulates load distribution based on the active routing strategy
    so the dashboard reflects actual traffic patterns.
    """
    traffic_intensity = state.get("traffic_intensity", 100)
    strategy = state.get("routing_strategy", "ai_powered")
    degraded_backend = get_active_degraded_backend()

    metrics = {}
    base_load = min(traffic_intensity / 100, 95)  # Cap at 95%

    for i in range(1, 4):
        server_name = f"backend-{i}"
        variation = random.uniform(-15, 15)

        if strategy == "off":
            # OFF mode: all traffic goes to the first server
            if i == 1:
                cpu = max(5, min(98, base_load + variation))
            else:
                # Idle servers show low baseline CPU
                cpu = max(5, min(20, 10 + variation * 0.3))
        else:
            # Load-balanced modes: distribute load across all servers
            cpu = max(5, min(98, base_load + variation))

        if server_name == degraded_backend:
            cpu = random.uniform(88, 98)

        metrics[server_name] = round(cpu, 1)

    return {
        "metrics": metrics,
        "source": "simulated_from_traffic",
        "traffic_intensity": traffic_intensity,
        "routing_strategy": strategy,
        "degraded_backend": degraded_backend,
    }


@app.get("/api/events")
async def get_events(limit: int = 10):
    """Get recent system events for audit log."""
    events = event_log[-limit:] if limit <= len(event_log) else event_log
    return {"events": events, "total": len(event_log)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
