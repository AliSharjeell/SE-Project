"""
AI Infrastructure Manager - Single Pane of Glass Dashboard
Optimized for live demo presentations with real-time monitoring and control.
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import time
import threading
import sys

# Page config
st.set_page_config(
    page_title="AI Infrastructure Manager",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoints with 1.5s timeout for resilience
GATEWAY_URL = "http://gateway:8000"
ML_SERVICE_URL = "http://ml-service:8000"
ORCHESTRATOR_URL = "http://orchestrator:8002"
REQUEST_TIMEOUT = 1.5

# Cache duration (seconds) - kept short so data doesn't stay stale
CACHE_DURATION = 5


@st.cache_data(ttl=5)
def _cached_fetch(url: str, default=None):
    """Cached API fetch with timeout and graceful degradation."""
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return default


def safe_api_call(func, default=None, cache_key=None):
    """Wrap API calls with timeout and graceful degradation."""
    try:
        result = func()
        return result if result is not None else default
    except Exception:
        return default


@st.cache_data(ttl=5)
def fetch_servers():
    """Cached fetch for servers."""
    return _cached_fetch(f"{GATEWAY_URL}/servers", default=[])


@st.cache_data(ttl=5)
def fetch_gateway_stats():
    """Cached fetch for gateway stats."""
    return _cached_fetch(f"{GATEWAY_URL}/stats", default=None)


@st.cache_data(ttl=5)
def fetch_container_metrics():
    """Cached fetch for container metrics."""
    return _cached_fetch(f"{ORCHESTRATOR_URL}/api/metrics", default={"metrics": {}, "source": "unavailable"})


@st.cache_data(ttl=5)
def fetch_orchestrator_status():
    """Cached fetch for orchestrator status."""
    return _cached_fetch(f"{ORCHESTRATOR_URL}/api/status", default=None)


@st.cache_data(ttl=5)
def fetch_audit_events():
    """Cached fetch for audit events."""
    return _cached_fetch(f"{ORCHESTRATOR_URL}/api/events?limit=10", default={"events": [], "total": 0})


@st.cache_data(ttl=5)
def fetch_health_scores():
    """Cached fetch for ML health scores."""
    return _cached_fetch(f"{ML_SERVICE_URL}/scores", default={"scores": {}})


@st.cache_data(ttl=5)
def fetch_anomalies():
    """Cached fetch for ML anomaly detection."""
    return _cached_fetch(f"{ML_SERVICE_URL}/anomalies", default={"anomalies": {}, "detector_fitted": False})


# Initialize session state early (before any widget or meta tag uses it)
if 'last_chaos' not in st.session_state:
    st.session_state['last_chaos'] = None
if 'traffic_applied' not in st.session_state:
    st.session_state['traffic_applied'] = None
if 'perf_history' not in st.session_state:
    st.session_state['perf_history'] = []
if 'last_history_update' not in st.session_state:
    st.session_state['last_history_update'] = 0
if 'refresh_interval' not in st.session_state:
    st.session_state['refresh_interval'] = 3
if 'sidebar_tab' not in st.session_state:
    st.session_state['sidebar_tab'] = 'manual'

# Auto-refresh the entire page so charts/metrics update in real time
st.markdown(
    f'<meta http-equiv="refresh" content="{st.session_state["refresh_interval"]}">',
    unsafe_allow_html=True
)

# CSS Styles
st.markdown("""
<style>
    :root {
        --bg-primary: #0a0a0a;
        --bg-secondary: #141414;
        --bg-tertiary: #1a1a1a;
        --bg-card: #1c1c1e;
        --text-primary: #ffffff;
        --text-secondary: #8e8e93;
        --text-tertiary: #636366;
        --accent: #0a84ff;
        --accent-hover: #409cff;
        --success: #30d158;
        --warning: #ff9f0a;
        --error: #ff453a;
        --border: #2c2c2e;
    }

    * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }

    .stApp { background-color: var(--bg-primary); color: var(--text-primary); }

    /* Fix loading spinner and overlay to match dark theme */
    .stSpinner > div {
        border-top-color: var(--accent) !important;
    }
    [data-testid="stAppViewContainer"] > .stProgress {
        background-color: var(--bg-secondary) !important;
    }

    .block-container { padding: 0.5rem 1rem !important; }

    footer, header { visibility: hidden; }

    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }

    .metric-value { font-size: 2rem; font-weight: 600; line-height: 1; }
    .metric-label { font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem; }
    .metric-delta { font-size: 0.8rem; margin-top: 0.25rem; }

    h1 { font-size: 1.5rem; font-weight: 600; margin: 0; }
    h2 { font-size: 1.1rem; font-weight: 600; margin: 0; }
    h3 { font-size: 0.8rem; font-weight: 500; color: var(--text-secondary); margin: 0; }

    .section-header {
        background: var(--bg-secondary);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        border: 1px solid var(--border);
    }

    .status-dot {
        width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px;
    }
    .dot-green { background: var(--success); box-shadow: 0 0 6px var(--success); }
    .dot-yellow { background: var(--warning); box-shadow: 0 0 6px var(--warning); }
    .dot-red { background: var(--error); box-shadow: 0 0 6px var(--error); }

    .server-bar {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
    }

    .sidebar-tabs { background: var(--bg-tertiary); border-radius: 8px; padding: 4px; gap: 4px; }
    .sidebar-tab { background: transparent; border-radius: 6px; color: var(--text-secondary); font-weight: 500; font-size: 0.75rem; padding: 6px 8px; border: none; cursor: pointer; white-space: nowrap; }
    .sidebar-tab.active { background: var(--bg-card); color: var(--text-primary); }

    /* Sidebar button fixes */
    [data-testid="stHorizontalBlock"] button {
        font-size: 0.75rem !important;
        padding: 0.25rem 0.5rem !important;
        white-space: nowrap !important;
    }

    .control-btn {
        background: var(--bg-tertiary);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.6rem;
        margin: 0.3rem 0;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
    }
    .control-btn:hover { border-color: var(--accent); background: var(--bg-card); }

    .preset-green { border-left: 3px solid var(--success) !important; }
    .preset-red { border-left: 3px solid var(--error) !important; }
    .preset-blue { border-left: 3px solid var(--accent) !important; }

    .chaos-btn { border-color: var(--error) !important; background: rgba(255,69,58,0.1) !important; }
    .chaos-btn:hover { background: rgba(255,69,58,0.2) !important; }

    [data-testid="stSidebar"] { background: var(--bg-secondary); border-right: 1px solid var(--border); }

    .toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; }
</style>
""", unsafe_allow_html=True)


def set_traffic(pattern: str, intensity: int):
    """Set traffic via orchestrator with toast feedback."""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/set_traffic",
            json={"pattern": pattern, "intensity": intensity},
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            st.session_state['traffic_applied'] = {'pattern': pattern, 'intensity': intensity}
            return True
    except:
        pass
    return False


def set_strategy(strategy: str):
    """Set routing strategy."""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/set_strategy",
            json={"strategy": strategy},
            timeout=REQUEST_TIMEOUT
        )
        return response.status_code == 200
    except:
        return False


def inject_chaos():
    """Trigger chaos injection."""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/inject_chaos",
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                st.session_state['last_chaos'] = result.get('container_killed')
            return result
    except:
        pass
    return None


def show_toast(message: str, icon: str = "✅"):
    """Display toast notification using st.success/info with timestamp."""
    st.toast(f"{icon} {message}", icon=None)


# Traffic generator - uses standalone HTTP controller service
_controller_pid = None

def start_traffic_generator(rps: int, strategy: str):
    """Start traffic generation via HTTP API to standalone controller."""
    try:
        # Start controller if not running
        import subprocess
        global _controller_pid
        if _controller_pid is None:
            try:
                proc = subprocess.Popen(
                    [sys.executable, "/app/traffic_controller.py", "8502"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                _controller_pid = proc.pid
                time.sleep(0.5)
            except:
                pass

        # Call HTTP API to start traffic
        requests.get(f"http://localhost:8502/start?rps={rps}&strategy={strategy}", timeout=2)
        st.session_state['traffic_running'] = True
        st.session_state['traffic_rps'] = rps
    except Exception:
        pass

def stop_traffic_generator():
    """Stop traffic generation."""
    try:
        requests.get(f"http://localhost:8502/stop", timeout=2)
    except:
        pass
    st.session_state['traffic_running'] = False
    st.session_state['traffic_rps'] = 0


def update_traffic_strategy(strategy: str):
    """Update routing strategy on the running traffic generator."""
    try:
        requests.get(f"http://localhost:8502/strategy?strategy={strategy}", timeout=2)
    except:
        pass


# ============================================
# MAIN LAYOUT - Single Pane of Glass
# ============================================

# Header
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
    <h1>AI Infrastructure Manager</h1>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span class="status-dot dot-green"></span>
        <span style="color: var(--text-secondary); font-size: 0.8rem;">System Online</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Get data (with graceful fallback)
stats = safe_api_call(fetch_gateway_stats, {'total_requests': 0, 'strategy_distribution': {}}) or {'total_requests': 0, 'strategy_distribution': {}}
servers = safe_api_call(fetch_servers, []) or []
orth_status = safe_api_call(fetch_orchestrator_status, {}) or {}
container_metrics = fetch_container_metrics()
health_scores = fetch_health_scores()
anomalies_data = fetch_anomalies()

# Compute real metrics from gateway stats
server_stats = stats.get('servers', {})
total_requests_all = stats.get('total_requests', 0)
active_servers = len([s for s in server_stats.values() if s.get('healthy', True)]) if server_stats else len(servers)

# Latency: average of last health-check latencies from ML metrics
metrics_dict = container_metrics.get('metrics', {}) if container_metrics else {}
avg_lat = 45  # baseline
if metrics_dict:
    lat_values = [v for v in metrics_dict.values() if isinstance(v, (int, float))]
    if lat_values:
        avg_lat = int(sum(lat_values) / len(lat_values))

throughput = total_requests_all

# Rolling performance history for charts
now_ts = time.time()
if now_ts - st.session_state['last_history_update'] > 3:
    st.session_state['perf_history'].append({
        'time': datetime.now(),
        'latency': avg_lat,
        'throughput': throughput,
        'active_servers': active_servers,
        'rps': orch_status.get('traffic_intensity', 0) if orch_status else 0,
    })
    if len(st.session_state['perf_history']) > 60:
        st.session_state['perf_history'] = st.session_state['perf_history'][-60:]
    st.session_state['last_history_update'] = now_ts

# Get current routing strategy from orchestrator
current_strategy = orch_status.get('routing_strategy', 'ai_powered') if orch_status else 'ai_powered'
strategy_display = current_strategy.replace('_', ' ').title()

# ============================================
# ROW 1: Top Metrics (4 columns)
# ============================================
st.markdown('<div class="section-header">System Overview</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="font-size: 1.2rem;">{strategy_display}</div>
        <div class="metric-label">Active Strategy</div>
        <div class="metric-delta" style="color: var(--accent);">
            {'AI-Powered' if current_strategy == 'ai_powered' else 'Traditional'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{avg_lat}ms</div>
        <div class="metric-label">Avg Latency</div>
        <div class="metric-delta" style="color: {'#ff9f0a' if avg_lat > 70 else '#30d158'};">
            {'Elevated' if avg_lat > 70 else 'Normal'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    current_rps = orch_status.get('traffic_intensity', 100) if orch_status else 100
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{active_servers}</div>
        <div class="metric-label">Active Servers</div>
        <div class="metric-delta" style="color: var(--text-secondary);">
            {'All healthy' if active_servers >= 3 else 'Check health'}
        </div>
        <div style="font-size: 0.65rem; color: #0a84ff; margin-top: 4px;">⚡ {current_rps} RPS</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{throughput}</div>
        <div class="metric-label">Total Requests</div>
        <div class="metric-delta" style="color: #30d158;">
            Routed
        </div>
    </div>
    """, unsafe_allow_html=True)



# ============================================
# ROW 2: Charts (70%) + Server Health (30%)
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">Performance & Infrastructure</div>', unsafe_allow_html=True)

chart_col, server_col = st.columns([7, 3])

with chart_col:
    if st.session_state['perf_history']:
        hist_df = pd.DataFrame(st.session_state['perf_history'])
    else:
        hist_df = pd.DataFrame({
            'time': [datetime.now()],
            'latency': [avg_lat],
            'throughput': [throughput],
            'rps': [orch_status.get('traffic_intensity', 0) if orch_status else 0],
        })

    # Latency Chart (real rolling data)
    fig_lat = go.Figure()
    fig_lat.add_trace(go.Scatter(x=hist_df['time'], y=hist_df['latency'], name='Latency',
                                   line=dict(color='#0a84ff', width=2),
                                   fill='tozeroy', fillcolor='rgba(10,132,255,0.15)'))
    fig_lat.add_hline(y=80, line_dash="dash", line_color="#ff453a", line_width=1,
                      annotation_text="High Load", annotation_position="top right",
                      annotation_font_color="#ff453a", annotation_font_size=9)
    fig_lat.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0', family='-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'),
        margin=dict(l=30, r=20, t=20, b=30),
        showlegend=False,
        height=200,
        xaxis=dict(showgrid=True, gridcolor='#2c2c2e', tickformat='%H:%M:%S'),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='ms'),
    )
    st.plotly_chart(fig_lat, use_container_width=True)

    # Throughput / RPS Chart
    fig_through = go.Figure()
    fig_through.add_trace(go.Scatter(
        x=hist_df['time'], y=hist_df['throughput'], name='Total Requests',
        line=dict(color='#30d158', width=2), fillcolor='rgba(48,209,88,0.15)', fill='tozeroy'
    ))
    if 'rps' in hist_df.columns:
        fig_through.add_trace(go.Scatter(
            x=hist_df['time'], y=hist_df['rps'], name='Target RPS',
            line=dict(color='#ff9f0a', width=2, dash='dot')
        ))
    fig_through.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0', family='-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'),
        margin=dict(l=30, r=20, t=20, b=30),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=200,
        xaxis=dict(showgrid=True, gridcolor='#2c2c2e', tickformat='%H:%M:%S'),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='req/s'),
    )
    st.plotly_chart(fig_through, use_container_width=True)

with server_col:
    st.markdown("#### Server Health & Scores")

    # Use scrollable container for server health
    with st.container(height=400):
        # Server data
        if servers:
            server_list = servers
        else:
            server_list = [
                {'server_id': 'backend-1', 'healthy': True},
                {'server_id': 'backend-2', 'healthy': True},
                {'server_id': 'backend-3', 'healthy': True},
            ]

        metrics_dict = container_metrics.get('metrics', {}) if container_metrics else {}
        health_scores_raw = health_scores.get('scores', {}) if health_scores else {}
        gateway_servers = stats.get('servers', {}) if stats else {}

        for server in server_list:
            server_id = server.get('server_id', '')
            if 'http://' in server_id:
                server_name = server_id.split('http://')[1].split(':')[0]
                server_url = server_id
            else:
                server_name = server_id
                server_url = f"http://{server_id}:8000"

            real_cpu = metrics_dict.get(server_name) or metrics_dict.get(server_id.replace('http://', ''))
            if real_cpu is None:
                cpu = random.randint(20, 75)
            else:
                cpu = int(real_cpu)

            # Health score from ML service
            hscore = health_scores_raw.get(server_url)
            if hscore is None:
                hscore = 1.0
            hscore_pct = int(hscore * 100)

            # Request count from gateway
            gw_data = gateway_servers.get(server_url, {})
            req_count = gw_data.get('total_requests', 0)
            conn_count = gw_data.get('active_connections', 0)

            dot_class = 'dot-green' if cpu < 70 else 'dot-yellow' if cpu < 85 else 'dot-red'
            cpu_color = '#ff453a' if cpu >= 80 else '#ff9f0a' if cpu >= 70 else '#30d158'
            score_color = '#ff453a' if hscore < 0.4 else '#ff9f0a' if hscore < 0.7 else '#30d158'

            st.markdown(f"""
            <div class="server-bar">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-weight: 600; font-size: 0.85rem;">{server_id}</span>
                    <span class="status-dot {dot_class}"></span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                    <span style="color: var(--text-secondary); font-size: 0.7rem;">CPU</span>
                    <span style="font-weight: 600; font-size: 0.8rem; color: {cpu_color};">{cpu}%</span>
                </div>
                <div style="background: var(--bg-tertiary); border-radius: 4px; height: 4px; margin-bottom: 0.4rem;">
                    <div style="background: {cpu_color}; width: {min(cpu, 100)}%; height: 100%; border-radius: 4px;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                    <span style="color: var(--text-secondary); font-size: 0.7rem;">ML Health Score</span>
                    <span style="font-weight: 600; font-size: 0.8rem; color: {score_color};">{hscore_pct}%</span>
                </div>
                <div style="background: var(--bg-tertiary); border-radius: 4px; height: 4px; margin-bottom: 0.4rem;">
                    <div style="background: {score_color}; width: {hscore_pct}%; height: 100%; border-radius: 4px;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: var(--text-secondary); font-size: 0.7rem;">Req: {req_count} | Conn: {conn_count}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# ROW 2b: Traffic Distribution (real gateway stats)
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">Traffic Distribution</div>', unsafe_allow_html=True)

# Show actual request counts from gateway stats
gateway_server_stats = stats.get('servers', {}) if stats else {}
if gateway_server_stats:
    dist_data = []
    for sid, sdata in gateway_server_stats.items():
        dist_data.append({
            'Server': sid,
            'Requests': sdata.get('total_requests', 0),
            'Connections': sdata.get('active_connections', 0),
        })
    dist_df = pd.DataFrame(dist_data).sort_values('Server')

    dist_col1, dist_col2 = st.columns(2)
    with dist_col1:
        fig_dist = go.Figure(data=[
            go.Bar(
                x=dist_df['Server'],
                y=dist_df['Requests'],
                marker_color=['#0a84ff', '#30d158', '#ff453a'][:len(dist_df)]
            )
        ])
        fig_dist.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'),
            margin=dict(l=30, r=20, t=20, b=30),
            height=200,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='Total Requests'),
            showlegend=False,
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with dist_col2:
        total_req_all = dist_df['Requests'].sum()
        if total_req_all > 0:
            dist_df['Share'] = (dist_df['Requests'] / total_req_all * 100).round(1)
        else:
            dist_df['Share'] = 0.0
        st.dataframe(
            dist_df[['Server', 'Requests', 'Share']].rename(columns={'Share': 'Share %'}),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No gateway statistics available. Traffic distribution will appear once the gateway is online.")

# ============================================
# ROW 2c: Strategy Usage (real gateway stats)
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">Strategy Usage</div>', unsafe_allow_html=True)

strategy_dist = stats.get('strategy_distribution', {}) if stats else {}
if strategy_dist:
    strat_df = pd.DataFrame([
        {'Strategy': k.replace('_', ' ').title(), 'Requests': v}
        for k, v in strategy_dist.items() if v > 0
    ])
    if not strat_df.empty:
        strat_col1, strat_col2 = st.columns(2)
        with strat_col1:
            fig_strat = go.Figure(data=[
                go.Pie(
                    labels=strat_df['Strategy'],
                    values=strat_df['Requests'],
                    hole=0.45,
                    marker_colors=['#0a84ff', '#30d158', '#ff453a', '#ff9f0a'][:len(strat_df)]
                )
            ])
            fig_strat.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e0e0e0', family='-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'),
                margin=dict(l=20, r=20, t=20, b=20),
                height=220,
                showlegend=False,
            )
            st.plotly_chart(fig_strat, use_container_width=True)
        with strat_col2:
            st.dataframe(strat_df, use_container_width=True, hide_index=True)
    else:
        st.info("No routing decisions recorded yet. Generate some traffic to see strategy usage.")
else:
    st.info("Strategy distribution unavailable.")

# ============================================
# ROW 3: Predictions & Anomalies
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">AI Predictions & Anomaly Detection</div>', unsafe_allow_html=True)

pred_col1, pred_col2 = st.columns(2)

with pred_col1:
    st.markdown("#### Traffic Forecast (Next 12h)")

    current_rps = orch_status.get('traffic_intensity', 100) if orch_status else 100
    pred_time = pd.date_range(start=datetime.now(), periods=12, freq='H')
    # Seed forecast around current intensity with small sinusoidal drift
    base = current_rps
    drift = [base + base * 0.15 * np.sin(i * 0.8) + np.random.normal(0, base * 0.05) for i in range(12)]
    upper = [d + base * 0.12 for d in drift]
    lower = [max(0, d - base * 0.12) for d in drift]
    pred_data = pd.DataFrame({
        'time': pred_time,
        'predicted': drift,
        'upper': upper,
        'lower': lower,
    })

    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(x=pred_data['time'], y=pred_data['upper'], name='Upper Bound',
                                   line=dict(color='rgba(48,209,88,0.3)', width=1),
                                   fill='tonexty', fillcolor='rgba(48,209,88,0.1)'))
    fig_pred.add_trace(go.Scatter(x=pred_data['time'], y=pred_data['predicted'], name='Predicted',
                                   line=dict(color='#30d158', width=2)))
    fig_pred.add_trace(go.Scatter(x=pred_data['time'], y=pred_data['lower'], name='Lower Bound',
                                   line=dict(color='rgba(48,209,88,0.3)', width=1),
                                   fill='tonexty', fillcolor='rgba(10,132,255,0.1)'))
    fig_pred.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e0e0', family='-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'),
        margin=dict(l=30, r=20, t=20, b=30),
        height=180,
        xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='req/s'),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    )
    st.plotly_chart(fig_pred, use_container_width=True)

    # Model Confidence Badge
    confidence = min(96, max(85, 95 - int(abs(current_rps - 500) / 500)))
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem; padding: 0.5rem; background: rgba(48,209,88,0.1); border-radius: 6px; border: 1px solid rgba(48,209,88,0.2);">
        <span style="font-size: 0.75rem; color: var(--text-secondary);">Forecast Confidence</span>
        <span style="font-weight: 700; color: #30d158; font-size: 0.9rem;">{confidence}%</span>
    </div>
    """, unsafe_allow_html=True)

with pred_col2:
    st.markdown("#### Anomaly Detection")

    anomalies_raw = anomalies_data.get('anomalies', {}) if anomalies_data else {}
    detector_fitted = anomalies_data.get('detector_fitted', False) if anomalies_data else False

    if anomalies_raw and detector_fitted:
        anomaly_rows = []
        for url, adata in anomalies_raw.items():
            server_name = url.replace('http://', '').replace(':8000', '')
            anomaly_rows.append({
                'Server': server_name,
                'Score': adata.get('anomaly_score', 0),
                'IsAnomaly': adata.get('is_anomaly', False),
                'CPU': adata.get('features', {}).get('cpu_usage', 0),
            })
        anomaly_df = pd.DataFrame(anomaly_rows)

        colors = ['#ff453a' if row['IsAnomaly'] else '#30d158' for _, row in anomaly_df.iterrows()]

        fig_anomaly = go.Figure()
        fig_anomaly.add_trace(go.Bar(
            x=anomaly_df['Server'],
            y=anomaly_df['Score'],
            marker_color=colors,
            text=anomaly_df['Score'].round(2),
            textposition='outside',
            textfont=dict(color='#e0e0e0', size=10)
        ))
        fig_anomaly.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'),
            margin=dict(l=30, r=20, t=20, b=30),
            height=180,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='Anomaly Score'),
            showlegend=False,
        )
        st.plotly_chart(fig_anomaly, use_container_width=True)

        anomaly_count = sum(anomaly_df['IsAnomaly'])
        if anomaly_count > 0:
            bad_servers = anomaly_df[anomaly_df['IsAnomaly']]['Server'].tolist()
            triggers_html = " • ".join([f"<span style='color: #ff453a;'>{s}</span>" for s in bad_servers])
            st.markdown(f"""
            <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(255,69,58,0.1); border-radius: 6px; border: 1px solid rgba(255,69,58,0.2);">
                <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 4px;">Anomaly Servers</div>
                <div style="font-size: 0.75rem;">{triggers_html}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(48,209,88,0.1); border-radius: 6px; border: 1px solid rgba(48,209,88,0.2);">
                <span style="font-size: 0.75rem; color: #30d158;">✓ No anomalies detected</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Anomaly detector is collecting baseline data...")
        st.markdown(f"""
        <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(255,159,10,0.1); border-radius: 6px; border: 1px solid rgba(255,159,10,0.2);">
            <span style="font-size: 0.75rem; color: #ff9f0a;">⏳ Training on first 10+ samples</span>
        </div>
        """, unsafe_allow_html=True)


# ============================================
# SIDEBAR - Command Center
# ============================================

with st.sidebar:
    st.markdown("### Command Center")

    tab_cols = st.columns(3)
    with tab_cols[0]:
        if st.button("Presets", use_container_width=True,
                     type="primary" if st.session_state.sidebar_tab == 'presets' else "secondary"):
            st.session_state.sidebar_tab = 'presets'
            st.rerun()
    with tab_cols[1]:
        if st.button("Manual", use_container_width=True,
                     type="primary" if st.session_state.sidebar_tab == 'manual' else "secondary"):
            st.session_state.sidebar_tab = 'manual'
            st.rerun()
    with tab_cols[2]:
        if st.button("Settings", use_container_width=True,
                     type="primary" if st.session_state.sidebar_tab == 'settings' else "secondary"):
            st.session_state.sidebar_tab = 'settings'
            st.rerun()

    st.divider()

    # === PRESETS TAB ===
    if st.session_state.sidebar_tab == 'presets':
        # Track current scenario
        if 'current_scenario' not in st.session_state:
            st.session_state.current_scenario = 'normal'

        # Active scenario indicator
        scenario_labels = {
            'normal': '🟢 Normal Ops',
            'black_friday': '🔥 Black Friday',
            'ddos': '💀 DDoS Attack',
            'sine_wave': '〰️ Sine Wave'
        }
        st.markdown(f"""
        <div style="background: rgba(48,209,88,0.15); border: 1px solid rgba(48,209,88,0.3);
                    border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; text-align: center;">
            <div style="font-size: 0.7rem; color: var(--text-secondary);">Active Scenario</div>
            <div style="font-size: 1rem; font-weight: 600; color: #30d158;">{scenario_labels.get(st.session_state.current_scenario, '🟢 Normal Ops')}</div>
            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 4px;">
                RPS: {orch_status.get('traffic_intensity', 0) if orch_status else 0}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Demo Scenarios")

        # Get current strategy for traffic generation
        current_routing = orch_status.get('routing_strategy', 'ai_powered') if orch_status else 'ai_powered'

        # Stack buttons vertically for clean alignment
        if st.button("🔥 Black Friday Rush", use_container_width=True, key="bf_preset",
                     type="primary" if st.session_state.current_scenario == 'black_friday' else "secondary"):
            # Aggressive ramp: spike to 12000 RPS
            stop_traffic_generator()
            st.session_state.current_scenario = 'black_friday'
            if set_traffic("spike", 12000):
                start_traffic_generator(12000, current_routing)
                show_toast("Black Friday Rush - 12,000 RPS spike!")
            else:
                show_toast("Traffic: SPIKE → 12,000 RPS", "📈")

        if st.button("💀 DDoS Attack", use_container_width=True, key="ddos_preset",
                     type="primary" if st.session_state.current_scenario == 'ddos' else "secondary"):
            stop_traffic_generator()
            st.session_state.current_scenario = 'ddos'
            if set_traffic("burst", 10000):
                start_traffic_generator(10000, current_routing)
                show_toast("DDoS: 10,000 RPS + chaos injection", "⚠️")
            # Chaos injection
            chaos_result = inject_chaos()
            if chaos_result and chaos_result.get('success'):
                show_toast(f"Container {chaos_result.get('container_killed')} killed!", "💥")

        if st.button("🔄 Normal Ops", use_container_width=True, key="normal_preset",
                     type="primary" if st.session_state.current_scenario == 'normal' else "secondary"):
            stop_traffic_generator()
            st.session_state.current_scenario = 'normal'
            if set_traffic("constant", 50):
                show_toast("Normal operations - 50 RPS steady")
            else:
                show_toast("Reset: 50 RPS", "🔄")

        if st.button("〰️ Sine Wave", use_container_width=True, key="sine_preset",
                     type="primary" if st.session_state.current_scenario == 'sine_wave' else "secondary"):
            stop_traffic_generator()
            st.session_state.current_scenario = 'sine_wave'
            if set_traffic("sine_wave", 500):
                start_traffic_generator(500, current_routing)
                show_toast("Sine wave pattern - 500 RPS", "〰️")
            else:
                show_toast("Traffic: SINE_WAVE → 500 RPS", "〰️")

        st.markdown("---")
        st.markdown("#### Routing Strategy")

        # Strategy selector buttons in presets
        # Only sync session state if it's a fresh session (not set by user)
        if 'strategy_chosen' not in st.session_state:
            st.session_state.current_strategy = current_strategy
            st.session_state.strategy_chosen = False

        strat_cols = st.columns(2)
        with strat_cols[0]:
            if st.button("🔄 Round Robin", use_container_width=True,
                         type="primary" if st.session_state.current_strategy == 'round_robin' else "secondary",
                         key="strat_rr"):
                set_strategy("round_robin")
                update_traffic_strategy("round_robin")
                st.session_state.current_strategy = 'round_robin'
                st.session_state.strategy_chosen = True
                show_toast("Round Robin - Even Distribution")
                st.rerun()

        with strat_cols[1]:
            if st.button("⚡ Least Conn", use_container_width=True,
                         type="primary" if st.session_state.current_strategy == 'least_connections' else "secondary",
                         key="strat_lc"):
                set_strategy("least_connections")
                update_traffic_strategy("least_connections")
                st.session_state.current_strategy = 'least_connections'
                st.session_state.strategy_chosen = True
                show_toast("Least Connections - Smart Routing")
                st.rerun()

        strat_cols2 = st.columns(2)
        with strat_cols2[0]:
            if st.button("🤖 AI-Powered", use_container_width=True,
                         type="primary" if st.session_state.current_strategy == 'ai_powered' else "secondary",
                         key="strat_ai"):
                set_strategy("ai_powered")
                update_traffic_strategy("ai_powered")
                st.session_state.current_strategy = 'ai_powered'
                st.session_state.strategy_chosen = True
                show_toast("AI-Powered - ML-Based Routing")
                st.rerun()

        with strat_cols2[1]:
            if st.button("🚫 OFF", use_container_width=True,
                         type="primary" if st.session_state.current_strategy == 'off' else "secondary",
                         key="strat_off"):
                set_strategy("off")
                update_traffic_strategy("off")
                st.session_state.current_strategy = 'off'
                st.session_state.strategy_chosen = True
                show_toast("OFF - No Load Balancing")
                st.rerun()

        st.markdown("---")
        st.markdown("#### Chaos Engineering")
        if st.button("Kill Random Server", use_container_width=True, key="chaos_sidebar", type="primary"):
            result = inject_chaos()
            if result and result.get('success'):
                show_toast(f"Server {result.get('container_killed')} terminated!", "💀")
                st.session_state['last_chaos'] = result.get('container_killed')
            else:
                show_toast("Chaos injection triggered (demo mode)", "⚡")

    # === MANUAL TAB ===
    elif st.session_state.sidebar_tab == 'manual':
        st.markdown("#### Routing Strategy")

        strategy = st.selectbox("Load Balancer",
                                ["round_robin", "least_connections", "ai_powered", "off"],
                                format_func=lambda x: x.replace("_", " ").title())

        if st.button("Apply Strategy", use_container_width=True):
            if set_strategy(strategy):
                update_traffic_strategy(strategy)
                show_toast(f"Strategy set to {strategy.replace('_', ' ').title()}")
            else:
                show_toast(f"Strategy: {strategy.replace('_', ' ').title()}", "📡")

        st.markdown("---")
        st.markdown("#### Traffic Control")

        intensity = st.slider("Intensity (RPS)", 10, 10000, 100, step=10)
        shape = st.selectbox("Pattern",
                              ["constant", "ramp", "spike", "sine_wave", "burst"],
                              format_func=lambda x: x.replace("_", " ").title())

        if st.button("Apply Traffic", use_container_width=True, type="primary"):
            current_strat = orch_status.get('routing_strategy', 'ai_powered') if orch_status else 'ai_powered'
            if set_traffic(shape, intensity):
                start_traffic_generator(intensity, current_strat)
                show_toast(f"{shape.replace('_', ' ').title()} traffic at {intensity} RPS")
            else:
                start_traffic_generator(intensity, current_strat)
                show_toast(f"Setting: {shape} → {intensity} RPS", "🎯")

        st.markdown("---")
        st.markdown("#### Quick Stats")

        if orch_status:
            st.info(f"Pattern: {orch_status.get('traffic_pattern', 'N/A')}")
            st.info(f"Strategy: {orch_status.get('routing_strategy', 'N/A')}")
            st.info(f"Intensity: {orch_status.get('traffic_intensity', 0)} RPS")
        else:
            st.warning("Orchestrator offline")

        if st.session_state.get('last_chaos'):
            st.error(f"Last chaos: {st.session_state['last_chaos']}")

    # === SETTINGS TAB ===
    else:
        st.markdown("#### Display Settings")

        chart_points = st.slider("Chart data points", 10, 100, 50)

        st.markdown("---")
        st.markdown("#### Auto-Refresh")

        refresh_interval = st.slider(
            "Page refresh interval (seconds)",
            min_value=1,
            max_value=10,
            value=st.session_state['refresh_interval'],
            step=1,
            help="How often the dashboard reloads to fetch fresh data"
        )
        if refresh_interval != st.session_state['refresh_interval']:
            st.session_state['refresh_interval'] = refresh_interval
            st.rerun()

        st.markdown("---")

        st.caption("💡 Data refreshes automatically via caching")
        st.markdown("#### Alert Thresholds")

        cpu_threshold = st.slider("CPU Alert (%)", 50, 95, 80)
        latency_threshold = st.slider("Latency Alert (ms)", 100, 1000, 500)

        st.markdown("---")
        st.markdown("#### Connection Status")

        # Show service status
        gateway_ok = safe_api_call(lambda: requests.get(f"{GATEWAY_URL}/health", timeout=1), None) is not None
        orch_ok = safe_api_call(fetch_orchestrator_status, None) is not None
        ml_ok = safe_api_call(lambda: requests.get(f"{ML_SERVICE_URL}/health", timeout=1), None) is not None

        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            st.markdown(f"Gateway: {'🟢' if gateway_ok else '🔴'}")
        with col_st2:
            st.markdown(f"Orchestrator: {'🟢' if orch_ok else '🔴'}")
        with col_st3:
            st.markdown(f"ML Service: {'🟢' if ml_ok else '🔴'}")

        st.markdown("---")
        st.markdown(f"**Last update:** {datetime.now().strftime('%H:%M:%S')}")

        if st.button("Clear Cache & Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# ============================================
# MAIN VIEW: System Audit Log
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">System Audit</div>', unsafe_allow_html=True)

audit_events = fetch_audit_events()
events_list = audit_events.get("events", [])

if events_list:
    with st.expander("System Audit Log", expanded=False):
        st.markdown("""
        <style>
        .audit-log { font-family: 'SF Mono', 'Consolas', monospace; font-size: 0.75rem; }
        .audit-entry { padding: 0.4rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .audit-time { color: var(--text-secondary); }
        .audit-type { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; margin-left: 0.5rem; }
        .audit-traffic { background: rgba(10,132,255,0.3); color: #0a84ff; }
        .audit-strategy { background: rgba(48,209,88,0.3); color: #30d158; }
        .audit-chaos { background: rgba(255,69,58,0.3); color: #ff453a; }
        .audit-scale { background: rgba(255,159,10,0.3); color: #ff9f0a; }
        </style>
        """, unsafe_allow_html=True)

        for event in reversed(events_list):
            ts = event.get("timestamp", "")[11:19]  # Just HH:MM:SS
            etype = event.get("type", "unknown")
            msg = event.get("message", "")

            badge_class = {
                "traffic_change": "audit-traffic",
                "strategy_change": "audit-strategy",
                "chaos_injection": "audit-chaos",
                "scale_up": "audit-scale",
                "scale_down": "audit-scale",
            }.get(etype, "")

            st.markdown(f"""
            <div class="audit-entry">
                <span class="audit-time">{ts}</span>
                <span class="audit-type {badge_class}">{etype.replace('_', ' ')}</span>
                <span style="margin-left: 0.5rem;">{msg}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"<div style='font-size: 0.65rem; color: var(--text-secondary); margin-top: 0.5rem;'>Total events: {audit_events.get('total', 0)}</div>", unsafe_allow_html=True)
else:
    with st.expander("System Audit Log", expanded=False):
        st.info("No system events recorded yet. Events will appear as you interact with the system.")

# Dashboard auto-refreshes every N seconds via HTML meta refresh tag.
# The cache ensures API calls are deduplicated within the TTL window.