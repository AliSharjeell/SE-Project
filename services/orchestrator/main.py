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
        import os
        # Use explicit socket path
        _docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
    return _docker_client

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
        # Find all backend containers
        containers = get_docker_client().containers.list(
            filters={"name": lambda name: name.startswith("backend-")}
        )

        running_backends = [c for c in containers if c.status == "running"]

        if not running_backends:
            return ChaosResult(
                success=False,
                message="No running backend containers found"
            )

        if len(running_backends) <= 1:
            return ChaosResult(
                success=False,
                message="Cannot kill the last remaining backend container"
            )

        # Select a random container to kill
        victim = random.choice(running_backends)
        container_name = victim.name

        # Force kill the container
        victim.kill(signal="SIGKILL")

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