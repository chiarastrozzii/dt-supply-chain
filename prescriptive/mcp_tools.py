import os
import pandas as pd
import json
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_resolved_path(relative_path):
    return os.path.abspath(os.path.join(BASE_DIR, relative_path))

def order_waiting_metrics():
    try:
        if not os.path.exists(get_resolved_path("../results.csv")):
            print("results.csv not found")
            return None

        df = pd.read_csv(get_resolved_path("../results.csv"))

        date_blueprint = "%a %b %d %H:%M:%S CET %Y"

        finish_time = pd.to_datetime(df['FinishTime'], format=date_blueprint, errors='coerce')
        start_time = pd.to_datetime(df['OrderCreationTime'], format=date_blueprint, errors='coerce')

        df['TotalCycleTime'] = (finish_time - start_time).dt.total_seconds() / 3600.0

        avg_total_cycle = round(float(df['TotalCycleTime'].mean()), 4)
        avg_wait_center = round(float(df['WaitLogicCenter'].mean()), 4) if 'WaitLogicCenter' in df.columns else 0.0
        avg_wait_order = round(float(df['WaitOrder'].mean()), 4) if 'WaitOrder' in df.columns else 0.0

        if avg_total_cycle > 4.0:
            severity_status = "Critical Bottleneck"
        elif avg_total_cycle > 2.0:
            severity_status = "Degraded Performance"
        else:
            severity_status = "Optimal Operational Threshold"

        text_output = (
            f"### REAL-TIME ORDER WAITING METRICS\n"
            f"- **Operational Status:** {severity_status}\n"
            f"- **Total Processed Orders (Sample):** {len(df)} orders\n\n"
            f"#### MACRO CYCLE PERFORMANCE\n"
            f"- **End-to-End Cycle Time:** `{avg_total_cycle}` hours\n\n"
            f"#### MICRO BOTTLENECK ANALYSIS\n"
            f"- **Transit & Intake Delay (WaitLogicCenter):** `{avg_wait_center}` hours\n"
            f"- **Queue Processing Delay (WaitOrder):** `{avg_wait_order}` hours\n"
        )
        return text_output
        
    except Exception as e:
        return f"⚠️ Failed to execute metrics calculation: {str(e)}"

#how many orders are expected next month and how will they impact the logicistic centers
def get_logistic_center_impact():
    DEFAULT_ORDERS_PER_WORKER = 40.0
    WORK_HOURS_PER_MONTH = 160.0
    try:
        config_path = get_resolved_path("../config.json")
        if not os.path.exists(config_path):
            return json.dumps({"error": f"Critical Error: '{config_path}' not found. Cannot proceed without original parameters."})
            
        with open(config_path, "r") as f:
            config_data = json.load(f)

        folder = get_resolved_path("../forecast_csv")
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
        if not files:
            return json.dumps({"error": "No forecast CSV files found in 'forecast_csv' folder."})

        latest_file = max(files, key=os.path.getmtime)
        df = pd.read_csv(latest_file, comment = '#')

        df['ds'] = pd.to_datetime(df['ds'])
        future_df = df[df['actual_volume'].isna()].copy()
        
        if not future_df.empty:
            working_days_df = future_df[future_df['ds'].dt.dayofweek < 5]
            next_month_working = working_days_df.head(22).copy()
            next_month_working['yhat'] = next_month_working['yhat'].clip(lower=0)
            total_expected_orders = int(next_month_working['yhat'].sum())
        else:
            total_expected_orders = 120

        results_path = get_resolved_path("../results.csv")
        if os.path.exists(results_path):
            results_df = pd.read_csv(results_path)
            total_past_orders = len(results_df)

            if total_past_orders > 0:
                pct_lc1_bolzano = len(results_df[results_df['TargetCenter'] == 1]) / total_past_orders
                pct_lc2_verona = len(results_df[results_df['TargetCenter'] == 2]) / total_past_orders
                pct_lc3_milan = len(results_df[results_df['TargetCenter'] == 3]) / total_past_orders

                if 'ProcessingTime' in results_df.columns:
                    avg_proc_time = results_df['ProcessingTime'].mean()
                    
                    if avg_proc_time > 0:
                        orders_per_worker = WORK_HOURS_PER_MONTH / avg_proc_time
                        calculated_from_data = True

                        orders_per_worker = max(10.0, min(orders_per_worker, 150.0))
            else:
                pct_lc1_bolzano, pct_lc2_verona, pct_lc3_milan = 0.20, 0.50, 0.30
        else:
            pct_lc1_bolzano, pct_lc2_verona, pct_lc3_milan = 0.20, 0.50, 0.30

        orders_floor = total_expected_orders
        orders_lc1 = total_expected_orders * pct_lc1_bolzano
        orders_lc2 = total_expected_orders * pct_lc2_verona
        orders_lc3 = total_expected_orders * pct_lc3_milan

        req_floor = max(1, int(orders_floor / orders_per_worker))
        req_lc1 = max(1, int(orders_lc1 / orders_per_worker))
        req_lc2 = max(1, int(orders_lc2 / orders_per_worker))
        req_lc3 = max(1, int(orders_lc3 / orders_per_worker))

        USE_CAP = False   
        MAX_WORKERS = 100  
        total_requested = req_floor + req_lc1 + req_lc2 + req_lc3

        if USE_CAP and total_requested > MAX_WORKERS:
            scale_factor = MAX_WORKERS / total_requested
            p_workersFloor = max(1, int(req_floor * scale_factor))
            p_workersLC1 = max(1, int(req_lc1 * scale_factor))
            p_workersLC2 = max(1, int(req_lc2 * scale_factor))
            p_workersLC3 = max(1, int(req_lc3 * scale_factor))
        else:
            p_workersFloor, p_workersLC1, p_workersLC2, p_workersLC3 = req_floor, req_lc1, req_lc2, req_lc3

        
        center_volumes = {
            "Bolzano (LC1)": int(orders_lc1),
            "Verona (LC2)": int(orders_lc2),
            "Milan (LC3)": int(orders_lc3)
        }
        fullest_center = max(center_volumes, key=center_volumes.get)

        text_output = (
            f"### PREDICTIVE ANALYSIS FOR NEXT MONTH:\n"
            f"- Total expected orders: `{total_expected_orders}`\n"
            f"- Distribution breakdown: Bolzano (`{int(orders_lc1)}`), Verona (`{int(orders_lc2)}`), Milan (`{int(orders_lc3)}`)\n"
            f"- Heaviest workload bottleneck: {fullest_center}\n\n"
            f"### PRESCRIPTIVE WORKFORCE RECONFIGURATION PLAN:\n"
            f"Please update the config variables to the following values to balance the workload:\n"
            f"- p_workersFloor = `{int(p_workersFloor)}`\n"
            f"- p_workersLC1 = `{int(p_workersLC1)}`\n"
            f"- p_workersLC2 = `{int(p_workersLC2)}`\n"
            f"- p_workersLC3 = `{int(p_workersLC3)}`"
        )

        return text_output

    except Exception as e:
        return json.dumps({"error": str(e)})

#check if our current supplier transportation fleet can handle the order volume expected for the next three months. if not, request more units to the transport agency
def check_transportation_capacity():
    try:
        config_path = get_resolved_path("../config.json")
        if not os.path.exists(config_path):
            return "Error: 'config.json' not found. Cannot analyze fleet capacity."
            
        with open(config_path, "r") as f:
            config_data = json.load(f)
        
        current_logistics = config_data.get("logisticsData", [])

        AVG_ROUND_TRIP_HOURS = 6.0 
        OPERATIONAL_HOURS_PER_DAY = 10.0
        WORKING_DAYS_IN_3_MONTHS = 66.0
        
        TOTAL_OPERATIONAL_HOURS = OPERATIONAL_HOURS_PER_DAY * WORKING_DAYS_IN_3_MONTHS
        trips_per_lorry_in_3_months = TOTAL_OPERATIONAL_HOURS / AVG_ROUND_TRIP_HOURS
        
        total_3month_current_capacity = 0
        for entry in current_logistics:
            if "sourceS" in entry["location"]:
                lorries = entry["lorries"]
                units = entry["unitsPerLorry"]
             
                total_3month_current_capacity += (lorries * units * trips_per_lorry_in_3_months)

        folder = get_resolved_path("../forecast_csv")
        if not os.path.exists(folder):
            return "Error: 'forecast_csv' folder not found."
            
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
        if not files:
            return "Error: No forecast files found to calculate 3-month demand."

        latest_file = max(files, key=os.path.getmtime)
        df = pd.read_csv(latest_file, comment='#')

        df['ds'] = pd.to_datetime(df['ds'])
        future_df = df[df['actual_volume'].isna()].copy()
        
        if not future_df.empty:
            future_df['yhat'] = future_df['yhat'].clip(lower=0)
            
            start_date = future_df['ds'].min()
            end_date = start_date + pd.Timedelta(days=90)
            quarterly_horizon_df = future_df[(future_df['ds'] >= start_date) & (future_df['ds'] <= end_date)]
            
            total_expected_3month_orders = int(quarterly_horizon_df['yhat'].sum())
        else:
            total_expected_3month_orders = 450

        deficit = total_expected_3month_orders - total_3month_current_capacity

        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            # Fallback check to see if it's stored in Streamlit secrets
            import streamlit as st
            github_token = st.secrets.get("GITHUB_TOKEN", None)
        if not github_token:
            return "Error: 'GITHUB_TOKEN' environment variable is not set."

        print("[MCP DIAGNOSTIC] Sending payload to GitHub Models API...")

        tool_client = OpenAI(
            api_key=github_token,
            base_url="https://models.inference.ai.azure.com"
        )

        agency_system_prompt = (
            "You are the Lead Fleet Dispatcher at Transportation Agency. "
            "Your job is to look at a factory's current fleet configuration and their projected order deficit, "
            "then issue an official proposal detailing exactly how many lorries they should have at each location. "
            "Respond strictly in plain text focusing only on the prescriptive changes."
        )

        agency_user_prompt = f"""
        Here is our current logistical setup for supplier transport:
        {json.dumps(current_logistics, indent=2)}

        Operational Analytics Briefing:
        - Total forecasted incoming orders for the next 3 months: {total_expected_3month_orders} units.
        - Our current fleet layout can transport a maximum of: {total_3month_current_capacity} units over 3 months.
        - Calculated Logistical Deficit: {deficit} units.

        If there is a deficit, please calculate a strategic increase in lorry counts across sourceS1, sourceS2, sourceS3, and sourceS4 to cover the extra {max(0, deficit)} units over the next 3 months. Keep the productionFloor lorries stable at 50 unless absolutely necessary.

        Please generate an official fleet modification dispatch text detailing exactly what the new 'lorries' variables should be changed to for each location.
        """

        response = tool_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": agency_system_prompt},
                {"role": "user", "content": agency_user_prompt}
            ],
            temperature=0.2
        )
        
        return response.choices[0].message.content

    except Exception as e:
        return f"Failed to execute fleet agency evaluation: {str(e)}"
       