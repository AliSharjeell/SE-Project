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

# Docker client
docker_client = docker.from_env()

# State
state = {
    "traffic_pattern": "constant",
    "traffic_intensity": 100,
    "routing_strategy": "round_robin",
    "last_chaos": None,
}


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
        containers = docker_client.containers.list(
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)