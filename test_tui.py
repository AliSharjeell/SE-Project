#!/usr/bin/env python3
"""
TUI Testing Interface for AI-Driven Infrastructure Manager
Interactive terminal-based testing and demonstration.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import datetime
import time
import numpy as np
import pandas as pd

from components import TrafficGenerator, MonitoringSystem, LoadBalancer, AutoScaler
from components.monitor import ServerMetrics
from components.load_balancer import BackendServer, LoadBalancerStrategy
from components.auto_scaler import AutoScalerConfig
from models import TrafficPredictor, AnomalyDetector
from orchestrator import InfrastructureOrchestrator


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.GREEN}[+] {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.RED}[-] {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.CYAN}[*] {text}{Colors.ENDC}")


def test_traffic_generator():
    print_header("Traffic Generator Tests")

    tg = TrafficGenerator(base_rate=10, max_rate=100)

    print_info("Generating requests with different patterns...")

    req = tg.generate_request()
    print_success(f"Basic request: ID={req.request_id[:20]}..., Size={req.payload_size} bytes")

    req2 = tg.generate_constant()
    print_success(f"Constant pattern: ID={req2.request_id[:20]}...")

    req3 = tg.generate_spike(peak_rate=100, progress=0.5)
    print_success(f"Spike pattern: ID={req3.request_id[:20]}...")

    req4 = tg.generate_sine_wave()
    print_success(f"Sine wave pattern: ID={req4.request_id[:20]}...")

    burst = tg.generate_burst(burst_size=5)
    print_success(f"Burst of {len(burst)} requests generated")

    return True


def test_monitoring_system():
    print_header("Monitoring System Tests")

    ms = MonitoringSystem(history_size=100)

    print_info("Adding metrics...")
    for i in range(10):
        metric = ServerMetrics(
            cpu_usage=50 + i * 3,
            memory_usage=60 + i * 2,
            response_time=100 + i * 10,
            request_rate=100 + i * 5,
            active_connections=10 + i,
            timestamp=datetime.datetime.now()
        )
        ms.add_metric(metric)

    stats = ms.get_all_stats()
    print_success(f"CPU Usage - Avg: {stats['cpu_usage']['avg']:.1f}%, Max: {stats['cpu_usage']['max']:.1f}%")
    print_success(f"Response Time - Avg: {stats['response_time']['avg']:.1f}ms, P95: {stats['response_time']['p95']:.1f}ms")
    print_success(f"Active Connections - Avg: {stats['active_connections']['avg']:.1f}")

    latest = ms.get_latest()
    print_success(f"Latest metrics: CPU={latest.cpu_usage:.1f}%, RT={latest.response_time:.1f}ms")

    return True


def test_load_balancer():
    print_header("Load Balancer Tests")

    lb = LoadBalancer()

    print_info("Adding servers...")
    lb.add_server(BackendServer(id='server-1', host='192.168.1.10', port=8001, cpu_usage=50.0, active_connections=10, avg_response_time=100.0))
    lb.add_server(BackendServer(id='server-2', host='192.168.1.11', port=8002, cpu_usage=50.0, active_connections=10, avg_response_time=100.0))
    lb.add_server(BackendServer(id='server-3', host='192.168.1.12', port=8003, cpu_usage=50.0, active_connections=10, avg_response_time=100.0))

    print_success(f"Added {len(lb.get_all_servers())} servers")

    print_info("Testing Round Robin (6 requests)...")
    for i in range(6):
        server = lb.route_request(LoadBalancerStrategy.ROUND_ROBIN)
        print(f"  Request {i+1} -> {server.id}")

    print_info("Testing Least Connections...")
    lb.update_server_metrics('server-2', {'active_connections': 100})
    server = lb.route_request(LoadBalancerStrategy.LEAST_CONNECTIONS)
    print_success(f"Least Connections chose: {server.id} (should avoid server-2)")

    print_info("Testing AI-Powered routing...")
    scores = {'server-1': 0.9, 'server-2': 0.5, 'server-3': 0.8}
    server = lb.route_request(LoadBalancerStrategy.AI_POWERED, prediction_scores=scores)
    print_success(f"AI-Powered chose: {server.id}")

    servers = lb.get_all_servers()
    print_success(f"Load balancer has {len(servers)} servers configured")

    return True


def test_auto_scaler():
    print_header("Auto-Scaler Tests")

    config = AutoScalerConfig(min_servers=1, max_servers=10)
    scaler = AutoScaler(config=config)

    print_info("Testing scale-up decision...")
    action = scaler.make_scaling_decision(
        current_servers=3,
        metrics={'cpu_usage': 85},
        predicted_load=80
    )
    print_success(f"Decision: {action.action_type.value}, Servers: +{action.servers_added_removed}")
    print(f"  Reason: {action.reason}")

    print_info("Testing scale-down decision...")
    action = scaler.make_scaling_decision(
        current_servers=5,
        metrics={'cpu_usage': 20},
        predicted_load=25
    )
    print_success(f"Decision: {action.action_type.value}, Servers: {action.servers_added_removed:+d}")

    print_info("Testing cooldown enforcement...")
    scaler.make_scaling_decision(current_servers=3, metrics={'cpu_usage': 85}, predicted_load=80)
    action = scaler.make_scaling_decision(current_servers=4, metrics={'cpu_usage': 85}, predicted_load=80)
    print_success(f"Immediate 2nd scale-up: {action.action_type.value} (should be STABLE due to cooldown)")

    status = scaler.get_status()
    print_success(f"Total scale-ups: {status['statistics']['total_scale_ups']}, Total scale-downs: {status['statistics']['total_scale_downs']}")

    return True


def test_traffic_predictor():
    print_header("Traffic Predictor (ML) Tests")

    tp = TrafficPredictor()

    print_info("Generating training data...")
    dates = pd.date_range('2024-01-01', periods=200, freq='1min')
    # Simulate realistic traffic with patterns
    base_traffic = 50 + 20 * np.sin(np.arange(200) / 20) + np.random.normal(0, 10, 200)
    data = pd.DataFrame({
        'timestamp': dates,
        'request_count': base_traffic.astype(int).clip(10, 150)
    })
    print_success(f"Generated {len(data)} data points")

    print_info("Training model...")
    tp.train(data)
    print_success("Model trained successfully")

    print_info("Making predictions...")
    pred, lower, upper = tp.predict_with_history(data, 10)
    print_success(f"Predictions for next 10 minutes:")
    for i, (p, l, u) in enumerate(zip(pred[:5], lower[:5], upper[:5])):
        print(f"  t+{i+1}: {p:.0f} requests (CI: {l:.0f}-{u:.0f})")

    print_info("Feature importance:")
    importance = tp.get_feature_importance()
    for feat, imp in list(importance.items())[:3]:
        print(f"  {feat}: {imp:.3f}")

    return True


def test_anomaly_detector():
    print_header("Anomaly Detector (ML) Tests")

    ad = AnomalyDetector(method='isolation_forest')

    print_info("Generating normal training data...")
    normal_data = pd.DataFrame({
        'cpu_usage': np.random.normal(50, 10, 200),
        'response_time': np.random.normal(100, 20, 200),
        'active_connections': np.random.normal(50, 15, 200)
    })
    ad.fit(normal_data)
    print_success("Detector trained on normal data")

    print_info("Testing anomaly detection...")
    # Normal samples
    test_normal = pd.DataFrame({
        'cpu_usage': [52, 48, 55],
        'response_time': [102, 98, 105],
        'active_connections': [52, 48, 55]
    })
    # Anomalous samples
    test_anomaly = pd.DataFrame({
        'cpu_usage': [95, 98],
        'response_time': [350, 400],
        'active_connections': [200, 250]
    })

    test_data = pd.concat([test_normal, test_anomaly], ignore_index=True)
    anomalies = ad.detect(test_data)
    scores = ad.get_anomaly_scores(test_data)

    print_success("Detection results:")
    labels = ['Normal', 'Normal', 'Normal', 'Normal', 'Normal', 'Anomaly', 'Anomaly']
    for i, (label, score) in enumerate(zip(anomalies, scores)):
        status = f"{Colors.RED}ANOMALY{Colors.ENDC}" if label == 1 else f"{Colors.GREEN}Normal{Colors.ENDC}"
        print(f"  Sample {i+1}: {status} (score: {score:.3f}) [{labels[i]}]")

    return True


def test_orchestrator():
    print_header("Infrastructure Orchestrator Tests")

    print_info("Initializing orchestrator...")
    orch = InfrastructureOrchestrator()

    try:
        orch.initialize()
        print_success("Orchestrator initialized")

        status = orch.get_system_status()
        print_success(f"Status: initialized={status.is_initialized}")
        print_success(f"Components: traffic_generator={status.traffic_generator}")

        print_info("Running one iteration...")
        result = orch.run_iteration()
        print_success(f"Iteration complete: iterations_run={result.iteration}")

        status = orch.get_system_status()
        print_success(f"Servers: {status.auto_scaler.get('current_servers', 'N/A')}, Active: {status.is_initialized}")

        orch.stop()
        print_success("Orchestrator stopped cleanly")

        return True
    except Exception as e:
        print_error(f"Error: {e}")
        orch.stop()
        return False


def run_simulation_demo():
    print_header("Simulation Demo")

    orch = InfrastructureOrchestrator()
    orch.initialize()

    print_info("Running 10 iterations of simulation...")
    for i in range(10):
        result = orch.run_iteration()
        metrics = result.get('metrics', {})

        cpu = metrics.get('cpu_usage', 0)
        rt = metrics.get('response_time', 0)

        cpu_bar = '=' * int(cpu / 5) + '-' * (20 - int(cpu / 5))
        rt_bar = '=' * int(rt / 10) + '-' * (20 - int(rt / 10))

        print(f"  Iter {i+1:2d} | CPU: {cpu:5.1f}% [{cpu_bar}] | RT: {rt:6.1f}ms [{rt_bar}]")

        time.sleep(0.1)

    status = orch.get_system_status()
    print_success(f"\nFinal state: {status['server_count']} servers")

    orch.stop()


def main():
    print(f"{Colors.BOLD}")
    print("+================================================================+")
    print("|     AI-Driven Infrastructure Manager - TUI Testing Suite      |")
    print("+================================================================+")
    print(f"{Colors.ENDC}")

    tests = [
        ("Traffic Generator", test_traffic_generator),
        ("Monitoring System", test_monitoring_system),
        ("Load Balancer", test_load_balancer),
        ("Auto-Scaler", test_auto_scaler),
        ("Traffic Predictor (ML)", test_traffic_predictor),
        ("Anomaly Detector (ML)", test_anomaly_detector),
        ("Infrastructure Orchestrator", test_orchestrator),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            results.append((name, False))

    print_header("Test Summary")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.ENDC}" if result else f"{Colors.RED}FAIL{Colors.ENDC}"
        print(f"  {status} - {name}")

    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")

    if passed == total:
        print_success("\nAll tests passed! System is working correctly.")
    else:
        print_error(f"\n{total - passed} test(s) failed.")

    print("\n")
    response = input(f"{Colors.CYAN}Run full simulation demo? (y/n): {Colors.ENDC}").strip().lower()
    if response == 'y':
        run_simulation_demo()


if __name__ == "__main__":
    main()