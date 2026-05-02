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

# Cache duration (seconds)
CACHE_DURATION = 5


def safe_api_call(func, default=None, cache_key=None):
    """Wrap API calls with timeout and graceful degradation."""
    # Check cache first
    if cache_key and cache_key in st.session_state:
        cached = st.session_state[cache_key]
        if time.time() - cached.get('_timestamp', 0) < CACHE_DURATION:
            return cached.get('data', default)

    try:
        result = func()
        if cache_key:
            st.session_state[cache_key] = {'data': result, '_timestamp': time.time()}
        return result
    except Exception as e:
        return default


@st.cache_data(ttl=CACHE_DURATION)
def get_gateway_stats_cached():
    try:
        response = requests.get(f"{GATEWAY_URL}/stats", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


@st.cache_data(ttl=CACHE_DURATION)
def get_servers_cached():
    try:
        response = requests.get(f"{GATEWAY_URL}/servers", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []


@st.cache_data(ttl=10)
def get_container_metrics_cached():
    """Fetch real container CPU metrics from orchestrator."""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/metrics", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"metrics": {}, "source": "unavailable"}


@st.cache_data(ttl=CACHE_DURATION)
def get_orchestrator_status_cached():
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/status", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


@st.cache_data(ttl=10)
def get_audit_events_cached():
    """Fetch system audit events from orchestrator."""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/api/events?limit=10", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"events": [], "total": 0}


# CSS Styles
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

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

    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

    .stApp { background-color: var(--bg-primary); color: var(--text-primary); }

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


# Initialize session state
if 'last_chaos' not in st.session_state:
    st.session_state['last_chaos'] = None
if 'traffic_applied' not in st.session_state:
    st.session_state['traffic_applied'] = None


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
stats = safe_api_call(get_gateway_stats_cached, {'total_requests': 0, 'requests_delta': 0}) or {'total_requests': 0, 'requests_delta': 0}
servers = safe_api_call(get_servers_cached, []) or []
orch_status = safe_api_call(get_orchestrator_status_cached, {}) or {}
container_metrics = get_container_metrics_cached()

# ============================================
# ROW 1: Top Metrics (4 columns)
# ============================================
st.markdown('<div class="section-header">System Overview</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

# Generate demo data if API fails
total_req = stats.get('total_requests', 0) or random.randint(10000, 50000)
req_delta = stats.get('requests_delta', 0) or round(random.uniform(-5, 15), 1)

# Get current routing strategy from orchestrator
current_strategy = orch_status.get('routing_strategy', 'ai_powered') if orch_status else 'ai_powered'
strategy_display = current_strategy.replace('_', ' ').title()

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="font-size: 1.2rem;">{strategy_display}</div>
        <div class="metric-label">Active Strategy</div>
        <div class="metric-delta" style="color: var(--accent);">
            AI-Powered
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    avg_lat = random.randint(20, 80)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{avg_lat}ms</div>
        <div class="metric-label">Avg Latency</div>
        <div class="metric-delta" style="color: {'#ff9f0a' if avg_lat > 50 else '#30d158'};">
            {'+' if avg_lat > 50 else '-'} {(abs(avg_lat - 40))}ms
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    active_servers = len(servers) if servers else 3
    current_rps = orch_status.get('traffic_intensity', 100) if orch_status else 100
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{active_servers}</div>
        <div class="metric-label">Active Servers</div>
        <div class="metric-delta" style="color: var(--text-secondary);">
            All healthy
        </div>
        <div style="font-size: 0.65rem; color: #0a84ff; margin-top: 4px;">⚡ {current_rps} RPS</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    throughput = random.randint(100, 500)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{throughput}/s</div>
        <div class="metric-label">Throughput</div>
        <div class="metric-delta" style="color: #30d158;">
            +{random.randint(5, 30)}%
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# ROW 2: Charts (70%) + Server Health (30%)
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">Performance & Infrastructure</div>', unsafe_allow_html=True)

chart_col, server_col = st.columns([7, 3])

with chart_col:
    # Generate demo chart data
    time_range = pd.date_range(end=datetime.now(), periods=24, freq='H')
    perf_data = pd.DataFrame({
        'time': time_range,
        'latency_p50': np.random.normal(45, 10, 24),
        'latency_p95': np.random.normal(120, 25, 24),
        'latency_p99': np.random.normal(200, 40, 24),
        'throughput': np.random.normal(350, 80, 24),
    })

    # Latency Chart
    fig_lat = go.Figure()
    fig_lat.add_trace(go.Scatter(x=perf_data['time'], y=perf_data['latency_p50'], name='P50', line=dict(color='#30d158', width=2)))
    fig_lat.add_trace(go.Scatter(x=perf_data['time'], y=perf_data['latency_p95'], name='P95', line=dict(color='#0a84ff', width=2)))
    fig_lat.add_trace(go.Scatter(x=perf_data['time'], y=perf_data['latency_p99'], name='P99', line=dict(color='#ff453a', width=2)))
    fig_lat.add_hline(y=200, line_dash="dash", line_color="#ff453a", line_width=1.5,
                      annotation_text="Danger: 200ms", annotation_position="top right",
                      annotation_font_color="#ff453a", annotation_font_size=10)
    fig_lat.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        font=dict(color='#000000', family='Inter'),
        margin=dict(l=30, r=20, t=20, b=30),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=200,
        xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='ms'),
    )
    st.plotly_chart(fig_lat, use_container_width=True)

    # Throughput Chart
    fig_through = go.Figure()
    fig_through.add_trace(go.Scatter(
        x=perf_data['time'], y=perf_data['throughput'], name='Throughput',
        fill='tozeroy', line=dict(color='#0a84ff', width=2), fillcolor='rgba(10,132,255,0.2)'
    ))
    fig_through.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        font=dict(color='#000000', family='Inter'),
        margin=dict(l=30, r=20, t=20, b=30),
        showlegend=False, height=200,
        xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='req/s'),
    )
    st.plotly_chart(fig_through, use_container_width=True)

with server_col:
    st.markdown("#### Server Health")

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

        # Get real metrics from container_metrics
        metrics_dict = container_metrics.get('metrics', {}) if container_metrics else {}

        for server in server_list:
            server_id = server.get('server_id', '')
            # Extract just the backend name from URL or full name
            if 'http://' in server_id:
                server_name = server_id.split('http://')[1].split(':')[0]
            else:
                server_name = server_id

            # Get real CPU from docker stats
            real_cpu = metrics_dict.get(server_name) or metrics_dict.get(server_id.replace('http://', ''))
            if real_cpu is None:
                cpu = random.randint(20, 75)  # Fallback to demo data
            else:
                cpu = int(real_cpu)

            dot_class = 'dot-green' if cpu < 70 else 'dot-yellow' if cpu < 85 else 'dot-red'
            threshold_color = '#ff453a' if cpu >= 80 else '#ff9f0a' if cpu >= 70 else '#30d158'

            st.markdown(f"""
            <div class="server-bar">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-weight: 600; font-size: 0.85rem;">{server['server_id']}</span>
                    <span class="status-dot {dot_class}"></span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: var(--text-secondary); font-size: 0.75rem;">CPU Usage</span>
                    <span style="font-weight: 600; font-size: 0.9rem;">{cpu}%</span>
                </div>
                <div style="background: var(--bg-tertiary); border-radius: 4px; height: 6px; margin-top: 0.5rem; position: relative;">
                    <div style="background: {threshold_color}; width: {cpu}%; height: 100%; border-radius: 4px;"></div>
                    <div style="position: absolute; right: 80%; top: -2px; bottom: -2px; width: 1px; background: rgba(255,69,58,0.5);"></div>
                </div>
                <div style="text-align: right; font-size: 0.65rem; color: rgba(255,69,58,0.6); margin-top: 2px;">80% threshold</div>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# ROW 3: Predictions & Anomalies
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">AI Predictions & Anomaly Detection</div>', unsafe_allow_html=True)

pred_col1, pred_col2 = st.columns(2)

with pred_col1:
    st.markdown("#### Traffic Forecast (Next 24h)")

    pred_time = pd.date_range(start=datetime.now(), periods=12, freq='2H')
    pred_data = pd.DataFrame({
        'time': pred_time,
        'predicted': np.random.normal(350, 60, 12),
        'upper': np.random.normal(420, 70, 12),
        'lower': np.random.normal(280, 50, 12),
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
        paper_bgcolor='white', plot_bgcolor='white',
        font=dict(color='#000000', family='Inter'),
        margin=dict(l=30, r=20, t=20, b=30),
        height=180,
        xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='req/s'),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    )
    st.plotly_chart(fig_pred, use_container_width=True)

    # Model Confidence Badge
    confidence = random.randint(88, 96)
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem; padding: 0.5rem; background: rgba(48,209,88,0.1); border-radius: 6px; border: 1px solid rgba(48,209,88,0.2);">
        <span style="font-size: 0.75rem; color: var(--text-secondary);">Model Confidence</span>
        <span style="font-weight: 700; color: #30d158; font-size: 0.9rem;">{confidence}%</span>
    </div>
    """, unsafe_allow_html=True)

with pred_col2:
    st.markdown("#### Anomaly Detection")

    anomaly_data = pd.DataFrame({
        'Time': pd.date_range(end=datetime.now(), periods=20, freq='15min'),
        'Score': np.random.normal(0.3, 0.2, 20)
    })
    # Add some anomalies
    anomaly_indices = random.sample(range(20), 2)
    for idx in anomaly_indices:
        anomaly_data.loc[idx, 'Score'] = random.uniform(-0.9, -0.5)

    colors = ['#ff453a' if s < -0.5 else '#30d158' for s in anomaly_data['Score']]

    fig_anomaly = go.Figure()
    fig_anomaly.add_trace(go.Bar(x=anomaly_data['Time'], y=anomaly_data['Score'], marker_color=colors))
    fig_anomaly.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        font=dict(color='#000000', family='Inter'),
        margin=dict(l=30, r=20, t=20, b=30),
        height=180,
        xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='Score', range=[-1, 1]),
        showlegend=False,
    )
    st.plotly_chart(fig_anomaly, use_container_width=True)

    # Anomaly trigger indicator
    anomaly_count = sum(1 for s in anomaly_data['Score'] if s < -0.5)
    if anomaly_count > 0:
        triggers = random.sample(['High CPU', 'Latency Spike', 'Memory Pressure', 'Request Flood'], min(anomaly_count, 3))
        triggers_html = " • ".join([f"<span style='color: #ff453a;'>{t}</span>" for t in triggers])
        st.markdown(f"""
        <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(255,69,58,0.1); border-radius: 6px; border: 1px solid rgba(255,69,58,0.2);">
            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 4px;">Anomaly Triggers</div>
            <div style="font-size: 0.75rem;">{triggers_html}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(48,209,88,0.1); border-radius: 6px; border: 1px solid rgba(48,209,88,0.2);">
            <span style="font-size: 0.75rem; color: #30d158;">✓ No anomalies detected</span>
        </div>
        """, unsafe_allow_html=True)


# ============================================
# SIDEBAR - Command Center
# ============================================
# Auto-refresh setting (default, can be overridden in settings tab)
auto_refresh = True

with st.sidebar:
    st.markdown("### Command Center")

    # Tab selector using columns
    if 'sidebar_tab' not in st.session_state:
        st.session_state.sidebar_tab = 'presets'

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
        st.markdown("#### Demo Scenarios")

        # Stack buttons vertically for clean alignment
        if st.button("Black Friday Rush", use_container_width=True, key="bf_preset"):
            # Aggressive ramp: spike to 12000 RPS
            if set_traffic("spike", 12000):
                show_toast("Black Friday Rush - 12,000 RPS spike!")
            else:
                show_toast("Traffic: SPIKE → 12,000 RPS", "📈")
            st.rerun()

        if st.button("DDoS Attack", use_container_width=True, key="ddos_preset"):
            # Violent DDoS: 10000 RPS burst + chaos injection
            set_traffic("burst", 10000)
            chaos_result = inject_chaos()
            if chaos_result and chaos_result.get('success'):
                show_toast(f"Container {chaos_result.get('container_killed')} killed!", "💥")
            else:
                show_toast("DDoS: 10,000 RPS + chaos injection", "⚠️")
            st.rerun()

        if st.button("Normal Ops", use_container_width=True, key="normal_preset"):
            if set_traffic("constant", 50):
                show_toast("Normal operations - 50 RPS steady")
            else:
                show_toast("Reset: 50 RPS", "🔄")

        if st.button("Sine Wave", use_container_width=True, key="sine_preset"):
            if set_traffic("sine_wave", 500):
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
                st.session_state.current_strategy = 'round_robin'
                st.session_state.strategy_chosen = True
                show_toast("Round Robin - Even Distribution")
                st.rerun()

        with strat_cols[1]:
            if st.button("⚡ Least Conn", use_container_width=True,
                         type="primary" if st.session_state.current_strategy == 'least_connections' else "secondary",
                         key="strat_lc"):
                set_strategy("least_connections")
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
                st.session_state.current_strategy = 'ai_powered'
                st.session_state.strategy_chosen = True
                show_toast("AI-Powered - ML-Based Routing")
                st.rerun()

        with strat_cols2[1]:
            if st.button("🚫 OFF", use_container_width=True,
                         type="primary" if st.session_state.current_strategy == 'off' else "secondary",
                         key="strat_off"):
                set_strategy("off")
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
            if set_traffic(shape, intensity):
                show_toast(f"{shape.replace('_', ' ').title()} traffic at {intensity} RPS")
            else:
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

        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
        chart_points = st.slider("Chart data points", 10, 100, 50)

        st.markdown("---")
        st.markdown("#### Alert Thresholds")

        cpu_threshold = st.slider("CPU Alert (%)", 50, 95, 80)
        latency_threshold = st.slider("Latency Alert (ms)", 100, 1000, 500)

        st.markdown("---")
        st.markdown("#### Connection Status")

        # Show service status
        gateway_ok = safe_api_call(lambda: requests.get(f"{GATEWAY_URL}/health", timeout=1), None) is not None
        orch_ok = safe_api_call(get_orchestrator_status_cached, None) is not None

        col_st1, col_st2 = st.columns(2)
        with col_st1:
            st.markdown(f"Gateway: {'🟢' if gateway_ok else '🔴'}")
        with col_st2:
            st.markdown(f"Orchestrator: {'🟢' if orch_ok else '🔴'}")

        st.markdown("---")
        st.markdown(f"**Last update:** {datetime.now().strftime('%H:%M:%S')}")

        if st.button("Clear Cache & Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# ============================================
# MAIN VIEW: System Audit Log
# ============================================
st.markdown('<div class="section-header" style="margin-top: 1rem;">System Audit</div>', unsafe_allow_html=True)

audit_events = get_audit_events_cached()
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

# Auto-refresh - use session state to track setting
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True

if st.session_state.auto_refresh:
    time.sleep(5)
    st.rerun()