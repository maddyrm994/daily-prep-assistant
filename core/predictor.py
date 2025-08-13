# core/predictor.py

import pandas as pd
import joblib
import requests
import holidays
import os
from datetime import datetime, timedelta
from config import MODEL_PATH, COLUMNS_PATH, API_KEY_PATH, HOLIDAY_COUNTRY, HOLIDAY_PROVINCE

# --- Load Artifacts on Startup ---
try:
    model = joblib.load(MODEL_PATH)
    model_columns = joblib.load(COLUMNS_PATH)
    with open(API_KEY_PATH, 'r') as f:
        api_key = f.read().strip()
    holiday_calendar = holidays.CountryHoliday(HOLIDAY_COUNTRY, prov=None, state=HOLIDAY_PROVINCE)
except FileNotFoundError as e:
    raise RuntimeError(f"Could not initialize predictor: {e}. Make sure all required files are present in their correct folders.")

# --- Helper Function for Weather ---
def get_hourly_weather_forecast(location, target_date, target_hour):
    """Fetches weather forecast for a specific date and hour."""
    base_url = "http://api.weatherapi.com/v1/forecast.json"
    days = (target_date - datetime.today().date()).days + 1
    if not (0 < days <= 14):
        return {"error": "Date must be within the next 14 days."}

    params = {'key': api_key, 'q': location, 'days': days}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        hourly_data = response.json()['forecast']['forecastday'][-1]['hour']
        return hourly_data[target_hour]
    except Exception as e:
        return {"error": f"API or data parsing error: {e}"}

# --- Rolling Average Prediction Function ---
def rolling_average_prediction(base_df, target_date, target_hour, window_days=3):
    """
    Predicts average order count per food item for the given hour over the recent window_days.
    """
    df = base_df.copy()
    # Ensure order_date is datetime.date
    df['order_date'] = pd.to_datetime(df['date']).dt.date
    start_date = target_date - timedelta(days=window_days)
    recent_df = df[df['order_date'] >= start_date]

    # Count orders per food item per hour
    mask = recent_df['hour'] == target_hour
    grouped = (
        recent_df[mask]
        .groupby(['food_item_name'])
        .size()
        .reset_index(name='rolling_avg_orders')
        .sort_values('rolling_avg_orders', ascending=False)
    )
    return grouped

# --- Main Prediction Function ---
def generate_predictions(base_df, location, target_date_str, target_hour, is_special_event, rolling_window_days=3):
    """Generates order predictions. This function is now pure and depends only on its inputs."""
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        return {"error": "Invalid date format. Please use YYYY-MM-DD."}

    weather_data = get_hourly_weather_forecast(location, target_date, target_hour)
    if "error" in weather_data:
        return weather_data

    unique_items = base_df[['food_item_name', 'food_item_category']].drop_duplicates()
    day_of_week = target_date.strftime('%A')
    day_type = 'Weekend' if day_of_week in ['Saturday', 'Sunday'] else 'Weekday'
    is_holiday = target_date in holiday_calendar

    scenarios = []
    for _, row in unique_items.iterrows():
        base_scenario = {
            'hour': target_hour, 'food_item_name': row['food_item_name'], 'food_item_category': row['food_item_category'],
            'day_of_the_week': day_of_week, 'day_type': day_type, 'temperature_c': weather_data['temp_c'],
            'wind_kph': weather_data['wind_kph'], 'precipitation_mm': weather_data['precip_mm'],
            'cloud': weather_data['cloud'], 'humidity': weather_data['humidity'], 'pressure_mb': weather_data['pressure_mb'],
            'is_holiday': is_holiday, 'is_special_event': is_special_event,
        }
        scenarios.append({**base_scenario, 'order_type': 'Dine In'})
        scenarios.append({**base_scenario, 'order_type': 'Take Away'})

    future_df = pd.DataFrame(scenarios)
    future_encoded = pd.get_dummies(future_df, columns=['food_item_name', 'food_item_category', 'day_of_the_week', 'day_type', 'order_type'])
    future_aligned = future_encoded.reindex(columns=model_columns, fill_value=0)
    
    predictions_proba = model.predict_proba(future_aligned)[:, 1]
    future_df['probability'] = predictions_proba

    overall = future_df.groupby('food_item_name')['probability'].mean().reset_index().sort_values('probability', ascending=False)
    detailed = future_df.pivot(index='food_item_name', columns='order_type', values='probability').reset_index().fillna(0)
    detailed = detailed.sort_values(by=['Dine In', 'Take Away'], ascending=False)

    # --- Rolling average prediction ---
    rolling_avg = rolling_average_prediction(base_df, target_date, target_hour, window_days=rolling_window_days)

    return {
        "weather": weather_data,
        "overall_prediction": overall,
        "detailed_prediction": detailed,
        "rolling_avg_prediction": rolling_avg,
        "rolling_window_days": rolling_window_days,
    }
