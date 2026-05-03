"""
Streamlit Dashboard for AI-Driven Infrastructure Manager.

Provides a real-time monitoring dashboard with metrics visualization,
load balancing insights, AI predictions, and auto-scaling visualization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional

# Import from project components (with fallback for standalone use)
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from components.monitor import MonitoringSystem, ServerMetrics
    from components.load_balancer import LoadBalancer, BackendServer, LoadBalancerStrategy
    from components.auto_scaler import AutoScaler, AutoScalerConfig, ScalingAction, ScalingActionType
    COMPONENTS_AVAILABLE = True
except ImportError:
    COMPONENTS_AVAILABLE = False


# ============================================================================
# Configuration and Session State
# ============================================================================

def init_session_state():
    """Initialize session state variables for dashboard."""
    if 'metrics_history' not in st.session_state:
        st.session_state.metrics_history = []
    if 'load_balancer' not in st.session_state:
        if COMPONENTS_AVAILABLE:
            st.session_state.load_balancer = create_demo_load_balancer()
        else:
            st.session_state.load_balancer = None
    if 'auto_scaler' not in st.session_state:
        if COMPONENTS_AVAILABLE:
            st.session_state.auto_scaler = create_demo_auto_scaler()
        else:
            st.session_state.auto_scaler = None
    if 'scaling_history' not in st.session_state:
        st.session_state.scaling_history = []
    if 'prediction_history' not in st.session_state:
        st.session_state.prediction_history = []
    if 'routing_history' not in st.session_state:
        st.session_state.routing_history = []
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()
    if 'server_count' not in st.session_state:
        st.session_state.server_count = 3


def create_demo_load_balancer():
    """Create a demo load balancer with sample servers."""
    lb = LoadBalancer(max_history=500)
    servers = [
        BackendServer(id=f"server-{i}", host=f"192.168.1.{10+i}", port=8000 + i)
        for i in range(1, 4)
    ]
    for server in servers:
        lb.add_server(server)
    return lb


def create_demo_auto_scaler():
    """Create a demo auto scaler."""
    config = AutoScalerConfig(
        min_servers=1,
        max_servers=10,
        scale_up_threshold=70.0,
        scale_down_threshold=30.0,
        scale_up_cooldown=30,
        scale_down_cooldown=60
    )
    return AutoScaler(config=config)


# ============================================================================
# Data Generation Functions
# ============================================================================

def generate_metric_data(timestamp: float) -> dict:
    """Generate simulated metric data."""
    cycle = (timestamp % 60) / 60
    base_cpu = 30 + cycle * 40 + random.gauss(0, 10)
    cpu = max(5.0, min(95.0, base_cpu + (20 if random.random() < 0.1 else 0)))

    memory = max(20.0, min(90.0, 45.0 + random.gauss(0, 8)))
    response_time = max(5.0, 50.0 + cycle * 200 + random.gauss(0, 30))
    request_rate = max(5.0, 200.0 + random.gauss(0, 50))
    connections = max(0, int(100 + random.gauss(0, 30)))

    return {
        'timestamp': timestamp,
        'datetime': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S'),
        'cpu_usage': round(cpu, 2),
        'memory_usage': round(memory, 2),
        'response_time': round(response_time, 2),
        'request_rate': round(request_rate, 2),
        'active_connections': connections
    }


def generate_prediction_data(timestamp: float) -> dict:
    """Generate simulated AI prediction data."""
    cycle = (timestamp % 60) / 60
    actual_traffic = 150 + cycle * 200 + random.gauss(0, 30)

    # AI prediction with some error
    prediction_error = random.gauss(0, 15)
    predicted_traffic = actual_traffic + prediction_error

    # Confidence interval (wider for further predictions)
    confidence = max(0.6, min(0.98, 0.85 - abs(prediction_error) / 100))
    margin = actual_traffic * (1 - confidence) * 0.5

    return {
        'timestamp': timestamp,
        'datetime': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S'),
        'predicted_traffic': round(predicted_traffic, 1),
        'actual_traffic': round(actual_traffic, 1),
        'confidence': round(confidence, 3),
        'lower_bound': round(predicted_traffic - margin, 1),
        'upper_bound': round(predicted_traffic + margin, 1)
    }


def generate_routing_data(lb: Optional, strategy: str, timestamp: float) -> dict:
    """Generate routing decision data."""
    if lb and hasattr(lb, 'get_all_servers'):
        servers = lb.get_all_servers()
        if servers:
            # Weighted distribution based on strategy
            if strategy == 'round_robin':
                weights = [1.0] * len(servers)
            elif strategy == 'least_connections':
                # Inverse of connections
                weights = [1.0 / max(1, s.active_connections) for s in servers]
            else:  # AI-powered
                weights = [random.uniform(0.5, 1.0) for _ in servers]

            total = sum(weights)
            selected_idx = random.choices(range(len(servers)), weights=weights)[0]
    else:
        servers = [f"server-{i}" for i in range(1, 4)]
        selected_idx = random.randint(0, len(servers) - 1)

    return {
        'timestamp': timestamp,
        'datetime': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S'),
        'strategy': strategy,
        'selected_server': servers[selected_idx] if isinstance(servers[0], str) else servers[selected_idx].id,
        'total_servers': len(servers) if not isinstance(servers[0], str) else len(servers)
    }


def update_metrics():
    """Update metrics history with new data points."""
    current_time = time.time()

    # Generate new metric
    metric = generate_metric_data(current_time)
    st.session_state.metrics_history.append(metric)

    # Keep last 100 points for charts
    if len(st.session_state.metrics_history) > 100:
        st.session_state.metrics_history = st.session_state.metrics_history[-100:]

    # Generate prediction
    prediction = generate_prediction_data(current_time)
    st.session_state.prediction_history.append(prediction)
    if len(st.session_state.prediction_history) > 100:
        st.session_state.prediction_history = st.session_state.prediction_history[-100:]

    # Generate routing decision
    strategies = ['round_robin', 'least_connections', 'ai_powered']
    routing = generate_routing_data(
        st.session_state.load_balancer,
        random.choice(strategies),
        current_time
    )
    st.session_state.routing_history.append(routing)
    if len(st.session_state.routing_history) > 100:
        st.session_state.routing_history = st.session_state.routing_history[-100:]

    # Simulate scaling events
    if random.random() < 0.05:  # 5% chance per update
        action_type = random.choice(['scale_up', 'scale_down', 'stable'])
        if action_type == 'scale_up':
            st.session_state.server_count = min(10, st.session_state.server_count + 1)
        elif action_type == 'scale_down':
            st.session_state.server_count = max(1, st.session_state.server_count - 1)

        scaling_action = {
            'timestamp': current_time,
            'datetime': datetime.fromtimestamp(current_time).strftime('%H:%M:%S'),
            'action': action_type,
            'server_count': st.session_state.server_count
        }
        st.session_state.scaling_history.append(scaling_action)
        if len(st.session_state.scaling_history) > 50:
            st.session_state.scaling_history = st.session_state.scaling_history[-50:]

    st.session_state.last_update = current_time


# ============================================================================
# Dashboard UI Components
# ============================================================================

def render_sidebar():
    """Render sidebar configuration controls."""
    st.sidebar.title("Dashboard Settings")

    # Refresh settings
    st.sidebar.subheader("Refresh Settings")
    auto_refresh = st.sidebar.checkbox("Auto-refresh (5s)", value=True)
    refresh_interval = 5

    # Scenario simulation
    st.sidebar.subheader("Scenario Simulation")
    scenario = st.sidebar.selectbox(
        "Load Scenario",
        ["Normal", "High Traffic", "Low Traffic", "Spike", "Sustained Load"]
    )

    # Display settings
    st.sidebar.subheader("Display")
    chart_points = st.sidebar.slider("Chart Data Points", 20, 100, 50)

    # Custom thresholds
    st.sidebar.subheader("Alert Thresholds")
    cpu_threshold = st.sidebar.slider("CPU Alert Threshold", 50, 95, 80)
    response_threshold = st.sidebar.slider("Response Time Alert (ms)", 100, 1000, 500)

    return auto_refresh, refresh_interval, scenario, chart_points, cpu_threshold, response_threshold


def render_overview_section():
    """Render the Overview section with system status cards."""
    st.header("System Overview")

    # Get latest metrics
    latest = st.session_state.metrics_history[-1] if st.session_state.metrics_history else None

    # Create metric cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Active Servers",
            st.session_state.server_count,
            delta=None
        )

    with col2:
        traffic = latest['request_rate'] if latest else 0
        st.metric(
            "Traffic Rate",
            f"{traffic:.0f} req/s",
            delta=f"{random.uniform(-10, 15):.1f}%" if latest else None
        )

    with col3:
        cpu = latest['cpu_usage'] if latest else 0
        cpu_delta = -5.2 if latest else None
        st.metric(
            "CPU Usage",
            f"{cpu:.1f}%",
            delta=cpu_delta
        )

    with col4:
        response = latest['response_time'] if latest else 0
        st.metric(
            "Avg Response Time",
            f"{response:.0f}ms",
            delta=f"{random.uniform(-20, 30):.0f}ms" if latest else None
        )

    # System status bar
    st.subheader("System Status")
    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        health = "Healthy" if (latest and latest['cpu_usage'] < 70) else "Warning"
        health_color = "green" if health == "Healthy" else "yellow"
        st.markdown(f"**Health Status:** :{health_color}[{health}]")

    with status_col2:
        active_conn = latest['active_connections'] if latest else 0
        st.markdown(f"**Active Connections:** {active_conn}")

    with status_col3:
        uptime = datetime.now().strftime('%H:%M:%S')
        st.markdown(f"**Dashboard Uptime:** {uptime}")


def render_realtime_metrics_section(chart_points: int):
    """Render Real-time Metrics section with line charts."""
    st.header("Real-time Metrics")

    if not st.session_state.metrics_history:
        st.info("Collecting metrics... Please wait.")
        return

    df = pd.DataFrame(st.session_state.metrics_history[-chart_points:])

    # Create tabs for different metrics
    tab1, tab2, tab3 = st.tabs(["CPU & Memory", "Response Time", "Connections"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['datetime'],
            y=df['cpu_usage'],
            name='CPU Usage %',
            line=dict(color='#FF6B6B', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df['datetime'],
            y=df['memory_usage'],
            name='Memory Usage %',
            line=dict(color='#4ECDC4', width=2)
        ))
        fig.update_layout(
            title="CPU and Memory Usage",
            xaxis_title="Time",
            yaxis_title="Usage %",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['datetime'],
            y=df['response_time'],
            name='Response Time (ms)',
            line=dict(color='#45B7D1', width=2),
            fill='tozeroy',
            fillcolor='rgba(69, 183, 209, 0.2)'
        ))
        fig.update_layout(
            title="Response Time",
            xaxis_title="Time",
            yaxis_title="Milliseconds",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['datetime'],
            y=df['active_connections'],
            name='Active Connections',
            line=dict(color='#96CEB4', width=2),
            fill='tozeroy',
            fillcolor='rgba(150, 206, 180, 0.2)'
        ))
        fig.add_trace(go.Scatter(
            x=df['datetime'],
            y=df['request_rate'],
            name='Request Rate',
            line=dict(color='#FFEAA7', width=2)
        ))
        fig.update_layout(
            title="Connections and Request Rate",
            xaxis_title="Time",
            yaxis_title="Count / Rate",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)


def render_load_balancer_section():
    """Render Load Balancer section with server distribution."""
    st.header("Load Balancer")

    if not st.session_state.routing_history:
        st.info("Collecting routing data...")
        return

    routing_df = pd.DataFrame(st.session_state.routing_history[-30:])

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Routing Strategy Distribution")
        strategy_counts = routing_df['strategy'].value_counts()
        fig = go.Figure(data=[
            go.Bar(
                x=strategy_counts.index,
                y=strategy_counts.values,
                marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1']
            )
        ])
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Server Selection History")
        server_counts = routing_df['selected_server'].value_counts()
        fig = go.Figure(data=[
            go.Pie(
                labels=server_counts.index,
                values=server_counts.values,
                hole=0.4,
                marker_colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
            )
        ])
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    # Routing decisions table
    st.subheader("Recent Routing Decisions")
    display_cols = ['datetime', 'strategy', 'selected_server']
    st.dataframe(routing_df[display_cols].tail(10), use_container_width=True)


def render_ai_predictions_section(chart_points: int):
    """Render AI Predictions section with predicted vs actual traffic."""
    st.header("AI Predictions")

    if not st.session_state.prediction_history:
        st.info("Collecting prediction data...")
        return

    df = pd.DataFrame(st.session_state.prediction_history[-chart_points:])

    # Predicted vs Actual traffic chart
    fig = go.Figure()

    # Actual traffic
    fig.add_trace(go.Scatter(
        x=df['datetime'],
        y=df['actual_traffic'],
        name='Actual Traffic',
        line=dict(color='#4ECDC4', width=2)
    ))

    # Predicted traffic
    fig.add_trace(go.Scatter(
        x=df['datetime'],
        y=df['predicted_traffic'],
        name='AI Predicted',
        line=dict(color='#FF6B6B', width=2, dash='dash')
    ))

    # Confidence interval
    fig.add_trace(go.Scatter(
        x=df['datetime'].tolist() + df['datetime'].tolist()[::-1],
        y=df['upper_bound'].tolist() + df['lower_bound'].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(255, 107, 107, 0.2)',
        line=dict(color='rgba(255, 107, 107, 0.2)'),
        name='Confidence Interval',
        showlegend=True
    ))

    fig.update_layout(
        title="Traffic Prediction: Actual vs AI Forecast",
        xaxis_title="Time",
        yaxis_title="Traffic (requests/sec)",
        height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Prediction metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        latest_pred = df.iloc[-1]
        accuracy = 100 - abs(latest_pred['predicted_traffic'] - latest_pred['actual_traffic']) / latest_pred['actual_traffic'] * 100
        st.metric("Prediction Accuracy", f"{max(0, accuracy):.1f}%")

    with col2:
        avg_confidence = df['confidence'].mean()
        st.metric("Avg Confidence", f"{avg_confidence * 100:.1f}%")

    with col3:
        error = abs(df['predicted_traffic'] - df['actual_traffic']).mean()
        st.metric("Mean Error", f"{error:.1f} req/s")


def render_auto_scaling_section():
    """Render Auto-Scaling section with scaling events timeline."""
    st.header("Auto-Scaling")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Scaling Events Timeline")

        if not st.session_state.scaling_history:
            st.info("No scaling events recorded yet.")
        else:
            df = pd.DataFrame(st.session_state.scaling_history)

            # Server count over time
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['datetime'],
                y=df['server_count'],
                name='Server Count',
                line=dict(color='#45B7D1', width=2),
                mode='lines+markers'
            ))
            fig.update_layout(
                title="Server Count History",
                xaxis_title="Time",
                yaxis_title="Number of Servers",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Scaling Statistics")
        st.metric("Current Servers", st.session_state.server_count)
        st.metric("Min Servers", 1)
        st.metric("Max Servers", 10)

        # Scale up/down counts
        if st.session_state.scaling_history:
            df = pd.DataFrame(st.session_state.scaling_history)
            scale_ups = (df['action'] == 'scale_up').sum()
            scale_downs = (df['action'] == 'scale_down').sum()
            st.metric("Scale Up Events", scale_ups)
            st.metric("Scale Down Events", scale_downs)

    # Scaling events table
    if st.session_state.scaling_history:
        st.subheader("Recent Scaling Actions")
        df = pd.DataFrame(st.session_state.scaling_history[-10:])
        df_display = df[['datetime', 'action', 'server_count']].copy()
        df_display.columns = ['Time', 'Action', 'Server Count']
        df_display['Action'] = df_display['Action'].map({
            'scale_up': 'Scale Up',
            'scale_down': 'Scale Down',
            'stable': 'Stable'
        })
        st.dataframe(df_display, use_container_width=True)


def render_comparison_section():
    """Render Comparison section for routing strategy comparison."""
    st.header("Strategy Comparison")

    if not st.session_state.routing_history:
        st.info("Collecting comparison data...")
        return

    df = pd.DataFrame(st.session_state.routing_history)

    # Calculate metrics for each strategy
    strategies = df['strategy'].unique()
    comparison_data = []

    for strategy in strategies:
        strategy_df = df[df['strategy'] == strategy]
        comparison_data.append({
            'Strategy': strategy.replace('_', ' ').title(),
            'Requests': len(strategy_df),
            'Avg Response': f"{random.randint(50, 150)}ms",
            'Load Distribution': f"{random.randint(60, 100)}%",
            'Efficiency': f"{random.randint(75, 99)}%"
        })

    comparison_df = pd.DataFrame(comparison_data)

    st.subheader("Strategy Performance Metrics")
    st.dataframe(comparison_df, use_container_width=True)

    # Visualization
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Request Distribution by Strategy")
        strategy_counts = df['strategy'].value_counts()
        fig = go.Figure(data=[
            go.Bar(
                x=[s.replace('_', ' ').title() for s in strategy_counts.index],
                y=strategy_counts.values,
                marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1']
            )
        ])
        fig.update_layout(
            title="Total Requests per Strategy",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Strategy Characteristics")
        characteristics = {
            'Round Robin': ['Simple', 'Fair distribution', 'No awareness'],
            'Least Connections': ['Load-aware', 'Dynamic', 'May lag'],
            'AI-Powered': ['Predictive', 'Optimal', 'Complex']
        }

        char_text = ""
        for strategy, traits in characteristics.items():
            char_text += f"**{strategy}**\n"
            for trait in traits:
                char_text += f"  - {trait}\n"
            char_text += "\n"

        st.markdown(char_text)


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main Streamlit application entry point."""

    # Page configuration
    st.set_page_config(
        page_title="AI Infrastructure Manager Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state()

    # Custom CSS - Dark theme styling
    st.markdown("""
    <style>
    /* Main content styling */
    .stApp {
        background-color: #1a1a2e;
        color: #e0e0e0;
    }
    .stMetric {
        background-color: #16213e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #0f3460;
    }
    .stMetric label {
        color: #a0a0a0 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #e0e0e0 !important;
    }
    h1 {
        color: #e0e0e0;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
    }
    h2 {
        color: #e0e0e0;
        margin-top: 20px;
    }
    h3 {
        color: #c0c0c0;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #16213e;
    }
    .stTabs [data-baseweb="tab"] {
        color: #a0a0a0;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #0f3460;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a1a2e !important;
        color: #3498db !important;
    }
    .streamlit-expanderHeader {
        color: #e0e0e0;
        font-weight: bold;
    }
    .st-expander {
        background-color: #16213e;
        border: 1px solid #0f3460;
    }
    .stSubheader {
        color: #e0e0e0;
    }
    /* Fix for markdown text - use more specific selectors to avoid affecting Streamlit internals */
    .stMarkdown p, .stMarkdown span, .stMarkdown div,
    .element-container p, .element-container span,
    .stAlert p, .stAlert span, .stAlert div {
        color: #e0e0e0;
    }
    .stAlert {
        background-color: #16213e;
    }
    /* DataFrame styling */
    .dataframe {
        background-color: #1a1a2e;
        color: #e0e0e0;
    }
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #16213e;
    }
    .stSidebar .stMarkdown {
        color: #e0e0e0;
    }
    /* Info/Warning boxes */
    .st-emotion-cache-1vbjmh {
        color: #e0e0e0;
    }
    /* Section containers */
    .element-container {
        background-color: transparent;
    }
    /* Horizontal lines */
    hr {
        border-color: #0f3460;
    }
    </style>
    """, unsafe_allow_html=True)

    # Render sidebar
    auto_refresh, refresh_interval, scenario, chart_points, cpu_threshold, response_threshold = render_sidebar()

    # Main title
    st.title("AI-Driven Infrastructure Manager")
    st.markdown(f"**Scenario:** {scenario} | **Last Update:** {datetime.now().strftime('%H:%M:%S')}")

    # Update metrics
    update_metrics()

    # Manual refresh with button
    if auto_refresh:
        if st.button("Refresh Metrics"):
            st.rerun()

    # Render dashboard sections
    tab_overview, tab_metrics, tab_lb, tab_predictions, tab_scaling, tab_compare = st.tabs([
        "Overview",
        "Real-time Metrics",
        "Load Balancer",
        "AI Predictions",
        "Auto-Scaling",
        "Comparison"
    ])

    with tab_overview:
        render_overview_section()

    with tab_metrics:
        render_realtime_metrics_section(chart_points)

    with tab_lb:
        render_load_balancer_section()

    with tab_predictions:
        render_ai_predictions_section(chart_points)

    with tab_scaling:
        render_auto_scaling_section()

    with tab_compare:
        render_comparison_section()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #7f8c8d;'>"
        "AI-Driven Infrastructure Manager Dashboard | University SE Project"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()