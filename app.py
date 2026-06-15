import streamlit as st
import pandas as pd
import plotly.express as px
from flask import Flask, request
import threading
import socket
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import sys
import os
import numpy as np
from prescriptive.orchestrator import run_mcp_agent
current_folder = os.path.dirname(os.path.abspath(__file__))

if current_folder not in sys.path:
    sys.path.append(current_folder)

from forecast_engine import generate_forecast

@st.cache_resource
def get_global_list():
    return []

@st.cache_resource
def get_factory_status():
    return {"is_working": False}

@st.cache_resource
def get_shift_status():
    return {"is_active": False}

@st.cache_resource
def get_schedule_info():
    return {"text": "Waiting for simulation start..."}

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

shared_data_list = get_global_list() # these variables are shared across all refreshes and all threads
shared_status = get_factory_status() 
shared_schedule = get_schedule_info() 
shared_shift = get_shift_status()

app = Flask(__name__)

@app.route('/add_data', methods=['POST'])
def add_data():
    content = request.json
    if content:
        shared_data_list.append(content)
        return {"status": "success"}, 200
    return {"status": "error"}, 400

@app.route('/update_schedule_text', methods=['POST'])
def update_schedule_text():
    content = request.json
    if content:
        shared_schedule["text"] = content.get('text', "No schedule info")
        return {"status": "success"}, 200
    return {"status": "error"}, 400

@app.route('/update_status', methods=['POST'])
def update_status():
    content = request.json
    if content:
        shared_status["is_working"] = content.get('is_working', True)
        return {"status": "success"}, 200
    return {"status": "error"}, 400

@app.route('/update_shift', methods=['POST'])
def update_shift():
    content = request.json
    if content:
        shared_shift["is_active"] = content.get('is_active', True)
        return {"status": "success"}, 200
    return {"status": "error"}, 400

def run_server():
    app.run(port=5001, debug=False, use_reloader=False)

if 'server_started' not in st.session_state:
    if not is_port_in_use(5001):
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        st.session_state['server_started'] = True
    else:
        st.write("Data listener is already running on port 5001.")
        st.session_state['server_started'] = True


# user interface
st.set_page_config(page_title="Supply Chain Live Data", layout="wide", page_icon="💽")

st_autorefresh(interval=5000, key="datarefresh")

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'show_assistant' not in st.session_state:
    st.session_state.show_assistant = False
if "active_prompt" not in st.session_state:
    st.session_state.active_prompt = None

col_title, col_emoji = st.columns([0.9, 0.1])
with col_title:
    st.title("Supply Chain Live Data Dashboard 📊")

    if shared_data_list:
        latest_entry = shared_data_list[-1]
        sim_date_str = latest_entry.get("SimulationDate", "N/A")
        try:
            parts = sim_date_str.split(" ")
            if len(parts) >= 6:
                clean_date = f"{parts[1]} {parts[2]} {parts[5]} {parts[3]}"
            else:
                clean_date = sim_date_str
        except:
            clean_date = sim_date_str
        st.markdown(f"""
            <div style='text-align: left; color: #5D5D5D; font-size: 1.2em;'>
                <strong>SIMULATION TIME</strong><br>
                {clean_date}
            </div>
        """, unsafe_allow_html=True)

with col_emoji:
    is_working_now = shared_status.get("is_working", False)
    emoji = "☀️" if is_working_now else "🌖"
    order_label = 'Orders Arriving' if is_working_now else 'Orders Stopped'

    is_shift_active = shared_shift.get("is_active", False)
    shift_emoji = "🌘"
    shift_label = "Off Hours"
    try:
        sim_time_str = shared_data_list[-1].get("SimulationDate", "00:00:00")
        current_hour = int(sim_time_str.split(" ")[3].split(":")[0])

        if 8 <= current_hour < 12 or 13 <= current_hour < 18:
            shift_emoji = "🏭" 
            shift_label = "Working"
        elif 12 <= current_hour < 13:
            shift_emoji = "🍽️"
            shift_label = "Lunch Break"
        else:
            shift_emoji = "🌒"
            shift_label = "Off Hours"
    except:
        pass

    st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; gap: 20px; align-items: center; text-align: center;">
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2.5em; line-height: 2.0;">{shift_emoji}</span>
                <span style="font-size: 0.8em; color: #5D5D5D; margin-top: -5px;">{shift_label}</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2.5em; line-height: 2.0;">{emoji}</span>
                <span style="font-size: 0.8em; color: #5D5D5D; margin-top: -5px;">{order_label}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

st.markdown("""
    <style>
    .metric-card {
        background-color: #1e2130;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #4e5d6c;
    }
    </style>
    """, unsafe_allow_html=True)


st.sidebar.header("Active Shift Schedule")
st.sidebar.info(shared_schedule["text"])

is_working_now = shared_status.get("is_working", False)

status_color = "#079d68" if is_working_now else "#ff4b4b"
status_text = "ACTIVE" if is_working_now else "OFF SHIFT"
st.sidebar.markdown(f"Current Status: <strong style='color:{status_color};'>{status_text}</strong>", unsafe_allow_html=True)

st.sidebar.header("Prophet Forecasting Engine")
st.sidebar.caption(
    "Triggers a multivariate demand forecast based on the historical data stream. "
    "Ensure the simulation has run for at least 30 unique days (2 years recommended) "
    "to capture full seasonal trends."
)
st.sidebar.warning(
    "**Crucial:** Stop the simulation execution before generating the forecast "
    "to ensure complete dataset processing."
)
run_prediction = st.sidebar.button("Generate 1-Year Demand Forecast")

st.sidebar.markdown("---") 
st.sidebar.header("Got a question? Ask the AI assistant!")
if st.sidebar.button("Open AI Assistant Chat", type="primary", use_container_width=True):
    st.session_state.show_assistant = not st.session_state.show_assistant
    st.rerun()

current_data = globals()['shared_data_list']

if current_data:
    df = pd.DataFrame(current_data)

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    tot_orders = df['OrderID'].nunique() if 'OrderID' in df.columns else 0
    avg_wait = df['WaitOrder'].mean() if 'WaitOrder' in df.columns else 0
    max_bottleneck = df['WaitLogicCenter'].max() if 'WaitLogicCenter' in df.columns else 0
    total_co2 = df['CO2'].sum() if 'CO2' in df.columns else 0
    #timestamp = df['Timestamp'].nunique() if 'Timestamp' in df.columns else 0
    carbon_ratio = df['CarbonRatio'].mean() if 'CarbonRatio' in df.columns else 0

    market_index = df['MarketIndex'].iloc[-1] if 'MarketIndex' in df.columns else 0
    active_pf_lorries = df['ActivePFLorries'].iloc[-1] if 'ActivePFLorries' in df.columns else 0

    c1.metric("Total Orders", f"{tot_orders}")
    c2.metric("Average Order Wait Time", f"{avg_wait:.2f}h")
    c3.metric("Max Bottleneck from Production Floor to Logic Center", f"{max_bottleneck:.2f}h")
    c4.metric("Total CO2", f"{total_co2:.2f}kg")
    c5.metric("Average Carbon Ratio", f"{carbon_ratio:.2f}")
    c6.metric("Market Index", f"{market_index:.2f}")


    if 'WaitOrder' in df.columns:
        st.subheader("Real Time Order Processing Delay")
        #fig = px.line(df, x=df.index, y="WaitOrder", 
        #              #title="Real-Time Order Wait Times for Processing",
        #              template="plotly_dark",
        #              line_shape="spline",
        #              hover_data={"OrderID": True, "WaitOrder": ':.2f'})
        #
        #fig.update_traces(line_color='#00d4ff', line_width=3)
        fig = px.histogram(df, 
                           x="WaitOrder", 
                           nbins=40,
                           template="plotly_dark",
                           color_discrete_sequence=['#318CE7'],
                           labels={"WaitOrder": "Wait Time (Hours)", "count": "Number of Orders"})
        fig.update_layout(bargap=0.1)
        st.plotly_chart(fig, width='stretch')

    if 'WaitLogicCenter' in df.columns:
        st.subheader("Real Time Wait Times from Production Floor to Logic Centers")
        fig2 = px.histogram(df, 
                            x="WaitLogicCenter", 
                            nbins=40, 
                            template="plotly_dark",
                            color_discrete_sequence=['#fe6f5e'],
                            labels={"WaitLogicCenter": "Wait Time (Hours)", "count": "Number of Orders"})
        fig2.update_layout(bargap=0.1)
        st.plotly_chart(fig2, width='stretch')

    if 'CO2' in df.columns:
        st.subheader("CO2 Emissions per Order Over Time")
        fig_co2 = px.line(df, x=df.index, y="CO2", 
                          #title="CO2 Emissions per Order",
                          template="plotly_dark",
                          hover_data={"OrderID": True, "CO2": ':.2f'},
                          labels={"index": "Order Index", "CO2": "CO2 Emissions (kg)"})
        fig_co2.update_traces(line_color='#90ee90', line_width=3)
        st.plotly_chart(fig_co2, width='stretch')

    if 'Timestamp' in df.columns:
        st.subheader("Order Arrivals Over Time")
        if 'SimulationDate' in df.columns:
            def clean_anylogic_date(date_str):
                try:
                    parts = str(date_str).split()
                    if len(parts) >= 6:
                        # Reconstruct without the timezone item: Month Day Year Time
                        return f"{parts[1]} {parts[2]} {parts[5]} {parts[3]}"
                except:
                    pass
                return None

            df['CleanedDateText'] = df['SimulationDate'].apply(clean_anylogic_date)
            df['DateTime'] = pd.to_datetime(df['CleanedDateText'], format="%b %d %Y %H:%M:%S", errors='coerce')
        
        # Fallback if parsing fails
        if 'DateTime' not in df.columns or df['DateTime'].isna().all():
            df['DateTime'] = pd.to_datetime("2026-03-23") + pd.to_timedelta(df['Timestamp'].astype(int), unit='h')

        total_days_simulated = (df['DateTime'].max() - df['DateTime'].min()).days

        # Group data into periods
        if total_days_simulated > 30:
            df['TimePeriod'] = df['DateTime'].dt.to_period('M')
            xaxis_title = "Timeline (Aggregated Monthly Arrivals)"
        else:
            df['TimePeriod'] = df['DateTime'].dt.to_period('D')
            xaxis_title = "Timeline (Aggregated Daily Arrivals)"

        # Sort and group chronological history cleanly
        arrival_counts = df.groupby('TimePeriod').size().reset_index(name='OrderCount')
        arrival_counts['TimePeriod'] = arrival_counts['TimePeriod'].astype(str)

        fig_hourly = px.bar(arrival_counts, x='TimePeriod', y='OrderCount',
                            template="plotly_dark",
                            labels={"TimePeriod": "Timeline", "OrderCount": "Number of Orders"})
        fig_hourly.update_traces(marker_color='#ff69b4')
        fig_hourly.update_layout(xaxis_title=xaxis_title)
        st.plotly_chart(fig_hourly, width='stretch')
    
    if 'CenterName' in df.columns:
        st.subheader("Real Time Center Workload")
    
        center_data = df['CenterName'].value_counts().reset_index()
        center_data.columns = ['Center Name', 'Order Count']
    
        fig_workload = px.bar(
            center_data,
            x='Order Count',
            y='Center Name',
            orientation='h',
            color='Order Count',
            color_continuous_scale='Purp',
            template="plotly_dark"
        )
        st.plotly_chart(fig_workload, width='stretch')

    if 'ProductPrice' in df.columns and 'CompetitorPrice' in df.columns and 'SimulationDate' in df.columns:
        st.subheader("Competitor Price vs Our Product Price Weekly Trends")
        df_trends = df.copy()

        try:
            # Cleanly extract date parts bypassing changing timezones (CET/CEST)
            def clean_anylogic_date(date_str):
                try:
                    parts = str(date_str).split()
                    if len(parts) >= 6:
                        return f"{parts[1]} {parts[2]} {parts[5]} {parts[3]}"
                except:
                    pass
                return None

            df_trends['CleanedDateText'] = df_trends['SimulationDate'].apply(clean_anylogic_date)
            df_trends['DateTime'] = pd.to_datetime(df_trends['CleanedDateText'], format="%b %d %Y %H:%M:%S", errors='coerce')
            df_trends = df_trends.dropna(subset=['DateTime'])

            if not df_trends.empty:
                total_days_simulated = (df_trends['DateTime'].max() - df_trends['DateTime'].min()).days

                if total_days_simulated > 180:
                    freq_setting = 'ME'
                    xaxis_label = "Timeline (Aggregated Monthly Means)"
                    tick_format = '%Y-%m'
                elif total_days_simulated > 30:
                    freq_setting = 'W'
                    xaxis_label = "Timeline (Aggregated Weekly Means)"
                    tick_format = '%Y-%m-%d'
                else:
                    freq_setting = 'D'
                    xaxis_label = "Timeline (Aggregated Daily Means)"
                    tick_format = '%Y-%m-%d'

                weekly_prices = df_trends.groupby(pd.Grouper(key='DateTime', freq=freq_setting))[['CompetitorPrice', 'ProductPrice']].mean().reset_index()

                fig_price = go.Figure()

                fig_price.add_trace(go.Scatter(
                    x=weekly_prices['DateTime'], y=weekly_prices['CompetitorPrice'],
                    name='Competitor Avg Price',
                    line=dict(color='#ED1B24', width=3, shape='hv')
                ))

                fig_price.add_trace(go.Scatter(
                    x=weekly_prices['DateTime'], y=weekly_prices['ProductPrice'],
                    name='Our Avg Price',
                    line=dict(color='#318CE7', width=3, shape='spline')
                ))

                fig_price.update_layout(
                    template='plotly_dark',
                    xaxis_title=xaxis_label,
                    yaxis_title='Price (€)',
                    hovermode='x unified',
                    xaxis=dict(tickformat=tick_format)
                )
                st.plotly_chart(fig_price, width='stretch')
            else:
                st.info("Parsing dates... Waiting for valid timestamp records from simulation stream.")

        except Exception as e:
            st.error(f"Error processing trend line calculations: {e}")

    with st.expander("See Raw Data Stream"):
        st.dataframe(df.tail(10), width='stretch')
else:
    st.info("Waiting for first POST request from AnyLogic... Start the simulation to begin.")

st.markdown("<div id='forecast_section' style='position:absolute; height:0; width:0; margin:0; padding:0; border:none;'></div>", unsafe_allow_html=True)

if 'forecast_generated' not in st.session_state:
    st.session_state['forecast_generated'] = False
if 'cached_forecast' not in st.session_state:
    st.session_state['cached_forecast'] = None
if 'cached_historical' not in st.session_state:
    st.session_state['cached_historical'] = None
if 'cached_metrics' not in st.session_state:
    st.session_state['cached_metrics'] = None

forecast_container = st.container()

if run_prediction:
    st.session_state['forecast_generated'] = True

    with st.spinner("Training Prophet model and generating forecast"):
        try:
            if os.path.exists("results.csv"):
                    raw_df = pd.read_csv("results.csv")
   
                    price_col = 'ProductPrice' if 'ProductPrice' in raw_df.columns else 'product_price'
                    comp_price_col = 'CompetitorPrice' if 'CompetitorPrice' in raw_df.columns else 'competitor_price'
                    market_idx_col = 'MarketIndex' if 'MarketIndex' in raw_df.columns else 'market_index'
                    
                    raw_df = raw_df.dropna(subset=[price_col, comp_price_col, market_idx_col])
                    raw_df.to_csv("results.csv", index=False)
            
            forecast, model, historical_data, metrics_dict = generate_forecast("results.csv", forecast_periods=365)

            if forecast is not None:
                for col in ['yhat', 'yhat_lower', 'yhat_upper']:
                    forecast[col] = forecast[col].clip(lower=0)

                st.session_state['cached_forecast'] = forecast
                st.session_state['cached_historical'] = historical_data
                st.session_state['cached_metrics'] = metrics_dict

            else:
                st.error("Could not generate forecast data.")
                st.session_state['forecast_generated'] = False
        except Exception as e:
            st.error(f"Error generating forecast: {e}")
            st.session_state['forecast_generated'] = False


if st.session_state['forecast_generated'] and st.session_state['cached_forecast'] is not None:
    with forecast_container:
        st.markdown("---")
        st.subheader("Order Demand Forecast (Next 365 Days)")

        forecast = st.session_state['cached_forecast']
        historical_data = st.session_state['cached_historical']
        metrics = st.session_state['cached_metrics']

        max_hist_date = historical_data['ds'].max()
        historical_pred = forecast[forecast['ds'] <= max_hist_date]
        future_pred = forecast[forecast['ds'] > max_hist_date].copy()

        future_start_date = future_pred['ds'].min()
        future_end_date = future_pred['ds'].max()

        fig_forecast = go.Figure()

        fig_forecast.add_trace(go.Scatter(
            x=pd.concat([future_pred['ds'], future_pred['ds'].iloc[::-1]]),
            y=pd.concat([future_pred['yhat_upper'], future_pred['yhat_lower'].iloc[::-1]]),
            fill='toself',
            fillcolor='#89cff0',
            line=dict(color='rgba(255,255,255,0)'),
            opacity=0.3,
            hoverinfo="skip",
            name='Confidence Margin (80%)'
        ))

        fig_forecast.add_trace(go.Bar(
            x=future_pred['ds'], 
            y=future_pred['yhat'],
            name='Predicted Demand',
            marker_color='#007fff',
            opacity=0.85,
            marker_line_width=0
        ))

        fig_forecast.update_layout(
            template='plotly_dark',
            xaxis_title='Timeline Calendar Date (Zoomed to 1-Year Horizon)',
            yaxis_title='Daily Order Volumes (Counts)',
            hovermode='x unified',
            barmode='overlay',
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=40, b=40),
            xaxis=dict(range=[future_start_date, future_end_date])
        )

        st.plotly_chart(fig_forecast, width='stretch')

        st.markdown("### Forecast Accuracy Metrics")

        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            st.metric(
                label="Mean Absolute Error (MAE)", 
                value=f"{metrics['MAE']} orders",
                help="The average amount your forecast models miss daily targets. Closer to 0 is perfect."
            )
        
        with kpi_col2:
            st.metric(
                label="Root Mean Square Error (RMSE)", 
                value=f"{metrics['RMSE']} orders",
                help="Measures large prediction errors. Heavily factors occasional massive market shifts."
            )

        with kpi_col3:
            st.metric(
                label="Historical Training Data Size", 
                value=f"{metrics['TotalTrainingDays']} Days",
                help="The aggregate sample width of simulated operational logs parsed by Prophet."
            )

        y_true_vals = historical_data['y'].values
        y_pred_vals = forecast[forecast['ds'] <= max_hist_date]['yhat'].values
        daily_errors = np.abs(y_true_vals - y_pred_vals)

        fig_error = go.Figure()

        fig_error.add_trace(go.Histogram(
            x=daily_errors,
            xbins=dict(
                start=0.0,
                size=0.15
            ),
            name='Daily Prediction Errors',
            marker_color='#29AB87',
            opacity=0.85,
            marker_line=dict(color='rgba(255,255,255,0.2)', width=1)
        ))

        fig_error.add_trace(go.Scatter(
            x=[None], y=[None], mode='lines',
            line=dict(color='#318CE7', width=3),
            name=f'MAE Baseline ({metrics["MAE"]})'
        ))
        
        fig_error.add_trace(go.Scatter(
            x=[None], y=[None], mode='lines',
            line=dict(color='#ED1B24', width=3, dash='dash'),
            name=f'RMSE Baseline ({metrics["RMSE"]})'
        ))

        fig_error.add_vline(
            x=metrics['MAE'], 
            line_width=3, 
            line_dash="solid", 
            line_color="#318CE7",
            annotation_text=f"MAE: {metrics['MAE']}",
            annotation_position="top left"
        )

        fig_error.add_vline(
            x=metrics['RMSE'], 
            line_width=3, 
            line_dash="dash", 
            line_color="#ED1B24",
            annotation_text=f"RMSE: {metrics['RMSE']}",
            annotation_position="top right"
        )

        fig_error.update_layout(
            template='plotly_dark',
            title=dict(
                text="<b>Forecast Error Variance Profile</b>",
                font=dict(size=14)
            ),
            xaxis_title='Absolute Error Magnitude (Orders Deviation)',
            yaxis_title='Frequency (Number of Days Mapping This Error)',
            height=400,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=50, b=40),
            bargap=0.05
        )

        st.plotly_chart(fig_error, width='stretch')

# --- AUTO-REFRESH RESILIENT CHAT MATRIX ---
if st.session_state.show_assistant:
    st.markdown("---")
    st.markdown("### Real-Time Metrics AI Assistant")
    
    st.markdown("<p style='font-size: 13px; font-weight: bold; color: #007fff; margin-bottom: 5px;'>📋 QUICK MACRO COMMANDS</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    # Pipeline 1: Capture Macro Inputs
    current_query = None

    with col1:
        if st.button("📊 Analyze Bottlenecks", use_container_width=True, key="btn_bottlenecks"):
            current_query = "Please analyze the current order waiting times and provide insights on any bottlenecks that could impact our logistics centers"
            
    with col2:
        if st.button("🏢 Warehouse Impact", use_container_width=True, key="btn_warehouse"):
            current_query = "Based on the latest demand forecast, how many orders are expected next month and how will they impact the logistics centers?"
    with col3:
        if st.button("🚛 Fleet Constraints", use_container_width=True, key="btn_fleet"):
            current_query = "Based on the order volume expected for the next three months, analyze the current transportation fleet capacity."

    # Pipeline 2: Capture Custom Written Prompt
    user_input = st.chat_input("Ask a question about real-time metrics...", key="main_chat_input")
    if user_input:
        current_query = user_input
    
    
    if current_query:
        st.session_state.chat_history.append({"role": "user", "content": current_query})
        # 2. Run the agent and append response directly to history
        with st.spinner("Orchestrator parsing metrics via MCP engine..."):
            try:
                agent_response = run_mcp_agent(current_query)
                
                if not agent_response or str(agent_response).strip() == "":
                    agent_response = "Agent executed successfully but returned an empty text string."
                    
                st.session_state.chat_history.append({"role": "assistant", "content": agent_response})
            except Exception as e:
                error_msg = f"Exception caught in Execution Pipeline: {str(e)}"
                st.error(error_msg)
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        st.rerun()

    chat_container = st.container(height=380)
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                "<div style='text-align: center; color: #5c6773; padding-top: 100px; font-style: italic;'>"
                "✨ System Idle. Click a macro button above or type your own custom query to start."
                "</div>", 
                unsafe_allow_html=True
            )
        else:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    
    st.markdown("---")