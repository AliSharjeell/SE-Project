"""
Auto-scaler Controller Service

Monitors backend container metrics and automatically scales the backend service
based on CPU utilization thresholds.
"""

import time
import threading
import statistics
from datetime import datetime
from typing import Dict, List, Optional

import docker
import requests
from flask import Flask, jsonify

# Configuration
GATEWAY_URL = "http://gateway:8000"
BACKEND_CONTAINER_PREFIX = "backend-"
METRICS_INTERVAL = 10  # seconds
SCALE_UP_THRESHOLD = 75.0  # CPU %
SCALE_DOWN_THRESHOLD = 25.0  # CPU %
MIN_SERVERS = 1
MAX_SERVERS = 10
COOLDOWN_SECONDS = 30

# Initialize Flask app
app = Flask(__name__)

# Initialize Docker client
docker_client = docker.from_env()

# State tracking
state = {
    "last_scale_action": None,
    "last_scale_time": None,
    "scale_direction": None,
    "total_scale_ups": 0,
    "total_scale_downs": 0,
    "current_servers": 0,
    "average_cpu": 0.0,
    "is_monitoring": True
}
state_lock = threading.Lock()


def get_backend_containers() -> List[docker.models.containers.Container]:
    """Get all running backend containers."""
    try:
        containers = docker_client.containers.list(
            filters={"name": lambda name: name.startswith(BACKEND_CONTAINER_PREFIX)}
        )
        return [c for c in containers if c.status == "running"]
    except Exception as e:
        print(f"Error listing containers: {e}")
        return []


def get_container_stats(container: docker.models.containers.Container) -> Optional[Dict]:
    """Get stats for a single container."""
    try:
        stats = container.stats(stream=False)
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_cpu_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus", 1)

        if system_cpu_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_cpu_delta) * num_cpus * 100.0
        else:
            cpu_percent = 0.0

        memory_usage = stats["memory_stats"].get("usage", 0)
        memory_limit = stats["memory_stats"].get("limit", 1)
        memory_percent = (memory_usage / memory_limit) * 100.0

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_usage_mb": memory_usage / (1024 * 1024)
        }
    except Exception as e:
        print(f"Error getting stats for container {container.name}: {e}")
        return None


def get_average_cpu() -> float:
    """Calculate average CPU usage across all backend containers."""
    containers = get_backend_containers()
    if not containers:
        return 0.0

    cpu_values = []
    for container in containers:
        stats = get_container_stats(container)
        if stats:
            cpu_values.append(stats["cpu_percent"])

    if not cpu_values:
        return 0.0

    return statistics.mean(cpu_values)


def get_container_count() -> int:
    """Get the number of running backend containers."""
    return len(get_backend_containers())


def register_with_gateway(container_name: str) -> bool:
    """Register a new container with the gateway."""
    try:
        response = requests.post(
            f"{GATEWAY_URL}/servers/register",
            json={"name": container_name, "port": 5000},
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error registering with gateway: {e}")
        return False


def create_container() -> Optional[str]:
    """Create and start a new backend container."""
    try:
        current_containers = get_backend_containers()
        next_num = len(current_containers) + 1
        container_name = f"{BACKEND_CONTAINER_PREFIX}{next_num}"

        # Pull the backend image if not present
        try:
            docker_client.images.get("backend:latest")
        except docker.errors.NotFound:
            print("Backend image not found. Please ensure it exists.")
            return None

        container = docker_client.containers.run(
            "backend:latest",
            detach=True,
            name=container_name,
            ports={"5000/tcp": None},
            restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}
        )

        time.sleep(2)  # Allow container to start

        if register_with_gateway(container_name):
            print(f"Successfully created and registered container: {container_name}")
            return container_name
        else:
            container.stop()
            container.remove()
            return None

    except Exception as e:
        print(f"Error creating container: {e}")
        return None


def remove_container(container_name: str) -> bool:
    """Stop and remove a backend container."""
    try:
        container = docker_client.containers.get(container_name)
        container.stop(timeout=5)
        container.remove()
        print(f"Successfully removed container: {container_name}")
        return True
    except Exception as e:
        print(f"Error removing container: {e}")
        return False


def scale_up() -> bool:
    """Scale up by one container."""
    with state_lock:
        now = datetime.now()

        if state["current_servers"] >= MAX_SERVERS:
            print("Maximum servers reached")
            return False

        if state["last_scale_time"]:
            time_since_last = (now - state["last_scale_time"]).total_seconds()
            if time_since_last < COOLDOWN_SECONDS:
                print(f"Cooldown active. {COOLDOWN_SECONDS - time_since_last:.0f}s remaining")
                return False

        new_container = create_container()
        if new_container:
            state["last_scale_action"] = "scale_up"
            state["last_scale_time"] = now
            state["scale_direction"] = "up"
            state["total_scale_ups"] += 1
            state["current_servers"] = get_container_count()
            print(f"Scaled up. New count: {state['current_servers']}")
            return True

        return False


def scale_down() -> bool:
    """Scale down by one container."""
    with state_lock:
        now = datetime.now()

        if state["current_servers"] <= MIN_SERVERS:
            print("Minimum servers reached")
            return False

        if state["last_scale_time"]:
            time_since_last = (now - state["last_scale_time"]).total_seconds()
            if time_since_last < COOLDOWN_SECONDS:
                print(f"Cooldown active. {COOLDOWN_SECONDS - time_since_last:.0f}s remaining")
                return False

        containers = get_backend_containers()
        if containers:
            # Remove the highest numbered container
            containers.sort(key=lambda c: c.name, reverse=True)
            container_to_remove = containers[0]

            if remove_container(container_to_remove.name):
                state["last_scale_action"] = "scale_down"
                state["last_scale_time"] = now
                state["scale_direction"] = "down"
                state["total_scale_downs"] += 1
                state["current_servers"] = get_container_count()
                print(f"Scaled down. New count: {state['current_servers']}")
                return True

        return False


def monitoring_loop():
    """Background loop that monitors metrics and triggers scaling."""
    print("Starting auto-scaler monitoring loop...")

    while state["is_monitoring"]:
        try:
            avg_cpu = get_average_cpu()
            current_count = get_container_count()

            with state_lock:
                state["average_cpu"] = avg_cpu
                state["current_servers"] = current_count

            print(f"Metrics - CPUs: {avg_cpu:.1f}%, Containers: {current_count}")

            with state_lock:
                cooldown_active = False
                if state["last_scale_time"]:
                    time_since = (datetime.now() - state["last_scale_time"]).total_seconds()
                    if time_since < COOLDOWN_SECONDS:
                        cooldown_active = True

            if not cooldown_active:
                if avg_cpu > SCALE_UP_THRESHOLD and current_count < MAX_SERVERS:
                    print(f"CPU ({avg_cpu:.1f}%) above threshold ({SCALE_UP_THRESHOLD}%) - scaling up")
                    scale_up()

                elif avg_cpu < SCALE_DOWN_THRESHOLD and current_count > MIN_SERVERS:
                    print(f"CPU ({avg_cpu:.1f}%) below threshold ({SCALE_DOWN_THRESHOLD}%) - scaling down")
                    scale_down()

        except Exception as e:
            print(f"Error in monitoring loop: {e}")

        time.sleep(METRICS_INTERVAL)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "autoscaler"}), 200


@app.route("/status", methods=["GET"])
def status():
    """Get current scaling status and statistics."""
    with state_lock:
        response = {
            "status": "running",
            "current_servers": state["current_servers"],
            "average_cpu": round(state["average_cpu"], 2),
            "min_servers": MIN_SERVERS,
            "max_servers": MAX_SERVERS,
            "scale_up_threshold": SCALE_UP_THRESHOLD,
            "scale_down_threshold": SCALE_DOWN_THRESHOLD,
            "total_scale_ups": state["total_scale_ups"],
            "total_scale_downs": state["total_scale_downs"],
            "last_action": state["last_scale_action"],
            "last_action_time": state["last_scale_time"].isoformat() if state["last_scale_time"] else None,
            "cooldown_seconds": COOLDOWN_SECONDS,
            "monitoring_interval_seconds": METRICS_INTERVAL
        }

    return jsonify(response), 200


@app.route("/scale/up", methods=["POST"])
def manual_scale_up():
    """Manual scale up endpoint."""
    success = scale_up()
    if success:
        return jsonify({"status": "success", "action": "scale_up", "servers": state["current_servers"]}), 200
    else:
        return jsonify({"status": "failed", "reason": "Cannot scale up (max servers or cooldown)"}), 400


@app.route("/scale/down", methods=["POST"])
def manual_scale_down():
    """Manual scale down endpoint."""
    success = scale_down()
    if success:
        return jsonify({"status": "success", "action": "scale_down", "servers": state["current_servers"]}), 200
    else:
        return jsonify({"status": "failed", "reason": "Cannot scale down (min servers or cooldown)"}), 400


if __name__ == "__main__":
    # Initialize server count
    state["current_servers"] = get_container_count()

    # Start monitoring in background thread
    monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitor_thread.start()

    # Start Flask app
    print("Auto-scaler controller starting on port 8000...")
    app.run(host="0.0.0.0", port=8000)