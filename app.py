# app.py

import streamlit as st
from datetime import date, timedelta
from core.data_loader import load_from_rms_database, load_from_files
from core.predictor import generate_predictions

# --- Page Configuration ---
st.set_page_config(
    page_title="Daily Prep Assistant",
    page_icon="🍳",
    layout="wide"
)

st.title("Daily Prep Assistant 🍳")
st.markdown("A predictive tool to forecast menu item demand for a given day and time.")

# --- Mode Selection ---
st.sidebar.title("Configuration")
app_mode = st.sidebar.selectbox("Choose App Mode", ["Integrated (Simulated)", "Standalone"])

base_df = None
location = None

# --- Data Loading UI ---
with st.sidebar.expander("Data Source", expanded=True):
    if app_mode == "Integrated (Simulated)":
        st.info("✅ Connected to RMS. Data loaded automatically.")
        base_df, location = load_from_rms_database()
    else: # Standalone Mode
        uploaded_file = st.file_uploader("Upload Order History (CSV)", type=['csv'])
        location_input = st.text_input("Enter Restaurant Location (e.g., 'New York')")
        if uploaded_file and location_input:
            base_df, location = load_from_files(uploaded_file, location_input)

# --- Prediction Inputs UI ---
if base_df is not None and location:
    st.sidebar.title("Prediction Inputs")
    
    selected_date = st.sidebar.date_input("Select Date", min_value=date.today(), max_value=date.today() + timedelta(days=13))
    
    # Use hours from the loaded data for consistency
    hours = sorted(base_df['hour'].unique())
    selected_hour = st.sidebar.selectbox("Select Hour (24h)", hours)
    
    is_special_event = st.sidebar.checkbox("Is there a special local event?")
    
    predict_button = st.sidebar.button("Generate Forecast", type="primary", use_container_width=True)

    # --- Prediction and Display Logic ---
    if predict_button:
        with st.spinner("Forecasting..."):
            # Convert date to string for the predictor function
            date_str = selected_date.strftime('%Y-%m-%d')
            
            # Call the core prediction function
            results = generate_predictions(base_df, location, date_str, selected_hour, is_special_event)
            
            if "error" in results:
                st.error(results["error"])
            else:
                st.subheader(f"Forecast for {selected_date.strftime('%A, %b %d, %Y')} at {selected_hour}:00")
                
                # Display Weather
                with st.expander("Weather Conditions", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Temperature", f"{results['weather']['temp_c']} °C")
                    col2.metric("Precipitation", f"{results['weather']['precip_mm']} mm")
                    col3.metric("Wind Speed", f"{results['weather']['wind_kph']} kph")
                    col4.metric("Cloud Cover", f"{results['weather']['cloud']}%")

                # Display Predictions
                tab1, tab2 = st.tabs(["📈 Overall Prediction", "📊 Dine-In vs. Take-Away"])
                
                with tab1:
                    st.dataframe(results['overall_prediction'], use_container_width=True,
                                 column_config={"probability": st.column_config.ProgressColumn("Probability", format="%.2f")})
                
                with tab2:
                    st.dataframe(results['detailed_prediction'], use_container_width=True,
                                 column_config={
                                     "Dine In": st.column_config.ProgressColumn("Dine In", format="%.2f"),
                                     "Take Away": st.column_config.ProgressColumn("Take Away", format="%.2f")
                                 })
else:
    st.sidebar.warning("Please configure the data source to proceed.")
