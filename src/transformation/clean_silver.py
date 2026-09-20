import json
from pathlib import Path
import pandas as pd


def flatten_bronze(bronze_path: Path):
    with open(bronze_path, "r") as f:
        records = json.load(f)

    rows = []
    for record in records:
        if record["error"] is not None:
            continue 

        city = record["city"]
        lat = record["lat"]
        lng = record["lng"]
        retrieved_at = record["fetched_at"][:10] 
        daily = record["api_response"]["daily"]

        for i, date in enumerate(daily["time"]):
            rows.append(
                {
                    "city": city,
                    "lat": lat,
                    "lng": lng,
                    "forecast_date": date,
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "precip_sum": daily["precipitation_sum"][i],
                    "precip_prob": daily["precipitation_probability_max"][i],
                    "wind_speed": daily["wind_speed_10m_max"][i],
                    "wind_gusts": daily["wind_gusts_10m_max"][i],
                    "weather_code": daily["weather_code"][i],
                    "retrieved_at": retrieved_at,
                }
            )

    return pd.DataFrame(rows)


def fix_types(df: pd.DataFrame):
    df["forecast_date"] = pd.to_datetime(df["forecast_date"]).dt.date
    df["retrieved_at"] = pd.to_datetime(df["retrieved_at"]).dt.date

    float_cols = [
        "lat",
        "lng",
        "temp_max",
        "temp_min",
        "precip_sum",
        "wind_speed",
        "wind_gusts",
    ]

    df[float_cols] = df[float_cols].astype(float)

    df["precip_prob"] = df["precip_prob"].astype(int)
    df["weather_code"] = df["weather_code"].astype(int)

    return df


def quality_checks(df: pd.DataFrame):
    before = len(df)
    df = df.dropna(subset=["temp_max", "temp_min", "wind_gusts"])
    print(f"dropped {before - len(df)} null rows")

    df = df[df["temp_max"].between(-10, 55)]
    df = df[df["temp_min"].between(-10, 55)]
    df = df[df["precip_sum"] >= 0]
    df = df[df["wind_speed"] >= 0]
    df = df[df["precip_prob"].between(0, 100)]

    return df


def deduplicate(df: pd.DataFrame):
    df = df.drop_duplicates(subset=["city", "forecast_date", "retrieved_at"])
    return df


def run_silver(bronze_path: Path, silver_dir: Path):
    silver_dir.mkdir(parents=True, exist_ok=True)

    df = flatten_bronze(bronze_path)
    df = fix_types(df)
    df = quality_checks(df)
    df = deduplicate(df)

    out_path = silver_dir / f"weather_clean.parquet"
    df.to_parquet(out_path, index=False)
    print(f"{len(df)} rows written to {out_path}")
    return str(out_path)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    json_path = base / "data" / "bronze" / "weather_raw.json"
    silver_dir = base / "data" / "silver"
    
    run_silver(json_path, silver_dir)
