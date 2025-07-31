# core/data_loader.py

import pandas as pd
import streamlit as st
from config import RMS_DATA_PATH, DEFAULT_LOCATION

# --- Integrated Mode ---
@st.cache_data
def load_from_rms_database():
    """
    Simulates loading data from an RMS database.
    In a real scenario, this would contain database connection logic (e.g., SQL queries).
    For this demo, we read from a predefined CSV.
    """
    try:
        df = pd.read_csv(RMS_DATA_PATH)
        # In a real app, you might fetch location from an RMS 'restaurants' table
        location = DEFAULT_LOCATION
        return df, location

#####-----##### MODIFICATION FOR REAL INTEGRATION #####-----#####

        # The real integration code
        #import sqlalchemy
        #import pandas as pd

        # Get database connection details from the RMS config
        #db_connection_str = 'mysql+pymysql://user:password@host/rms_db'
        #db_engine = sqlalchemy.create_engine(db_connection_str)

        # Fetch order history and location with SQL queries
        #order_history_df = pd.read_sql("SELECT * FROM orders", db_engine)
        #location_df = pd.read_sql("SELECT city FROM restaurants WHERE id = 1", db_engine)
        #location = location_df['city'].iloc[0]

        #return order_history_df, location

#####-----##### #####-----##### #####-----##### #####-----#####

    except FileNotFoundError:
        st.error(f"Integrated mode error: Could not find the RMS data file at '{RMS_DATA_PATH}'.")
        return None, None

# --- Standalone Mode ---
def load_from_files(uploaded_file, location_input):
    """
    Loads data from user-uploaded files and inputs for standalone mode.
    """
    if uploaded_file is None:
        st.warning("Please upload your order history CSV file.")
        return None, None
    if not location_input:
        st.warning("Please enter the restaurant location.")
        return None, None
        
    try:
        df = pd.read_csv(uploaded_file)
        # Validate that the uploaded file has the necessary columns
        required_cols = ['food_item_name', 'food_item_category', 'hour']
        if not all(col in df.columns for col in required_cols):
            st.error(f"Uploaded CSV is missing one or more required columns: {required_cols}")
            return None, None
            
        return df, location_input
    except Exception as e:
        st.error(f"Error processing uploaded file: {e}")
        return None, None
