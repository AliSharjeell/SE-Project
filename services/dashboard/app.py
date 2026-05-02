"""
Performance Dashboard - AI Infrastructure Manager

Modern, minimalist, Apple/Linear-inspired dark theme dashboard.
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import random

# Page config
st.set_page_config(
    page_title="AI Infrastructure Manager",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# API endpoints
GATEWAY_URL = "http://gateway:8000"
ML_SERVICE_URL = "http://ml-service:8000"


# Apple/Linear-inspired CSS
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
        --shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: var(--bg-primary);
        color: var(--text-primary);
    }

    /* Remove default padding */
    .block-container {
        padding: 0 1rem !important;
        padding-top: 1rem !important;
    }

    /* Hide Streamlit branding */
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Cards */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.5rem 0;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 600;
        color: var(--text-primary);
        line-height: 1;
    }

    .metric-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.5rem;
    }

    .metric-delta {
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }

    .delta-positive {
        color: var(--success);
    }

    .delta-negative {
        color: var(--error);
    }

    /* Headers */
    h1 {
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
        padding: 0;
    }

    h2 {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
    }

    h3 {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-secondary);
        margin: 0;
    }

    /* Charts */
    .js-plotly-plot .plotly {
        background: transparent !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--bg-secondary);
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 6px;
        color: var(--text-secondary);
        font-weight: 500;
        font-size: 0.875rem;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: var(--bg-tertiary);
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }

    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }

    .status-healthy {
        background-color: var(--success);
        box-shadow: 0 0 8px var(--success);
    }

    .status-warning {
        background-color: var(--warning);
        box-shadow: 0 0 8px var(--warning);
    }

    .status-critical {
        background-color: var(--error);
        box-shadow: 0 0 8px var(--error);
    }

    /* Server cards */
    .server-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary);
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] h3 {
        color: var(--text-primary);
    }
</style>
""", unsafe_allow_html=True)


def get_gateway_stats():
    """Fetch gateway statistics."""
    try:
        response = requests.get(f"{GATEWAY_URL}/stats", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_servers():
    """Fetch server list."""
    try:
        response = requests.get(f"{GATEWAY_URL}/servers", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []


def get_gateway_health():
    """Check gateway health."""
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def route_request(strategy: str):
    """Send a test request through the gateway."""
    try:
        response = requests.post(
            f"{GATEWAY_URL}/route",
            json={"strategy": strategy},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


# Header
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
    <h1>AI Infrastructure Manager</h1>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span class="status-indicator status-healthy"></span>
        <span style="color: var(--text-secondary); font-size: 0.875rem;">System Online</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Key Metrics Row
col1, col2, col3, col4 = st.columns(4)

# Simulated metrics for demo
metrics_data = {
    "total_requests": random.randint(10000, 50000),
    "requests_delta": round(random.uniform(-5, 15), 1),
    "avg_latency": random.randint(20, 80),
    "latency_delta": round(random.uniform(-10, 10), 1),
    "active_servers": 3,
    "servers_delta": 0,
    "throughput": random.randint(100, 500),
    "throughput_delta": round(random.uniform(-20, 30), 1),
}

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{metrics_data['total_requests']:,}</div>
        <div class="metric-label">Total Requests</div>
        <div class="metric-delta {'delta-positive' if metrics_data['requests_delta'] > 0 else 'delta-negative'}">
            {'+' if metrics_data['requests_delta'] > 0 else ''}{metrics_data['requests_delta']}%
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{metrics_data['avg_latency']}ms</div>
        <div class="metric-label">Avg Latency</div>
        <div class="metric-delta {'delta-negative' if metrics_data['latency_delta'] > 0 else 'delta-positive'}">
            {'+' if metrics_data['latency_delta'] > 0 else ''}{metrics_data['latency_delta']}ms
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{metrics_data['active_servers']}</div>
        <div class="metric-label">Active Servers</div>
        <div class="metric-delta" style="color: var(--text-secondary);">
            {metrics_data['servers_delta']:+d} from baseline
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{metrics_data['throughput']}/s</div>
        <div class="metric-label">Throughput</div>
        <div class="metric-delta {'delta-positive' if metrics_data['throughput_delta'] > 0 else 'delta-negative'}">
            {'+' if metrics_data['throughput_delta'] > 0 else ''}{metrics_data['throughput_delta']}%
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border-color: var(--border); margin: 1.5rem 0;'>", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Performance", "Servers", "Routing", "Predictions"])

with tab1:
    st.subheader("Performance Metrics")

    # Generate sample data
    time_range = pd.date_range(end=datetime.now(), periods=24, freq='H')
    perf_data = pd.DataFrame({
        'time': time_range,
        'latency_p50': np.random.normal(45, 10, 24),
        'latency_p95': np.random.normal(120, 25, 24),
        'latency_p99': np.random.normal(200, 40, 24),
        'throughput': np.random.normal(350, 80, 24),
    })

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("##### Latency Distribution")
        fig_latency = go.Figure()
        fig_latency.add_trace(go.Scatter(
            x=perf_data['time'], y=perf_data['latency_p50'],
            name='P50', line=dict(color='#30d158', width=2)
        ))
        fig_latency.add_trace(go.Scatter(
            x=perf_data['time'], y=perf_data['latency_p95'],
            name='P95', line=dict(color='#0a84ff', width=2)
        ))
        fig_latency.add_trace(go.Scatter(
            x=perf_data['time'], y=perf_data['latency_p99'],
            name='P99', line=dict(color='#ff453a', width=2)
        ))
        fig_latency.update_layout(
            template='plotly_dark',
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
            font=dict(color='#ffffff', family='Inter'),
            margin=dict(l=40, r=20, t=20, b=40),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=300,
            xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
            yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='ms'),
        )
        st.plotly_chart(fig_latency, use_container_width=True)

    with col_chart2:
        st.markdown("##### Throughput Over Time")
        fig_throughput = go.Figure()
        fig_throughput.add_trace(go.Scatter(
            x=perf_data['time'], y=perf_data['throughput'],
            name='Throughput',
            fill='tozeroy',
            line=dict(color='#0a84ff', width=2),
            fillcolor='rgba(10, 132, 255, 0.2)'
        ))
        fig_throughput.update_layout(
            template='plotly_dark',
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
            font=dict(color='#ffffff', family='Inter'),
            margin=dict(l=40, r=20, t=20, b=40),
            showlegend=False,
            height=300,
            xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
            yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='req/s'),
        )
        st.plotly_chart(fig_throughput, use_container_width=True)

with tab2:
    st.subheader("Server Status")

    servers = get_servers()
    if not servers:
        servers = [
            {"server_id": "backend-1", "host": "192.168.1.10", "port": 8000, "url": "http://backend-1:8000", "healthy": True, "active_connections": 12},
            {"server_id": "backend-2", "host": "192.168.1.11", "port": 8000, "url": "http://backend-2:8000", "healthy": True, "active_connections": 8},
            {"server_id": "backend-3", "host": "192.168.1.12", "port": 8000, "url": "http://backend-3:8000", "healthy": True, "active_connections": 15},
        ]

    cols = st.columns(3)
    for idx, server in enumerate(servers):
        with cols[idx % 3]:
            cpu = random.randint(20, 75)
            status_class = "status-healthy" if cpu < 70 else "status-warning"
            st.markdown(f"""
            <div class="server-card">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
                    <h2>{server['server_id']}</h2>
                    <span class="status-indicator {status_class}"></span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.75rem;">CPU</div>
                        <div style="font-size: 1.25rem; font-weight: 600;">{cpu}%</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.75rem;">Connections</div>
                        <div style="font-size: 1.25rem; font-weight: 600;">{server.get('active_connections', random.randint(5, 20))}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.75rem;">Host</div>
                        <div style="font-size: 0.875rem;">{server['host']}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.75rem;">Port</div>
                        <div style="font-size: 0.875rem;">{server['port']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.subheader("Load Balancing Strategies")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("##### Strategy Distribution")

        strategy_data = pd.DataFrame({
            'Strategy': ['Round Robin', 'Least Connections', 'AI-Powered'],
            'Requests': [random.randint(500, 2000), random.randint(300, 1500), random.randint(1000, 3000)]
        })

        fig_pie = go.Figure(data=[go.Pie(
            labels=strategy_data['Strategy'],
            values=strategy_data['Requests'],
            hole=0.6,
            marker=dict(colors=['#0a84ff', '#30d158', '#ff9f0a'])
        )])
        fig_pie.update_layout(
            template='plotly_dark',
            paper_bgcolor='transparent',
            font=dict(color='#ffffff', family='Inter'),
            margin=dict(l=40, r=40, t=40, b=40),
            height=280,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.markdown("##### Test Routing")

        strategy = st.selectbox(
            "Select Strategy",
            ["round_robin", "least_connections", "ai_powered"],
            format_func=lambda x: x.replace("_", " ").title()
        )

        if st.button("Send Test Request", use_container_width=True):
            result = route_request(strategy)
            if result:
                st.success(f"Request routed to {result.get('server', 'unknown')}")
            else:
                st.warning("Gateway not reachable - showing demo data")
                st.info("Demo: Would route to server-1 using Round Robin")

with tab4:
    st.subheader("AI Predictions")

    col_pred1, col_pred2 = st.columns(2)

    with col_pred1:
        st.markdown("##### Traffic Forecast")
        st.caption("Next 24 hours predicted traffic")

        pred_time = pd.date_range(start=datetime.now(), periods=12, freq='2H')
        pred_data = pd.DataFrame({
            'time': pred_time,
            'predicted': np.random.normal(350, 60, 12),
            'upper': np.random.normal(420, 70, 12),
            'lower': np.random.normal(280, 50, 12),
        })

        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=pred_data['time'], y=pred_data['upper'],
            name='Upper Bound', line=dict(color='rgba(48, 209, 88, 0.3)', width=1),
            fill='tonexty', fillcolor='rgba(48, 209, 88, 0.1)'
        ))
        fig_pred.add_trace(go.Scatter(
            x=pred_data['time'], y=pred_data['predicted'],
            name='Predicted', line=dict(color='#30d158', width=2)
        ))
        fig_pred.add_trace(go.Scatter(
            x=pred_data['time'], y=pred_data['lower'],
            name='Lower Bound', line=dict(color='rgba(48, 209, 88, 0.3)', width=1),
            fill='tonexty', fillcolor='rgba(10, 132, 255, 0.1)'
        ))
        fig_pred.update_layout(
            template='plotly_dark',
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
            font=dict(color='#ffffff', family='Inter'),
            margin=dict(l=40, r=20, t=20, b=40),
            height=280,
            xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
            yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='req/s'),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        )
        st.plotly_chart(fig_pred, use_container_width=True)

    with col_pred2:
        st.markdown("##### Anomaly Detection")

        anomaly_data = pd.DataFrame({
            'Time': pd.date_range(end=datetime.now(), periods=20, freq='10min'),
            'Score': np.random.normal(0.3, 0.2, 20)
        })
        anomaly_data.loc[random.sample(range(20), 2), 'Score'] = -0.8

        colors = ['#ff453a' if s < -0.5 else '#30d158' for s in anomaly_data['Score']]

        fig_anomaly = go.Figure()
        fig_anomaly.add_trace(go.Bar(
            x=anomaly_data['Time'],
            y=anomaly_data['Score'],
            marker_color=colors,
        ))
        fig_anomaly.update_layout(
            template='plotly_dark',
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
            font=dict(color='#ffffff', family='Inter'),
            margin=dict(l=40, r=20, t=20, b=40),
            height=280,
            xaxis=dict(showgrid=True, gridcolor='#2c2c2e'),
            yaxis=dict(showgrid=True, gridcolor='#2c2c2e', title='Anomaly Score',
                       range=[-1, 1]),
            showlegend=False,
        )
        st.plotly_chart(fig_anomaly, use_container_width=True)

# Sidebar
with st.sidebar:
    st.title("Settings")

    st.subheader("Refresh")
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
    refresh_interval = 5 if auto_refresh else 0

    st.subheader("Load Generator")
    traffic_pattern = st.selectbox(
        "Traffic Pattern",
        ["Constant", "Ramp", "Spike", "Sine Wave"],
        index=0
    )
    target_rate = st.slider("Target Rate (req/s)", 10, 500, 100)

    st.subheader("Display")
    chart_points = st.slider("Chart Data Points", 10, 100, 50)

    st.subheader("Alerts")
    cpu_threshold = st.slider("CPU Alert Threshold", 50, 95, 80)
    latency_threshold = st.slider("Latency Alert (ms)", 100, 1000, 500)

    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if auto_refresh:
    import time
    time.sleep(refresh_interval)
    st.rerun()