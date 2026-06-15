import os
import pandas as pd
import sys
import json
import asyncio
from mcp.server.fastmcp import FastMCP
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
from mcp_tools import order_waiting_metrics, get_logistic_center_impact, check_transportation_capacity
from openai import OpenAI, AsyncOpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_resolved_path(relative_path):
    return os.path.abspath(os.path.join(BASE_DIR, relative_path))

mcp = FastMCP("Digital Twin Orchestrator")

@mcp.tool()
def get_order_waiting_metrics_tool():
    return order_waiting_metrics()

@mcp.tool()
def get_logistic_center_impact_tool():
    return get_logistic_center_impact()

@mcp.tool()
def analyze_fleet_capacity_tool():
    return check_transportation_capacity()

#resources that the orchestrator can read directly
@mcp.resource("resource://config")
def read_config_json():
    config_path = get_resolved_path("../config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return f.read()
    return "Config file not found."

@mcp.resource("resource://results")
def read_results_csv():
    results_path = get_resolved_path("../results.csv")
    if not os.path.exists(results_path):
        return "Results file not found."
    
    try:
        df = pd.read_csv(results_path)
        total_rows = len(df)
        
        # Capture a small snippet of the most recent 15 rows
        tail_string = df.tail(15).to_string(index=False)
        
        return (
            f"SIMULATION LOG SUMMARY (results.csv):\n"
            f"- Total historical records processed: {total_rows} orders\n"
            f"- Data Columns available: {', '.join(df.columns)}\n\n"
            f"--- LATEST 15 LOGGED ENTRIES ---\n"
            f"{tail_string}"
        )
    except Exception as e:
        return f"Error parsing results file: {str(e)}"

@mcp.resource("resource://forecast")
def read_forecast_csv():
    folder = get_resolved_path("../forecast_csv")
    if not os.path.exists(folder):
        return "Forecast directory not found."
        
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
    if not files:
        return "No forecast CSV files found."
        
    try:
        latest_file = max(files, key=os.path.getctime)
        df = pd.read_csv(latest_file, comment='#')
        
        future_predictions = df[df['actual_volume'].isna()]
        
        return (
            f"FORECAST SUMMARY ENGINE (File: {os.path.basename(latest_file)}):\n"
            f"- Total timeline scope: {len(df)} days\n"
            f"- Future prediction window: {len(future_predictions)} days out\n\n"
            f"--- NEXT 10 DAYS EXPECTED DEMAND FORECAST OVERVIEW ---\n"
            f"{future_predictions[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].head(10).to_string(index=False)}"
        )
    except Exception as e:
        return f"Error parsing forecast file: {str(e)}"


#prompts to build shortcut for the users
@mcp.prompt()
def check_waiting_metrics_prompt():
    return ("Please analyze the current order waiting times and provide insights on any bottlenecks that could impact our logistics centers")

@mcp.prompt()
def check_logistic_center_impact_prompt():
    return ("Based on the latest demand forecast, how many orders are expected next month and how will they impact the logistics centers? "
                "Please provide insights on the expected order distribution across centers and any potential staffing implications.")

@mcp.prompt()
def check_transportation_capacity_prompt():
    return ("Based on the order volume expected for the next three months, analyze the current transportation fleet capacity and "
    "provide recommendations on whether we need to request more units from the transport agency to handle the expected demand.")

def run_mcp_agent(prompt: str) -> str:
    prompt_lower = prompt.lower()
    
    # 1. Deterministic Macro Routing (Fast, zero API cost, completely reliable)
    if "waiting times" in prompt_lower or "bottlenecks" in prompt_lower:
        return order_waiting_metrics()
        
    elif "demand forecast" in prompt_lower or "next month" in prompt_lower:
        # Returns the prescriptive workforce text directly
        return get_logistic_center_impact()
        
    elif "three months" in prompt_lower or "fleet capacity" in prompt_lower:
        # Returns the transportation agency evaluation text directly
        return check_transportation_capacity()
    
    # 2. Fallback to standard OpenAI LLM if the user types a custom question
    gh_token = os.environ.get("GITHUB_TOKEN")
    if not gh_token:
        return "⚠️ Setup Error: GITHUB_TOKEN environment variable is missing!"

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=gh_token
    )

    config_ctx = read_config_json()
    results_ctx = read_results_csv()
    forecast_ctx = read_forecast_csv()

    if "not found" in str(config_ctx).lower() or "error" in str(config_ctx).lower():
        return f"⚠️ Local Config Error: The orchestrator couldn't read your config data. Details: {config_ctx}"
    if "not found" in str(results_ctx).lower() or "error" in str(results_ctx).lower():
        return f"⚠️ Local Results Error: The orchestrator couldn't read your simulation logs. Details: {results_ctx}"
    if "not found" in str(forecast_ctx).lower() or "error" in str(forecast_ctx).lower():
        return f"⚠️ Local Forecast Error: The orchestrator couldn't read your forecasting files. Details: {forecast_ctx}"

    system_instruction = (
        "You are the lead orchestrator of the company in charge of all the logistics. "
        "Answer user logistics questions concisely based on the live system resources provided below.\n\n"
        "=========================================\n"
        "LIVE SYSTEM LOGISTICS RESOURCES\n"
        "=========================================\n\n"
        f"MCP RESOURCE: resource://config\n{config_ctx}\n\n"
        f"MCP RESOURCE: resource://results\n{results_ctx}\n\n"
        f"MCP RESOURCE: resource://forecast\n{forecast_ctx}\n\n"
        "=========================================\n"
        "Analyze the provided parameters, metrics summaries, or forecast tables to provide accurate answers."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error gathering AI response: {str(e)}"

if __name__ == "__main__":
    mcp.run()