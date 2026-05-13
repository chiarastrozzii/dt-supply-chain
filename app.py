import streamlit as st
import pandas as pd
import plotly.express as px
from flask import Flask, request
import threading
import socket
from streamlit_autorefresh import st_autorefresh

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

st_autorefresh(interval=2000, key="datarefresh")

col_title, col_emoji = st.columns([0.9, 0.1])
with col_title:
    st.title("Supply Chain Live Data Dashboard 📊")

    if shared_data_list:
        latest_entry = shared_data_list[-1]
        sim_date_str = latest_entry.get("SimulationDate", "N/A")
        clean_date = " ".join(sim_date_str.split(" ")[:4])
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

current_data = globals()['shared_data_list']  # Access the global list directly

if current_data:
    df = pd.DataFrame(current_data)

    c1, c2, c3, c4, c5 = st.columns(5)

    tot_orders = df['OrderID'].nunique() if 'OrderID' in df.columns else 0
    avg_wait = df['WaitOrder'].mean() if 'WaitOrder' in df.columns else 0
    max_bottleneck = df['WaitLogicCenter'].max() if 'WaitLogicCenter' in df.columns else 0
    total_co2 = df['CO2'].sum() if 'CO2' in df.columns else 0
    #timestamp = df['Timestamp'].nunique() if 'Timestamp' in df.columns else 0
    carbon_ratio = df['CarbonRatio'].mean() if 'CarbonRatio' in df.columns else 0

    c1.metric("Total Orders", f"{tot_orders}")
    c2.metric("Average Order Wait Time", f"{avg_wait:.2f}h")
    c3.metric("Max Bottleneck from Production Floor\n to Logic center", f"{max_bottleneck:.2f}h")
    c4.metric("Total CO2", f"{total_co2:.2f}kg")
    c5.metric("Average Carbon Ratio", f"{carbon_ratio:.2f}")

    if 'WaitOrder' in df.columns:
        st.subheader("Real Time Order Processing Delay")
        fig = px.line(df, x=df.index, y="WaitOrder", 
                      #title="Real-Time Order Wait Times for Processing",
                      template="plotly_dark",
                      line_shape="spline",
                      hover_data={"OrderID": True, "WaitOrder": ':.2f'})
        
        fig.update_traces(line_color='#00d4ff', line_width=3)
        st.plotly_chart(fig, width='stretch')

    if 'WaitLogicCenter' in df.columns:
        st.subheader("Real Time Wait Times from Production Floor to Logic Centers")
        fig2 = px.line(df, x=df.index, y="WaitLogicCenter", 
                      #title="Real Time Logic Center Wait Times",
                      template="plotly_dark",
                      line_shape="spline",
                      hover_data={"OrderID": True, "WaitLogicCenter": ':.2f'})

        fig2.update_traces(line_color='#ff6e00', line_width=3)
        st.plotly_chart(fig2, width='stretch')

    if 'CO2' in df.columns:
        st.subheader("CO2 Emissions per Order Over Time")
        fig_co2 = px.line(df, x=df.index, y="CO2", 
                          #title="CO2 Emissions per Order",
                          template="plotly_dark",
                          hover_data={"OrderID": True, "CO2": ':.2f'})
        fig_co2.update_traces(line_color='#00ff7f', line_width=3)
        st.plotly_chart(fig_co2, width='stretch')

    if 'Timestamp' in df.columns:
        st.subheader("Order Arrivals Over Time")
        df['CreationHour'] = df['Timestamp'].astype(int)  # Convert seconds to hours
        arrival_counts = df.groupby('CreationHour').size().reset_index(name='OrderCount')

        #df['CreationHour'] = (df['Timestamp'] % 24).astype(int) 
        # Count orders per hour
        #arrival_counts = df.groupby('CreationHour').size().reindex(range(24), fill_value=0).reset_index(name='OrderCount')

        df['AbsHour'] = df['Timestamp'].astype(int) 
        max_h = int(df['AbsHour'].max()) if not df.empty else 24
        arrival_counts = df.groupby('AbsHour').size().reindex(range(max_h + 1), fill_value=0).reset_index(name='OrderCount')

        fig_hourly = px.bar(arrival_counts, x='AbsHour', y='OrderCount',
                            #title="Orders Arriving per Simulation Hour",
                            template="plotly_dark")
        fig_hourly.update_traces(marker_color='#ff69b4')
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

    with st.expander("See Raw Data Stream"):
        st.dataframe(df.tail(10), width='stretch')
else:
    st.info("Waiting for first POST request from AnyLogic... Start the simulation to begin.")
