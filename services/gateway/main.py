import os
import httpx
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from load_balancer import LoadBalancer, RoutingStrategy


class RouteRequest(BaseModel):
    strategy: RoutingStrategy
    path: str = "/"
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Any = None


class RouteResponse(BaseModel):
    server: str
    status_code: int
    response: Dict[str, Any]


class ServerRegistration(BaseModel):
    host: str
    port: int
    server_id: str


class ServerInfo(BaseModel):
    server_id: str
    host: str
    port: int
    url: str
    healthy: bool = True
    active_connections: int = 0


class StatsResponse(BaseModel):
    strategy_distribution: Dict[str, int]
    total_requests: int
    servers: Dict[str, Dict[str, Any]]


# Initialize load balancer
load_balancer = LoadBalancer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load initial backend URLs from environment variable
    backend_urls = os.getenv("BACKEND_URLS", "")
    if backend_urls:
        for url in backend_urls.split(","):
            url = url.strip()
            if url:
                load_balancer.add_server(url)
    yield


app = FastAPI(
    title="AI Infrastructure Gateway",
    description="Load balancer gateway for AI Infrastructure Manager microservices",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/route", response_model=RouteResponse)
async def route_request(request: RouteRequest):
    """
    Route a request to a backend server using the specified strategy.
    """
    if not load_balancer.get_servers():
        raise HTTPException(status_code=503, detail="No backend servers available")

    # Select a server based on the routing strategy
    selected_server = load_balancer.select_server(request.strategy)
    if not selected_server:
        raise HTTPException(status_code=503, detail="No healthy servers available")

    target_url = f"{selected_server}{request.path}"

    try:
        load_balancer.increment_connections(selected_server)

        async with httpx.AsyncClient(timeout=30.0) as client:
            httpx_response = await client.request(
                method=request.method,
                url=target_url,
                headers=request.headers,
                json=request.body if request.body else None,
            )

        load_balancer.decrement_connections(selected_server)
        load_balancer.record_request(selected_server, httpx_response.status_code)

        return RouteResponse(
            server=selected_server,
            status_code=httpx_response.status_code,
            response=httpx_response.json() if httpx_response.headers.get("content-type", "").startswith("application/json") else {"message": "Response received"},
        )

    except httpx.HTTPError as e:
        load_balancer.decrement_connections(selected_server)
        load_balancer.mark_unhealthy(selected_server)
        raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")


@app.get("/servers", response_model=list[ServerInfo])
async def get_servers():
    """
    Returns list of known backend servers with their health status.
    """
    return load_balancer.get_server_info()


@app.post("/servers/register")
async def register_server(registration: ServerRegistration):
    """
    Register a new backend server.
    """
    url = f"http://{registration.host}:{registration.port}"
    success = load_balancer.add_server(url, server_id=registration.server_id)

    if not success:
        raise HTTPException(status_code=400, detail="Server already registered")

    return {"message": "Server registered successfully", "url": url}


@app.delete("/servers/{server_id}")
async def remove_server(server_id: str):
    """
    Remove a backend server from the pool.
    """
    success = load_balancer.remove_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail="Server not found")

    return {"message": "Server removed successfully"}


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Returns routing statistics and strategy distribution.
    """
    return load_balancer.get_stats()


@app.get("/health")
async def health_check():
    """
    Health check endpoint for the gateway.
    """
    return {"status": "healthy", "servers_available": len(load_balancer.get_servers())}


@app.get("/generate-load")
async def generate_load(strategy: str = "ai_powered"):
    """
    Endpoint that generates load by routing a request through the load balancer.
    This exercises the load balancing logic and counts towards stats.
    Uses 'ai_powered' strategy by default.
    """
    from load_balancer import RoutingStrategy

    if not load_balancer.get_servers():
        raise HTTPException(status_code=503, detail="No backend servers available")

    try:
        strategy_enum = RoutingStrategy(strategy)
    except ValueError:
        strategy_enum = RoutingStrategy.AI_POWERED

    # Select a server using specified strategy
    selected_server = load_balancer.select_server(strategy_enum)
    if not selected_server:
        raise HTTPException(status_code=503, detail="No healthy servers available")

    # Record this as a request
    load_balancer.increment_connections(selected_server)
    load_balancer.record_request(selected_server, 200)
    load_balancer.decrement_connections(selected_server)

    return {
        "status": "ok",
        "routed_to": selected_server,
        "strategy": strategy_enum.value
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)