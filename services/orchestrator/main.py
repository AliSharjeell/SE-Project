"""
Orchestrator Service - Live Demo Control API

Provides control endpoints for the Live Demo Control Panel.
"""

import random
import threading
from typing import Optional
from datetime import datetime

import docker
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Orchestrator - Live Demo Control", version="1.0.0")

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
    "routing_strategy": "round_robin",
    "last_chaos": None,
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
    return {
        "traffic_pattern": state["traffic_pattern"],
        "traffic_intensity": state["traffic_intensity"],
        "routing_strategy": state["routing_strategy"],
        "last_chaos": state["last_chaos"],
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
    valid_strategies = ["round_robin", "least_connections", "ai_powered"]
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
    """Kill a random backend container to test system recovery."""
    import random
    import subprocess

    # Try to list and kill backend containers
    container_names = list_backend_containers()

    if not container_names:
        # No Docker access - simulate chaos for demo purposes
        simulated_containers = ["backend-2", "backend-3", "backend-4"]
        container_name = random.choice(simulated_containers)
        state["last_chaos"] = {
            "container": container_name,
            "timestamp": datetime.now().isoformat(),
            "simulated": True
        }
        log_event("chaos_injection", f"[SIMULATED] Chaos injected on {container_name}", {"container": container_name, "simulated": True})

        return ChaosResult(
            success=True,
            container_killed=container_name,
            message=f"Chaos injected on {container_name} (simulated - Docker not accessible from container)"
        )

    if len(container_names) <= 1:
        return ChaosResult(
            success=False,
            message="Cannot kill the last remaining backend container"
        )

    # Select a random container to kill (exclude the first one)
    victim_name = random.choice(container_names[1:]) if len(container_names) > 1 else container_names[0]

    # Try to kill the container
    if kill_container(victim_name):
        container_name = victim_name
    else:
        # If kill fails, simulate the event
        container_name = victim_name
        state["last_chaos"] = {
            "container": container_name,
            "timestamp": datetime.now().isoformat(),
            "simulated": True
        }
        log_event("chaos_injection", f"[SIMULATED] Chaos injected on {container_name}", {"container": container_name, "simulated": True})

        return ChaosResult(
            success=True,
            container_killed=container_name,
            message=f"Chaos injected on {container_name} (simulated)"
        )

    state["last_chaos"] = {
        "container": container_name,
        "timestamp": datetime.now().isoformat(),
    }
    log_event("chaos_injection", f"Container {container_name} terminated for chaos testing", {"container": container_name})

    return ChaosResult(
        success=True,
        container_killed=container_name,
        message=f"Container {container_name} killed. System should recover by routing to healthy servers."
    )


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "orchestrator"}


@app.get("/api/debug")
async def debug_info():
    """Debug endpoint for Docker connection status."""
    import sys
    client = get_docker_client()
    if client:
        try:
            client.ping()
            containers = client.containers.list()
            backend_containers = [c.name for c in containers if c.name.startswith("backend-")]
            return {
                "docker_connected": True,
                "all_containers": [c.name for c in containers],
                "backend_containers": backend_containers,
                "python_version": sys.version
            }
        except Exception as e:
            return {"docker_connected": True, "error": str(e)}
    return {"docker_connected": False, "client": None}


@app.get("/api/events")
async def get_events(limit: int = 10):
    """Get recent system events for audit log."""
    events = event_log[-limit:] if limit <= len(event_log) else event_log
    return {"events": events, "total": len(event_log)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)