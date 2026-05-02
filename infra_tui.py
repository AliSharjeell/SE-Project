#!/usr/bin/env python3
"""
AI-Driven Infrastructure Manager - Interactive TUI
Full-featured terminal user interface for system interaction.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import time
import datetime
import threading
import numpy as np
import pandas as pd
from collections import deque

# No curses dependency - works on all platforms

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


class InfrastructureTUI:
    def __init__(self):
        self.tg = TrafficGenerator(base_rate=10, max_rate=100)
        self.ms = MonitoringSystem(history_size=100)
        self.lb = LoadBalancer()
        self.config = AutoScalerConfig()
        self.scaler = AutoScaler(config=self.config)
        self.predictor = TrafficPredictor()
        self.anomaly_detector = AnomalyDetector(method='isolation_forest')
        self.orchestrator = None
        self.running = False
        self.simulation_thread = None
        self.metrics_history = deque(maxlen=50)
        self.routing_history = deque(maxlen=100)
        self.scaling_history = deque(maxlen=50)
        self.stats = {
            'total_requests': 0,
            'total_anomalies': 0,
            'scale_ups': 0,
            'scale_downs': 0,
        }

        # Add default servers to load balancer
        self._setup_default_servers()

    def _setup_default_servers(self):
        """Initialize with 3 backend servers."""
        for i in range(1, 4):
            self.lb.add_server(BackendServer(
                id=f'server-{i}',
                host=f'192.168.1.{10+i}',
                port=8000 + i,
                cpu_usage=30.0,
                active_connections=0,
                avg_response_time=50.0
            ))

    def print_banner(self):
        """Print the main banner."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}")
        print("+==============================================================+")
        print("|     AI-Driven Infrastructure Manager - Interactive TUI         |")
        print("|     Intelligent Load Balancing & Auto-Scaling System         |")
        print("+==============================================================+")
        print(f"{Colors.ENDC}\n")

    def print_menu(self):
        """Print the main menu."""
        print(f"{Colors.BOLD}+====================== MAIN MENU ======================+{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[1]{Colors.ENDC} Traffic Generator    - Generate test traffic         {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[2]{Colors.ENDC} Load Balancer       - Route requests manually      {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[3]{Colors.ENDC} Auto-Scaler        - View/change scaling config    {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[4]{Colors.ENDC} ML Predictions     - Train & predict traffic       {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[5]{Colors.ENDC} Anomaly Detection  - Detect abnormal behavior     {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[6]{Colors.ENDC} System Metrics     - View monitoring data         {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[7]{Colors.ENDC} Auto-Simulation   - Run continuous simulation    {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.GREEN}[8]{Colors.ENDC} Full Demo          - Run complete demonstration  {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}|{Colors.ENDC}  {Colors.YELLOW}[Q]{Colors.ENDC} Quit               - Exit the application         {Colors.BOLD}|{Colors.ENDC}")
        print(f"{Colors.BOLD}+==============================================================+{Colors.ENDC}\n")

    def traffic_generator_menu(self):
        """Traffic Generator submenu."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Traffic Generator ==={Colors.ENDC}\n")
        print(f"{Colors.CYAN}Select pattern:{Colors.ENDC}")
        print(f"  {Colors.GREEN}[1]{Colors.ENDC} Constant rate")
        print(f"  {Colors.GREEN}[2]{Colors.ENDC} Ramp (gradual increase)")
        print(f"  {Colors.GREEN}[3]{Colors.ENDC} Spike (sudden burst)")
        print(f"  {Colors.GREEN}[4]{Colors.ENDC} Sine wave (periodic)")
        print(f"  {Colors.GREEN}[5]{Colors.ENDC} Burst (multiple requests)")
        print(f"  {Colors.GREEN}[0]{Colors.ENDC} Back to main menu\n")

        choice = input(f"{Colors.YELLOW}Choice: {Colors.ENDC}").strip()

        patterns = {
            '1': ('constant', self.tg.generate_constant),
            '2': ('ramp', lambda: self.tg.generate_ramp(10, 100, 60, 0.5)),
            '3': ('spike', lambda: self.tg.generate_spike(100, 0.5)),
            '4': ('sine wave', self.tg.generate_sine_wave),
            '5': ('burst', lambda: self.tg.generate_burst(10)),
        }

        if choice in patterns:
            name, func = patterns[choice]
            if choice == '5':
                requests = func()
                print(f"\n{Colors.GREEN}[+] Generated burst of {len(requests)} requests{Colors.ENDC}")
                for i, req in enumerate(requests[:5]):
                    print(f"    Request {i+1}: {req.request_id[:20]}...")
            else:
                req = func()
                print(f"\n{Colors.GREEN}[+] Generated {name} request:{Colors.ENDC}")
                print(f"    ID: {req.request_id}")
                print(f"    Payload: {req.payload_size} bytes")

            self.stats['total_requests'] += 1
        elif choice != '0':
            print(f"\n{Colors.RED}[-] Invalid choice{Colors.ENDC}")

    def load_balancer_menu(self):
        """Load Balancer submenu."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Load Balancer ==={Colors.ENDC}\n")

        servers = self.lb.get_all_servers()
        print(f"{Colors.CYAN}Active Servers ({len(servers)}):{Colors.ENDC}")
        for s in servers:
            print(f"  - {s.id}: {s.host}:{s.port} (CPU: {s.cpu_usage:.1f}%, Conn: {s.active_connections})")

        print(f"\n{Colors.CYAN}Select routing strategy:{Colors.ENDC}")
        print(f"  {Colors.GREEN}[1]{Colors.ENDC} Round Robin (sequential)")
        print(f"  {Colors.GREEN}[2]{Colors.ENDC} Least Connections (fewest active)")
        print(f"  {Colors.GREEN}[3]{Colors.ENDC} AI-Powered (ML-predicted health)")
        print(f"  {Colors.GREEN}[4]{Colors.ENDC} Add custom server")
        print(f"  {Colors.GREEN}[0]{Colors.ENDC} Back\n")

        choice = input(f"{Colors.YELLOW}Choice: {Colors.ENDC}").strip()

        if choice == '1':
            server = self.lb.route_request(LoadBalancerStrategy.ROUND_ROBIN)
            print(f"\n{Colors.GREEN}[+] Round Robin -> {server.id}{Colors.ENDC}")
        elif choice == '2':
            server = self.lb.route_request(LoadBalancerStrategy.LEAST_CONNECTIONS)
            print(f"\n{Colors.GREEN}[+] Least Connections -> {server.id}{Colors.ENDC}")
        elif choice == '3':
            scores = {s.id: np.random.uniform(0.5, 1.0) for s in servers}
            server = self.lb.route_request(LoadBalancerStrategy.AI_POWERED, prediction_scores=scores)
            print(f"\n{Colors.GREEN}[+] AI-Powered -> {server.id}{Colors.ENDC}")
            print(f"    Prediction scores: {scores}")
        elif choice == '4':
            sid = input("Server ID: ").strip()
            host = input("Host (e.g., 192.168.1.20): ").strip() or "localhost"
            port = int(input("Port: ").strip() or "8000")
            self.lb.add_server(BackendServer(
                id=sid, host=host, port=port,
                cpu_usage=30.0, active_connections=0, avg_response_time=50.0
            ))
            print(f"{Colors.GREEN}[+] Server {sid} added{Colors.ENDC}")
        elif choice != '0':
            print(f"\n{Colors.RED}[-] Invalid choice{Colors.ENDC}")

    def auto_scaler_menu(self):
        """Auto-Scaler configuration submenu."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Auto-Scaler ==={Colors.ENDC}\n")

        status = self.scaler.get_status()
        print(f"{Colors.CYAN}Current Configuration:{Colors.ENDC}")
        cfg = status['config']
        print(f"  Min Servers: {cfg['min_servers']}")
        print(f"  Max Servers: {cfg['max_servers']}")
        print(f"  Scale Up Threshold: {cfg['scale_up_threshold']}%")
        print(f"  Scale Down Threshold: {cfg['scale_down_threshold']}%")
        print(f"\n{Colors.CYAN}Statistics:{Colors.ENDC}")
        print(f"  Total Scale Ups: {status['statistics']['total_scale_ups']}")
        print(f"  Total Scale Downs: {status['statistics']['total_scale_downs']}")

        print(f"\n{Colors.CYAN}Test Scaling Decision:{Colors.ENDC}")
        cpu = float(input("CPU Usage %: ").strip() or "75")
        predicted = float(input("Predicted Load %: ").strip() or "70")
        current = int(input("Current Servers: ").strip() or "3")

        action = self.scaler.make_scaling_decision(
            current_servers=current,
            metrics={'cpu_usage': cpu},
            predicted_load=predicted
        )

        print(f"\n{Colors.GREEN}[+] Decision: {action.action_type.value.upper()}{Colors.ENDC}")
        print(f"    Servers: {current} -> {current + action.servers_added_removed}")
        print(f"    Reason: {action.reason}")

    def ml_predictions_menu(self):
        """ML Predictions submenu."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== ML Traffic Predictions ==={Colors.ENDC}\n")

        print(f"{Colors.CYAN}Generating synthetic training data...{Colors.ENDC}")
        dates = pd.date_range('2024-01-01', periods=200, freq='1min')
        base_traffic = 50 + 20 * np.sin(np.arange(200) / 20) + np.random.normal(0, 10, 200)
        data = pd.DataFrame({
            'timestamp': dates,
            'request_count': base_traffic.astype(int).clip(10, 150)
        })

        print(f"{Colors.CYAN}Training model...{Colors.ENDC}")
        self.predictor.train(data)

        print(f"\n{Colors.GREEN}[+] Model trained successfully!{Colors.ENDC}")
        print(f"\n{Colors.CYAN}Making predictions for next 10 minutes:{Colors.ENDC}")

        pred, lower, upper = self.predictor.predict_with_history(data, 10)
        confidence = self.predictor.get_confidence_score(pred[0])

        print(f"\n{Colors.BOLD}Predictions with 95% Confidence Intervals:{Colors.ENDC}")
        print(f"{'-' * 55}")
        print(f"{'Time':^8} | {'Prediction':^12} | {'Confidence Interval':^25}")
        print(f"{'-' * 55}")
        for i, (p, l, u) in enumerate(zip(pred[:10], lower[:10], upper[:10])):
            print(f"t+{i+1:2d} min  |   {p:5.0f} req    |     [{l:4.0f} - {u:4.0f}]")
        print(f"{'-' * 55}")
        print(f"\nModel Confidence Score: {confidence:.2%}")

    def anomaly_detection_menu(self):
        """Anomaly Detection submenu."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Anomaly Detection ==={Colors.ENDC}\n")

        print(f"{Colors.CYAN}Generating baseline data...{Colors.ENDC}")
        baseline = pd.DataFrame({
            'cpu_usage': np.random.normal(50, 10, 100),
            'response_time': np.random.normal(100, 20, 100),
            'active_connections': np.random.normal(50, 15, 100)
        })
        self.anomaly_detector.fit(baseline)
        print(f"{Colors.GREEN}[+] Detector trained on normal behavior{Colors.ENDC}")

        print(f"\n{Colors.CYAN}Testing with sample data (including anomalies):{Colors.ENDC}")
        test_data = pd.DataFrame({
            'cpu_usage': [52, 48, 95, 55, 98, 50, 52],
            'response_time': [102, 98, 105, 350, 400, 100, 105],
            'active_connections': [52, 48, 55, 200, 250, 50, 52]
        })

        anomalies = self.anomaly_detector.detect(test_data)
        scores = self.anomaly_detector.get_anomaly_scores(test_data)

        print(f"\n{'-' * 60}")
        print(f"{'Sample':^8} | {'CPU':^8} | {'RT':^8} | {'Score':^10} | {'Status':^12}")
        print(f"{'-' * 60}")
        labels = ['Normal', 'Normal', 'Normal', 'ANOMALY', 'ANOMALY', 'Normal', 'Normal']
        for i, (a, s) in enumerate(zip(anomalies, scores)):
            status = f"{Colors.RED}ANOMALY{Colors.ENDC}" if a == 1 else f"{Colors.GREEN}Normal{Colors.ENDC}"
            cpu = test_data.iloc[i]['cpu_usage']
            rt = test_data.iloc[i]['response_time']
            print(f"{i+1:^8} | {cpu:^8.0f} | {rt:^8.0f} | {s:^10.3f} | {status}")
        print(f"{'-' * 60}")

        anomaly_count = sum(anomalies)
        print(f"\nDetected {anomaly_count} anomalies in {len(test_data)} samples")

    def system_metrics_menu(self):
        """System metrics submenu."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== System Metrics ==={Colors.ENDC}\n")

        if not self.metrics_history:
            print(f"{Colors.YELLOW}[!] No metrics collected yet. Run simulation first.{Colors.ENDC}")
            return

        print(f"{Colors.CYAN}Collected {len(self.metrics_history)} metric snapshots{Colors.ENDC}\n")

        print(f"{Colors.BOLD}Recent Metrics History:{Colors.ENDC}")
        print(f"{'-' * 70}")
        print(f"{'Time':^12} | {'CPU':^8} | {'Memory':^8} | {'RT':^8} | {'Connections':^12}")
        print(f"{'-' * 70}")

        for m in list(self.metrics_history)[-10:]:
            ts = m.get('timestamp', 'N/A')[-8:]
            cpu = m.get('cpu_usage', 0)
            mem = m.get('memory_usage', 0)
            rt = m.get('response_time', 0)
            conn = m.get('active_connections', 0)
            cpu_bar = '=' * int(cpu / 10)
            print(f"{ts:^12} | {cpu:5.1f}% {cpu_bar:<3} | {mem:6.1f}% | {rt:6.0f}ms | {conn:10.0f}")
        print(f"{'-' * 70}")

        # Calculate averages
        if self.metrics_history:
            avg_cpu = np.mean([m.get('cpu_usage', 0) for m in self.metrics_history])
            avg_rt = np.mean([m.get('response_time', 0) for m in self.metrics_history])
            print(f"\n{Colors.BOLD}Statistics:{Colors.ENDC}")
            print(f"  Average CPU: {avg_cpu:.1f}%")
            print(f"  Average Response Time: {avg_rt:.1f}ms")
            print(f"  Total Requests Processed: {self.stats['total_requests']}")
            print(f"  Anomalies Detected: {self.stats['total_anomalies']}")

    def run_simulation(self):
        """Run interactive simulation."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== Auto-Simulation Mode ==={Colors.ENDC}\n")
        print(f"{Colors.YELLOW}Press ENTER to step through iterations, 'q' to quit...{Colors.ENDC}\n")

        iteration = 0
        while True:
            iteration += 1

            # Generate traffic
            req = self.tg.generate_request()
            self.stats['total_requests'] += 1

            # Simulate metrics
            cpu = np.random.uniform(30, 80)
            mem = np.random.uniform(40, 70)
            rt = np.random.uniform(20, 150)
            conn = np.random.uniform(50, 150)

            metric = ServerMetrics(
                cpu_usage=cpu, memory_usage=mem, response_time=rt,
                request_rate=100, active_connections=conn,
                timestamp=datetime.datetime.now()
            )
            self.ms.add_metric(metric)
            self.metrics_history.append({
                'timestamp': str(datetime.datetime.now()),
                'cpu_usage': cpu, 'memory_usage': mem,
                'response_time': rt, 'active_connections': conn
            })

            # Route request
            servers = self.lb.get_all_servers()
            scores = {s.id: np.random.uniform(0.3, 1.0) for s in servers}
            server = self.lb.route_request(LoadBalancerStrategy.AI_POWERED, prediction_scores=scores)

            # Scaling decision
            predicted = cpu + np.random.uniform(-10, 10)
            action = self.scaler.make_scaling_decision(
                current_servers=len(servers),
                metrics={'cpu_usage': cpu},
                predicted_load=predicted
            )

            if action.action_type.value == 'scale_up':
                self.stats['scale_ups'] += 1
            elif action.action_type.value == 'scale_down':
                self.stats['scale_downs'] += 1

            # Anomaly check
            anomaly_score = np.random.random()
            if anomaly_score > 0.9:
                self.stats['total_anomalies'] += 1
                anomaly_flag = f"{Colors.RED}ANOMALY{Colors.ENDC}"
            else:
                anomaly_flag = f"{Colors.GREEN}OK{Colors.ENDC}"

            # Display
            cpu_bar = '=' * int(cpu / 5) + '-' * (20 - int(cpu / 5))
            status = "SCALE UP" if action.action_type.value == 'scale_up' else \
                     "SCALE DOWN" if action.action_type.value == 'scale_down' else "STABLE"

            print(f"Iter {iteration:3d} | CPU: {cpu:5.1f}% [{cpu_bar}] | "
                  f"RT: {rt:5.0f}ms | -> {server.id:10s} | {status:10s} | {anomaly_flag}")

            user_input = input().strip().lower()
            if user_input == 'q':
                break

            if iteration >= 50:
                print(f"\n{Colors.YELLOW}Max iterations reached.{Colors.ENDC}")
                break

        print(f"\n{Colors.CYAN}Simulation ended after {iteration} iterations.{Colors.ENDC}")

    def run_full_demo(self):
        """Run complete demonstration."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== FULL SYSTEM DEMONSTRATION ==={Colors.ENDC}\n")

        print(f"{Colors.CYAN}Step 1: Initializing System Components...{Colors.ENDC}")
        print(f"  [OK] Traffic Generator ready")
        print(f"  [OK] Monitoring System ready")
        print(f"  [OK] Load Balancer with 3 servers")
        print(f"  [OK] Auto-Scaler configured")
        print(f"  [OK] ML Models initialized")

        print(f"\n{Colors.CYAN}Step 2: Training ML Models...{Colors.ENDC}")

        # Train predictor
        dates = pd.date_range('2024-01-01', periods=300, freq='1min')
        traffic = 50 + 30 * np.sin(np.arange(300) / 30) + np.random.normal(0, 15, 300)
        data = pd.DataFrame({'timestamp': dates, 'request_count': traffic.astype(int).clip(10, 150)})
        self.predictor.train(data)
        print(f"  [OK] Traffic Predictor trained")

        # Train anomaly detector
        baseline = pd.DataFrame({
            'cpu_usage': np.random.normal(50, 10, 200),
            'response_time': np.random.normal(100, 20, 200)
        })
        self.anomaly_detector.fit(baseline)
        print(f"  [OK] Anomaly Detector trained")

        print(f"\n{Colors.CYAN}Step 3: Running 20 Simulation Iterations...{Colors.ENDC}")
        print(f"{'-' * 75}")
        print(f"{'Iter':^5} | {'CPU':^12} | {'Response':^12} | {'Route':^15} | {'Scaling':^10} | {'Anomaly':^8}")
        print(f"{'-' * 75}")

        for i in range(20):
            iteration = i + 1
            cpu = np.random.uniform(25, 85)
            rt = np.random.uniform(30, 200)
            conn = np.random.randint(20, 200)

            servers = self.lb.get_all_servers()
            scores = {s.id: max(0.1, 1.0 - s.cpu_usage/100) for s in servers}
            server = self.lb.route_request(LoadBalancerStrategy.AI_POWERED, prediction_scores=scores)

            predicted = cpu + np.random.uniform(-15, 15)
            action = self.scaler.make_scaling_decision(
                current_servers=len(servers),
                metrics={'cpu_usage': cpu},
                predicted_load=predicted
            )

            anomaly = np.random.random() > 0.85
            if anomaly:
                self.stats['total_anomalies'] += 1

            cpu_bar = '=' * int(cpu / 10)
            scale_str = action.action_type.value.replace('scale_', '').upper()
            anomaly_str = f"{Colors.RED}DETECTED{Colors.ENDC}" if anomaly else f"{Colors.GREEN}None{Colors.ENDC}"

            print(f"{iteration:^5} | {cpu:5.1f}% {cpu_bar:<2} | {rt:8.0f}ms     | {server.id:15s} | {scale_str:^10} | {anomaly_str}")

            self.metrics_history.append({
                'cpu_usage': cpu, 'response_time': rt,
                'active_connections': conn
            })

        print(f"{'-' * 75}")

        print(f"\n{Colors.CYAN}Step 4: System Summary{Colors.ENDC}")
        status = self.scaler.get_status()
        print(f"  Total Requests: {self.stats['total_requests'] + 20}")
        print(f"  Anomalies Detected: {self.stats['total_anomalies']}")
        print(f"  Scale Events: {status['statistics']['total_scale_ups']} up, "
              f"{status['statistics']['total_scale_downs']} down")
        print(f"  Active Servers: {len(self.lb.get_all_servers())}")

        print(f"\n{Colors.GREEN}{Colors.BOLD}[[OK]] Demonstration Complete!{Colors.ENDC}\n")

    def run(self):
        """Main run loop."""
        self.print_banner()
        self.running = True

        while self.running:
            self.print_menu()
            choice = input(f"{Colors.YELLOW}Select option: {Colors.ENDC}").strip().lower()

            if choice == '1':
                self.traffic_generator_menu()
            elif choice == '2':
                self.load_balancer_menu()
            elif choice == '3':
                self.auto_scaler_menu()
            elif choice == '4':
                self.ml_predictions_menu()
            elif choice == '5':
                self.anomaly_detection_menu()
            elif choice == '6':
                self.system_metrics_menu()
            elif choice == '7':
                self.run_simulation()
            elif choice == '8':
                self.run_full_demo()
            elif choice in ['q', 'quit', 'exit']:
                self.running = False
            else:
                print(f"\n{Colors.RED}[-] Invalid option. Please try again.{Colors.ENDC}")

            if self.running:
                input(f"\n{Colors.CYAN}Press ENTER to continue...{Colors.ENDC}")

        print(f"\n{Colors.GREEN}{Colors.BOLD}Thank you for using AI-Driven Infrastructure Manager!{Colors.ENDC}\n")


def main():
    tui = InfrastructureTUI()
    tui.run()


if __name__ == "__main__":
    main()