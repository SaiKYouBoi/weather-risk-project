import streamlit as st
import pandas as pd
from sqlalchemy import text
from src.db.connection import engine
from streamlit_autorefresh import st_autorefresh
import os


st.set_page_config(page_title="Weather Risk Dashboard", layout="wide")
st.title("Morocco Delivery Risk Dashboard")


refresh_minutes = 15
st_autorefresh(interval=refresh_minutes * 60 * 1000, key="autorefresh")
st.caption(f"⟳ Auto-refreshes every {refresh_minutes} minutes")

def query(sql, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


risk_colours = {
    "low":      "background-color: #d4edda; color: #155724", 
    "moderate": "background-color: #fff3cd; color: #856404",  
    "high":     "background-color: #ffe5b4; color: #7d4e00", 
    "critical": "background-color: #f8d7da; color: #721c24", 
}

def colour_risk(val):
    return risk_colours.get(val, "")

#
st.sidebar.header("Filters")


all_cities_df = query("SELECT city FROM cities ORDER BY city")
all_cities = ["All cities"] + all_cities_df["city"].tolist()

selected_city = st.sidebar.selectbox("City", all_cities)

date_bounds = query("SELECT MIN(forecast_date) AS min_d, MAX(forecast_date) AS max_d FROM weather_daily")
min_date = pd.to_datetime(date_bounds["min_d"].iloc[0]).date()
max_date = pd.to_datetime(date_bounds["max_d"].iloc[0]).date()

date_range = st.sidebar.date_input(
    "Date range",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0] if date_range else min_date


city_filter = "" if selected_city == "All cities" else f"AND c.city = '{selected_city}'"
date_filter = f"AND w.forecast_date BETWEEN '{start_date}' AND '{end_date}'"
base_join   = "FROM weather_daily w JOIN cities c ON c.city_id = w.city_id"
where       = f"WHERE 1=1 {city_filter} {date_filter}"


st.header("Peak Temperature by City")
df1 = query(f"""
    SELECT c.city, MAX(w.temp_max) AS peak_temp_c
    {base_join} {where}
    GROUP BY c.city ORDER BY peak_temp_c DESC
""")
st.bar_chart(df1.set_index("city"))

st.header("Peak Wind Gusts by City")
df2 = query(f"""
    SELECT c.city, MAX(w.wind_gusts) AS peak_gusts_kmh
    {base_join} {where}
    GROUP BY c.city ORDER BY peak_gusts_kmh DESC
""")
st.bar_chart(df2.set_index("city"))

st.header("Average Risk Score by City")
df3 = query(f"""
    SELECT c.city, ROUND(AVG(w.risk_score)::NUMERIC, 2) AS avg_risk_score
    {base_join} {where}
    GROUP BY c.city ORDER BY avg_risk_score DESC
""")
st.bar_chart(df3.set_index("city"))

st.header("Risk Score Over Time")
df4 = query(f"""
    SELECT w.forecast_date, ROUND(AVG(w.risk_score)::NUMERIC, 2) AS avg_risk_score
    {base_join} {where}
    GROUP BY w.forecast_date ORDER BY w.forecast_date
""")
df4["forecast_date"] = pd.to_datetime(df4["forecast_date"])
st.line_chart(df4.set_index("forecast_date"))

st.header("Worst Day Per City")
df5 = query(f"""
    SELECT DISTINCT ON (c.city)
        c.city, w.forecast_date, w.risk_score, w.risk_label
    {base_join} {where}
    ORDER BY c.city, w.risk_score DESC
""")

styled = df5.style.map(colour_risk, subset=["risk_label"])
st.dataframe(styled, use_container_width=True)