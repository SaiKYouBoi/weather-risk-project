import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DB_URL)

st.set_page_config(page_title="Weather Risk Dashboard", layout="wide")
st.title("Morocco Delivery Risk Dashboard")

def query(sql):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


st.header("Peak Temperature by City")
df1 = query("""
    SELECT c.city, MAX(w.temp_max) AS peak_temp_c
    FROM weather_daily w JOIN cities c ON c.city_id = w.city_id
    GROUP BY c.city ORDER BY peak_temp_c DESC
""")
st.bar_chart(df1.set_index("city"))
