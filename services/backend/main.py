import os
import time
import random
import psutil
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

start_time = datetime.now()

def get_server_id() -> str:
    return os.environ.get("HOSTNAME", "unknown")

@app.get("/health")
async def health():
    return {"status": "healthy", "server_id": get_server_id()}

@app.post("/process")
async def process(request: dict):
    request_id = request.get("request_id", "")
    payload = request.get("payload", "")

    processing_time = random.uniform(0.05, 0.2)
    time.sleep(processing_time)

    return {
        "processed": True,
        "server_id": get_server_id(),
        "processing_time_ms": round(processing_time * 1000, 2)
    }

@app.get("/metrics")
async def metrics():
    uptime = (datetime.now() - start_time).total_seconds()

    return {
        "cpu_usage": round(psutil.cpu_percent(interval=0.1), 2),
        "memory_usage": round(psutil.virtual_memory().percent, 2),
        "response_time": round(random.uniform(10, 50), 2),
        "active_connections": random.randint(1, 100),
        "uptime_seconds": round(uptime, 2)
    }