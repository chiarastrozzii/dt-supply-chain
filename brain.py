import os
import threading
import requests

def _async_post(url, data):
    try:
        requests.post(url, json=data, timeout=1.0)
    except:
        pass

def check_bottleneck(avg_wait_time, max_allowed_wait):
    try:
        wait = float(avg_wait_time)
        limit = float(max_allowed_wait)
    except (ValueError, TypeError):
        return "DATA ERROR: Invalid input type"
    
    if wait > (limit * 2):
        return f"CRITICAL DELAY: Supplier 4 is stalling! (Avg: {round(wait, 2)} days)"
    elif wait > limit:
        return f"WARNING: Buffer growing."
    else:
        return "SYSTEM OK: Flow is synchronized."

def send_to_dashboard(order_id, center_name, wait_order, wait_logic, co2, simulation_date, timestamp, carbon_ratio, market_index, competitor_price, product_price, active_pf_lorries):
    url = "http://localhost:5001/add_data" #server

    data = {
        "OrderID": order_id,
        "CenterName": center_name,
        "WaitOrder": wait_order,
        "WaitLogicCenter": wait_logic,
        "CO2": co2,
        "SimulationDate" : simulation_date,
        "Timestamp" : timestamp,
        "CarbonRatio" : carbon_ratio,
        "MarketIndex": market_index,
        "CompetitorPrice": competitor_price,
        "ProductPrice": product_price,
        "ActivePFLorries": active_pf_lorries
    }
    threading.Thread(target=_async_post, args=(url, data), daemon=True).start()

    #try:
    #    requests.post(url, json=data, timeout=0.1)
    #except Exception as e:
    #    print(f"Connection Error: {e}")

def update_factory_status(is_working):
    url = "http://localhost:5001/update_status"
    data = {"is_working": is_working}
    threading.Thread(target=_async_post, args=(url, data), daemon=True).start()
    #try:
    #    requests.post(url, json=data, timeout=0.1)
    #except:
    #    pass

def set_schedule_info(description):
    url = "http://localhost:5001/update_schedule_text"
    data = {"text": description}
    threading.Thread(target=_async_post, args=(url, data), daemon=True).start()

def update_shift_status(is_active):
    url = "http://localhost:5001/update_shift"
    data = {"is_active": is_active}
    threading.Thread(target=_async_post, args=(url, data), daemon=True).start()