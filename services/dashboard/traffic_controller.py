#!/usr/bin/env python3
"""
Standalone Traffic Generator - runs independently.
Controlled via HTTP requests to start/stop traffic generation.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests
import sys
import os

# Configuration
GATEWAY_URL = os.environ.get('GATEWAY_URL', 'http://gateway:8000')
GENERATE_ENDPOINT = f"{GATEWAY_URL}/generate-load"
STATS_ENDPOINT = f"{GATEWAY_URL}/stats"

# Global state - managed via class for better encapsulation
class TrafficState:
    active = False
    thread = None
    rps = 100
    count = 0
    start = None
    strategy = "ai_powered"

state = TrafficState()


class TrafficHandler(BaseHTTPRequestHandler):
    """HTTP handler for traffic generator control."""

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(('{"status": "ok", "active": %s}' % str(state.active).lower()).encode())

        elif self.path.startswith('/start'):
            rps = self._get_param('rps', 100)
            strategy = self._get_param('strategy', 'ai_powered')
            self._start_traffic(rps, strategy)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(('{"status": "started", "rps": %s}' % rps).encode())

        elif self.path == '/stop':
            self._stop_traffic()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "stopped"}')

        elif self.path == '/stats':
            rate = state.count / (time.time() - state.start) if state.start and state.count > 0 else 0
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(('{"active": %s, "count": %d, "rate": %.1f}' % (str(state.active).lower(), state.count, rate)).encode())

        elif self.path == '/reset':
            state.count = 0
            state.start = time.time()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "reset"}')

        else:
            self.send_response(404)
            self.end_headers()

    def _get_param(self, name, default):
        if '?' in self.path:
            query = self.path.split('?')[1]
            for param in query.split('&'):
                if '=' in param:
                    k, v = param.split('=', 1)
                    if k == name:
                        return v
        return default

    def _start_traffic(self, rps, strategy="ai_powered"):
        self._stop_traffic()
        state.rps = int(rps)
        state.strategy = strategy
        state.active = True
        state.count = 0
        state.start = time.time()
        state.thread = threading.Thread(target=self._generate_traffic, daemon=True)
        state.thread.start()

    def _stop_traffic(self):
        state.active = False

    def _generate_traffic(self):
        interval = 1.0 / max(state.rps, 1)
        endpoint = f"{GENERATE_ENDPOINT}?strategy={state.strategy}"
        while state.active:
            try:
                requests.get(endpoint, timeout=1)
                state.count += 1
            except:
                pass
            time.sleep(interval)

    def log_message(self, format, *args):
        pass


def run_server(port=8502):
    server = HTTPServer(('0.0.0.0', port), TrafficHandler)
    print(f"Traffic controller listening on port {port}")
    print(f"Gateway: {GATEWAY_URL}")
    server.serve_forever()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8502
    run_server(port)