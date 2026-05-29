import pandas as pd 
from prophet import Prophet
import os
import matplotlib.pyplot as plt
from datetime import datetime

def generate_forecast(data_path, forecast_periods):
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Could not find the simulation log file at: {data_path}")
        
    df = pd.read_csv(data_path)

    if len(df) < 30:
        print("⚠️ Not enough history points yet to build a stable forecast curve.")
        return None, None

    def parse_anylogic_date(date_str):
        try:
            months_map = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                          'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
            parts = str(date_str).split()
            if len(parts) >= 6:
                return f"{parts[5]}-{months_map[parts[1]]}-{parts[2].zfill(2)} {parts[3]}"
        except:
            pass
        return None

    if 'OrderCreationTime' in df.columns:
        df['CleanedTime'] = df['OrderCreationTime'].apply(parse_anylogic_date)
        df['SimTime'] = pd.to_datetime(df['CleanedTime'], errors='coerce')
    else:
        df['SimTime'] = pd.to_datetime("2026-03-02") + pd.to_timedelta(df['OrderCreationTime'].astype(int), unit='h')

    df = df.dropna(subset=['SimTime'])

    df['ds'] = df['SimTime'].dt.normalize()

    price_col = 'ProductPrice' if 'ProductPrice' in df.columns else 'product_price'
    comp_price_col = 'CompetitorPrice' if 'CompetitorPrice' in df.columns else 'competitor_price'
    market_idx_col = 'MarketIndex' if 'MarketIndex' in df.columns else 'market_index'

    #compress raw orders down into distinct, structured day steps
    daily_data = df.groupby('ds').agg(
        y=('OrderCreationTime', 'size'),
        our_price=(price_col, 'mean'),
        comp_price=(comp_price_col, 'mean'),
        market_index=(market_idx_col, 'mean') 
    ).reset_index()

    daily_data['price_difference'] = daily_data['comp_price'] - daily_data['our_price']

    full_timeline = pd.date_range(start=daily_data['ds'].min(), end=daily_data['ds'].max(), freq='D')
    daily_data = daily_data.set_index('ds').reindex(full_timeline).reset_index()
    daily_data.columns = ['ds', 'y', 'our_price', 'comp_price', 'market_index', 'price_difference']
 
    daily_data['y'] = daily_data['y'].fillna(0)
    daily_data['our_price'] = daily_data['our_price'].ffill().bfill()
    daily_data['comp_price'] = daily_data['comp_price'].ffill().bfill()
    daily_data['market_index'] = daily_data['market_index'].ffill().bfill()
    daily_data['price_difference'] = daily_data['price_difference'].ffill().bfill()

    if len(daily_data) < 30:
        print("⚠️ Simulation has not run for enough unique days to calculate trends.")
        return None, None, None

    # 5. Initialize Prophet Causal Architecture
    model = Prophet(
        growth='linear',
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )

    model.add_regressor('our_price', prior_scale=0.5)
    model.add_regressor('comp_price', prior_scale=0.5)
    model.add_regressor('market_index', prior_scale=0.5)
    model.add_regressor('price_difference', prior_scale=0.5)

    print(f"📈 Training Multivariate Demand Engine on {len(daily_data)} operational days...")
    model.fit(daily_data)

    future = model.make_future_dataframe(periods=forecast_periods, freq='D')
    future = future.merge(daily_data[['ds', 'our_price', 'comp_price', 'market_index', 'price_difference']], on='ds', how='left')

    future['day_of_year'] = future['ds'].dt.dayofyear
    daily_data['day_of_year'] = daily_data['ds'].dt.dayofyear

    seasonal_baselines = daily_data.groupby('day_of_year')[['our_price', 'comp_price', 'market_index', 'price_difference']].mean()

    future = future.set_index('day_of_year')
    future[['our_price', 'comp_price', 'market_index', 'price_difference']] = future[['our_price', 'comp_price', 'market_index', 'price_difference']].fillna(seasonal_baselines)
    future = future.reset_index(drop=True)

    future['our_price'] = future['our_price'].ffill().bfill()
    future['comp_price'] = future['comp_price'].ffill().bfill()
    future['market_index'] = future['market_index'].ffill().bfill()
    future['price_difference'] = future['price_difference'].ffill().bfill()

    forecast = model.predict(future)

    return forecast, model, daily_data

if __name__ == "__main__":
    print("running local test for forecast_engine.py...")

    TEST_DATA_PATH = "results.csv" 

    if not os.path.exists(TEST_DATA_PATH):
        print(f"❌ Test Aborted: Cannot find '{TEST_DATA_PATH}'.")
        print("   Please make sure the file is in this folder, or update TEST_DATA_PATH.")
    else:
        try:
            forecast, model, historical_daily = generate_forecast(TEST_DATA_PATH, forecast_periods=365)
            
            if forecast is not None:
                print("\n✅ SUCCESS! Prophet Model trained and forecast generated.")
                print(f"Historical data covered: {historical_daily['ds'].min()} to {historical_daily['ds'].max()}")
    
                future_df = forecast[forecast['ds'] > historical_daily['ds'].max()]
                print(f"Future forecast generated for: {len(future_df)} days out.")
                
                print("\n📋 Sample of Next Week's Predicted Order Volumes:")
                print(future_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].head(7).to_string(index=False))
            
                #print("\n📊 Displaying diagnostic plot...")
                #fig = model.plot(forecast)
                #import matplotlib.pyplot as plt
                #plt.show()

                output_folder = "forecast_csv"
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
  
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = os.path.join(output_folder, f"demand_forecast_{timestamp_str}.csv")

                export_cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
                forecast_subset = forecast[export_cols].copy()

                history_subset = historical_daily[['ds', 'y']].rename(columns={'y': 'actual_volume'})
                complete_export_df = pd.merge(forecast_subset, history_subset, on='ds', how='left')

                final_column_order = ['ds', 'actual_volume', 'yhat', 'yhat_lower', 'yhat_upper']
                complete_export_df = complete_export_df[final_column_order]

                complete_export_df.to_csv(csv_filename, index=False)
                print(f"Forecast csv exported to: {csv_filename}")

                fig, ax = plt.subplots(figsize=(12, 6))
 
                max_hist_date = historical_daily['ds'].max()
                historical_pred = forecast[forecast['ds'] <= max_hist_date]
                future_pred = forecast[forecast['ds'] > max_hist_date]

                ax.fill_between(
                    future_pred['ds'], 
                    future_pred['yhat_lower'], 
                    future_pred['yhat_upper'], 
                    color='#89cff0', 
                    alpha=0.3, 
                    label='Confidence Margin (80%)'
                )

                ax.scatter(
                    historical_daily['ds'],
                    historical_daily['y'],
                    color='#3EB489',
                    s=8, 
                    alpha=0.6, 
                    label='Observed History (Order Creation Date)'
                )

                ax.bar(
                    historical_pred['ds'], 
                    historical_pred['yhat'], 
                    color='#29AB87',
                    width=1.5,
                    label='Fitted History (Model Prediction)'
                )

                ax.bar(
                    future_pred['ds'], 
                    future_pred['yhat'], 
                    color='#318CE7',
                    width=1.5,
                    label='Predicted Future Demand'
                )

                ax.set_title("Supply Chain Demand Forecast", fontsize=14, fontweight='bold', pad=15)
                ax.set_xlabel("Timeline Calendar Date", fontsize=11, labelpad=10)
                ax.set_ylabel("Daily Order Volumes (Counts)", fontsize=11, labelpad=10)
                
                ax.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='lightgrey', fontsize=9)
                ax.grid(True, linestyle='--', alpha=0.5, color='lightgrey')

                plt.gcf().autofmt_xdate()

                plt.tight_layout()
                plt.show()

        except Exception as e:
            print(f"❌ An error occurred during the test run: {e}")