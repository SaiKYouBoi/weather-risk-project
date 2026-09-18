import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

base = Path(__file__).resolve().parent.parent
cities_csv = Path(__file__).resolve().parent / "ma.csv"
bronze_dir = base / "data" / "bronze"

meteo_url = "https://api.open-meteo.com/v1/forecast"
forecast_days = 7
time_out = 10

max_retries = 3
retry_backoff = [2, 4]


def call_api(params: dict):
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(meteo_url, params=params, timeout=time_out)
            response.raise_for_status()
            print(f"Response:{response}")
            return response.json()

        except (requests.Timeout, requests.ConnectionError) as e:
            last_exception = e
            if attempt < max_retries:
                wait = retry_backoff[attempt - 1]
                print(
                    f"[BRONZE] Attempt {attempt} failed ({type(e).__name__}). Retrying in {wait}s..."
                )
                time.sleep(wait)

    raise last_exception


def fetch_city_forecast(city_row: pd.Series):
    city_name = city_row["city"]
    lat = float(city_row["lat"])
    lng = float(city_row["lng"])
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
                "weather_code",
            ]
        ),
        "timezone": "Africa/Casablanca",
        "forecast_days": forecast_days,
    }

    record = {
        "city": city_name,
        "lat": lat,
        "lng": lng,
        "fetched_at": fetched_at,
        "api_response": None,
        "error": None,
    }

    try:
        data = call_api(params)
        print(f"data: {data}")
        if not data.get("daily") or not data["daily"].get("time"):
            record["error"] = "EMPTY_RESPONSE: daily.time missing from API payload"
            return record
        print(f"racord: {record}")
        record["api_response"] = data

    except requests.HTTPError as e:
        record["error"] = f"HTTP_ERROR: {e.response.status_code} — {e}"
    except requests.Timeout:
        record["error"] = f"TIMEOUT: no response within {time_out}s after retries"
    except requests.ConnectionError as e:
        record["error"] = f"CONNECTION_ERROR: {e}"
    except Exception as e:
        record["error"] = f"UNEXPECTED_ERROR: {type(e).__name__}: {e}"

    return record


def load_cities(csv_path):
    df = pd.read_csv(csv_path)

    required_cols = {"city", "lat", "lng"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"ma.csv is missing required columns: {missing}")

    if df.empty:
        raise ValueError("ma.csv has no rows — nothing to extract.")

    print(f"1.Loadingg the csv cities:{df}")
    return df


def run_extraction():

    cities_df = load_cities(cities_csv)

    # run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bronze_dir.mkdir(parents=True, exist_ok=True)
    out_path = bronze_dir / f"weather_raw.json"

    # if out_path.exists():
    #     print(f"file for {run_date} already exists at {out_path}. ")
    #     return out_path

    results = []
    total = len(cities_df)
    success_count = 0
    error_count = 0

    for idx, row in cities_df.iterrows():
        city_name = row["city"]
        # print(f"({idx + 1}/{total}) fetching: {city_name}")

        record = fetch_city_forecast(row)

        if record["error"]:
            print(f"{city_name}: {record['error']}")
            error_count += 1
        else:
            print(f"{city_name}: nioce")
            success_count += 1

        results.append(record)

        time.sleep(0.3)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(
        f"done. {success_count}/{total} succeeded, {error_count} failed. "
        f"Saved to: {out_path}"
    )

    return out_path


if __name__ == "__main__":
    run_extraction()
