import pandas as pd
from sqlalchemy import text
from pathlib import Path
from src.db.connection import engine


def add_temp_category(df):

    df["temp_category"] = pd.cut(
        df["temp_max"],
        bins=[-float("inf"), 25, 35, 42, float("inf")],
        labels=["mild", "hot", "extreme_heat", "danger"],
    ).astype(str)
    return df


def add_precip_category(df):
    df["precip_category"] = pd.cut(
        df["precip_sum"],
        bins=[-1, 0, 5, 20, float("inf")],
        labels=["none", "light", "heavy", "extreme"],
    ).astype(str)
    return df


def add_wind_category(df):
    df["wind_category"] = pd.cut(
        df["wind_gusts"],
        bins=[-1, 30, 60, 80, float("inf")],
        labels=["calm", "windy", "strong", "storm"],
    ).astype(str)
    return df


def compute_risk_score(df):

    df["score_precip"] = (df["precip_sum"] / 20 * 100).clip(0, 100)

    df["score_precip_prob"] = df["precip_prob"].clip(0, 100)

    df["score_wind"] = (df["wind_gusts"] / 80 * 100).clip(0, 100)

    df["score_temp"] = ((df["temp_max"] - 35) / (42 - 35) * 100).clip(0, 100)

    df["risk_score"] = (
        df["score_precip"] * 0.30
        + df["score_precip_prob"] * 0.25
        + df["score_wind"] * 0.30
        + df["score_temp"] * 0.15
    ).round(2)

    df["risk_label"] = pd.cut(
        df["risk_score"],
        bins=[-1, 25, 50, 75, 100],
        labels=["low", "moderate", "high", "critical"],
    ).astype(str)

    return df


def upsert_cities(df, engine):
    cities = df[["city", "lat", "lng"]].drop_duplicates("city")
    with engine.connect() as conn:
        for _, row in cities.iterrows():
            conn.execute(
                text("""
                INSERT INTO cities (city, lat, lng)
                VALUES (:city, :lat, :lng)
                ON CONFLICT (city) DO NOTHING
            """),
                row.to_dict(),
            )


def upsert_forecasts(df, engine):
    with engine.connect() as conn:

        result = conn.execute(text("SELECT city_id, city FROM cities"))
        city_map = {row.city: row.city_id for row in result}

    df["city_id"] = df["city"].map(city_map)

    cols = [
        "city_id",
        "forecast_date",
        "retrieved_at",
        "temp_max",
        "temp_min",
        "precip_sum",
        "precip_prob",
        "wind_speed",
        "wind_gusts",
        "weather_code",
        "temp_category",
        "precip_category",
        "wind_category",
        "risk_score",
        "risk_label",
    ]

    with engine.connect() as conn:
        for _, row in df[cols].iterrows():
            conn.execute(
                text("""
                INSERT INTO weather_daily
                    (city_id, forecast_date, retrieved_at,
                     temp_max, temp_min, precip_sum, precip_prob,
                     wind_speed, wind_gusts, weather_code,
                     temp_category, precip_category, wind_category,
                     risk_score, risk_label)
                VALUES
                    (:city_id, :forecast_date, :retrieved_at,
                     :temp_max, :temp_min, :precip_sum, :precip_prob,
                     :wind_speed, :wind_gusts, :weather_code,
                     :temp_category, :precip_category, :wind_category,
                     :risk_score, :risk_label)
                ON CONFLICT (city_id, forecast_date, retrieved_at)
                DO UPDATE SET
                    risk_score = EXCLUDED.risk_score,
                    risk_label = EXCLUDED.risk_label,
                    temp_max   = EXCLUDED.temp_max,
                    wind_gusts = EXCLUDED.wind_gusts
            """),
                row.to_dict(),
            )


def run_gold(silver_path: Path):
    df = pd.read_parquet(silver_path)

    df = add_temp_category(df)
    df = add_precip_category(df)
    df = add_wind_category(df)

    df = compute_risk_score(df)

    upsert_cities(df, engine)
    upsert_forecasts(df, engine)

    print(f"{len(df)} rows loaded to PostgreSQL")


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    silver_file = base / "data" / "silver" / "weather_clean.parquet"
    run_gold(silver_file)
