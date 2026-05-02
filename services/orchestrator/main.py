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
        _docker_client = docker.from_env()
    return _docker_client


def get_docker_socket_containers():
    """Get containers via Docker socket API."""
    import urllib.request
    import json
    try:
        # Use Unix socket to query Docker API
        sock = '/var/run/docker.sock'
        req = urllib.request.Request(f"http://unix.sock/containers/json?filters={{\"name\":{{\"backend-\":true}}}}",
                                      headers={'Content-Type': 'application/json'})
        # This won't work directly, need socket path workaround
        return []
    except:
        pass
    # Fallback: use docker CLI if available
    return list_backend_containers_cli()


def list_backend_containers_cli():
    """List backend containers using docker CLI."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=backend-", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
        return []
    except Exception as e:
        print(f"Error listing containers: {e}")
        return []


def list_backend_containers():
    """List running backend container names."""
    import subprocess
    try:
        # Use docker CLI directly
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=backend-", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=15,
            shell=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
        return []
    except Exception as e:
        print(f"Error listing containers: {e}")
        return []


def kill_container(name: str) -> bool:
    """Kill a container by name."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "kill", name],
            capture_output=True,
            text=True,
            timeout=15,
            shell=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error killing container: {e}")
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
    try:
        # Find all backend containers using CLI
        container_names = list_backend_containers()

        if not container_names:
            return ChaosResult(
                success=False,
                message="No running backend containers found"
            )

        if len(container_names) <= 1:
            return ChaosResult(
                success=False,
                message="Cannot kill the last remaining backend container"
            )

        # Select a random container to kill (exclude the first one)
        victim_name = random.choice(container_names[1:]) if len(container_names) > 1 else container_names[0]

        # Kill the container using CLI
        if kill_container(victim_name):
            container_name = victim_name
        else:
            return ChaosResult(
                success=False,
                message=f"Failed to kill container {victim_name}"
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

    except docker.errors.APIError as e:
        return ChaosResult(
            success=False,
            message=f"Docker API error: {str(e)}"
        )
    except Exception as e:
        return ChaosResult(
            success=False,
            message=f"Error: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "orchestrator"}


@app.get("/api/events")
async def get_events(limit: int = 10):
    """Get recent system events for audit log."""
    events = event_log[-limit:] if limit <= len(event_log) else event_log
    return {"events": events, "total": len(event_log)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)