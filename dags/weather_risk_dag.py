from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from pathlib import Path

from src.extraction.extract_weather import run_extraction
from src.transformation.clean_silver import run_silver
from src.load.load_to_postgres import run_gold

base   = Path("/opt/project")
bronze = base / "data/bronze/weather_raw.json"
silver = base / "data/silver"


default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="weather_risk_pipeline",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["weather", "morocco", "risk"],
) as dag:

    extract = PythonOperator(
        task_id="extract_weather",
        python_callable=run_extraction,
    )

    transform = PythonOperator(
        task_id="clean_silver",
        python_callable=run_silver,
        op_kwargs={
            "bronze_path": bronze,
            "silver_dir": silver,
        },
    )

    load = PythonOperator(
        task_id="load_to_postgres",
        python_callable=run_gold,
        op_kwargs={
            "silver_path": silver / "weather_clean.parquet",
        },
    )

    extract >> transform >> load
