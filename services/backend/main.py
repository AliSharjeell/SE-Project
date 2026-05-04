import asyncio
import os
import time
import random
import psutil
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

start_time = datetime.now()
_cpu_percent_cache = 0.0
_cpu_percent_last_check = 0.0
_degraded_until = 0.0

def get_server_id() -> str:
    return os.environ.get("HOSTNAME", "unknown")

def is_degraded() -> bool:
    return time.time() < _degraded_until

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "server_id": get_server_id(),
        "degraded": is_degraded()
    }

@app.post("/process")
async def process(request: dict):
    request_id = request.get("request_id", "")
    payload = request.get("payload", "")

    processing_time = random.uniform(0.8, 1.2) if is_degraded() else random.uniform(0.05, 0.2)
    await asyncio.sleep(processing_time)

    return {
        "processed": True,
        "server_id": get_server_id(),
        "processing_time_ms": round(processing_time * 1000, 2),
        "degraded": is_degraded()
    }

@app.get("/metrics")
async def metrics():
    uptime = (datetime.now() - start_time).total_seconds()

    # Non-blocking CPU read: use cached value or instantaneous read without interval
    global _cpu_percent_cache, _cpu_percent_last_check
    now = time.time()
    if now - _cpu_percent_last_check > 1.0:
        _cpu_percent_cache = psutil.cpu_percent(interval=None)
        _cpu_percent_last_check = now

    degraded = is_degraded()

    return {
        "cpu_usage": round(random.uniform(85, 98) if degraded else _cpu_percent_cache, 2),
        "memory_usage": round(random.uniform(75, 90) if degraded else psutil.virtual_memory().percent, 2),
        "response_time": round(random.uniform(800, 1200) if degraded else random.uniform(10, 50), 2),
        "active_connections": random.randint(60, 120) if degraded else random.randint(1, 100),
        "uptime_seconds": round(uptime, 2),
        "degraded": degraded
    }

@app.post("/chaos/degrade")
async def degrade(config: dict | None = None):
    global _degraded_until
    duration_seconds = int((config or {}).get("duration_seconds", 120))
    _degraded_until = time.time() + max(10, min(duration_seconds, 600))
    return {
        "status": "degraded",
        "server_id": get_server_id(),
        "duration_seconds": duration_seconds
    }

@app.post("/chaos/recover")
async def recover():
    global _degraded_until
    _degraded_until = 0.0
    return {"status": "recovered", "server_id": get_server_id()}
