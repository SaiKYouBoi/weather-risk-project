# Morocco Weather Risk Pipeline

A end-to-end data engineering project that collects daily weather forecasts for Moroccan cities, scores their operational risk for last-mile delivery, and stores the results in PostgreSQL — ready for dashboarding and scheduling.

---

## Architecture

```
Open-Meteo API
      │
      ▼
[extraction]  extract_weather.py
      │  → data/bronze/weather_raw.json
      ▼
[transformation]  clean_silver.py
      │  → data/silver/weather_clean.parquet
      ▼
[load]  load_to_postgres.py
      │  → PostgreSQL (cities + weather_daily)
      ▼
[dashboard]  dashboard/app.py
      │  → Streamlit on localhost:8501
      ▼
[orchestration]  dags/
         → Airflow DAG (daily schedule)
```

---

## Cities Covered

Moroccan cities across all major regions:

| City | Region |
|---|---|
| Casablanca | Grand Casablanca-Settat |
| Rabat | Rabat-Salé-Kénitra |
| Marrakech | Marrakech-Safi |
| Fes | Fès-Meknès |
| Tangier | Tanger-Tétouan-Al Hoceïma |
| Agadir | Souss-Massa |
| Meknes | Fès-Meknès |
| Oujda | Oriental |
| Kenitra | Rabat-Salé-Kénitra |
| Tetouan | Tanger-Tétouan-Al Hoceïma |
| Safi | Marrakech-Safi |
| El Jadida | Grand Casablanca-Settat |
| Beni Mellal | Béni Mellal-Khénifra |
| Nador | Oriental |
| Khouribga | Béni Mellal-Khénifra |
| Taza | Fès-Meknès |
| Settat | Grand Casablanca-Settat |
| Larache | Tanger-Tétouan-Al Hoceïma |
| Guelmim | Guelmim-Oued Noun |
| Dakhla | Dakhla-Oued Ed-Dahab |

---

## Risk Score Formula

```python
risk_score = (
    score_precip      * 0.30 +   
    score_wind        * 0.30 +   
    score_precip_prob * 0.25 +   
    score_temp        * 0.15    
)
```

Weights sum to **1.0**, guaranteeing `risk_score ∈ [0, 100]`.

| Variable | Weight | Reason |
|---|---|---|
| `precip_sum` | 30% | Rainfall directly stops deliveries |
| `wind_gusts` | 30% | Gusts tip motorbikes and vans |
| `precip_prob` | 25% | Forward-looking planning signal |
| `temp_max` | 15% | Degrades drivers, rarely halts operations in Morocco |

**Risk labels:**

| Score | Label |
|---|---|
| 0 – 25 | `low` |
| 25 – 50 | `moderate` |
| 50 – 75 | `high` |
| 75 – 100 | `critical` |

---

## 🗄️ Database Schema

```
cities
  └── city_id (PK)
  └── city, lat, lng, population, region

weather_daily
  └── id (PK)
  └── city_id (FK → cities)
  └── forecast_date, retrieved_at
  └── temp_max, temp_min, precip_sum, precip_prob
  └── wind_speed, wind_gusts, weather_code
  └── temp_category, precip_category, wind_category
  └── risk_score, risk_label
  └── UNIQUE (city_id, forecast_date, retrieved_at)
```

---

## Quick Start

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd weather-risk
pip install -r requirements.txt
pip install streamlit
```

### 2. Configure environment

Copy `.env.example` and fill in your values:

```bash
cp .env.example .env.local
```

### 3. Start PostgreSQL

```bash
docker compose up -d postgres
```

### 4. Create tables

```bash
docker exec -i postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < sql/schema.sql
```

### 5. Run the pipeline

```bash
# Extract (Bronze)
python extraction/extract_weather.py

# Transform (Silver)
python transformation/clean_silver.py

# Load (Gold → PostgreSQL)
cd load && python load_to_postgres.py
```

### 6. Launch the dashboard

```bash
streamlit run dashboard/app.py
# → http://localhost:8501
```

---

## Analytical Queries

Five ready-to-run queries are in [`sql/queries.sql`](sql/queries.sql):

| Query | Question |
|---|---|
| Q1 | Which cities will experience the highest temperatures? |
| Q2 | Which cities will experience the most intense wind surges? |
| Q3 | Which cities have the highest average risk? |
| Q4 | Which periods present the greatest risk? |
| Q5 | For each city, which period presents the highest risk? |

Run all at once:

```bash
docker exec -i postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < sql/queries.sql
```

---

## Project Structure

```
weather-risk/
├── extraction/
│   ├── extract_weather.py   # Fetches 7-day forecasts from Open-Meteo API
│   └── ma.csv               # Moroccan cities with coordinates
├── transformation/
│   └── clean_silver.py      # Flatten, type-cast, quality checks → Parquet
├── load/
│   ├── load_to_postgres.py  # Compute risk score, upsert to PostgreSQL
│   └── config.py            # DB connection from .env
├── sql/
│   ├── schema.sql           # CREATE TABLE statements
│   └── queries.sql          # 5 analytical queries
├── diagram/
│   └── database             # Database Diagram
├── dashboard/
│   └── app.py               # Streamlit dashboard (5 charts)
├── dags/                    # Airflow DAGs
├── data/
│   ├── bronze/              # Raw JSON from API
│   └── silver/              # Cleaned Parquet
├── docker-compose.yml       # PostgreSQL + pgAdmin 
├── requirements.txt
└── .env.example
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| API Source | [Open-Meteo](https://open-meteo.com/) (free, no key needed) |
| Language | Python 3.10+ |
| Data processing | pandas, pyarrow |
| Database | PostgreSQL 17 (Docker) |
| ORM / connector | SQLAlchemy + psycopg2 |
| Dashboard | Streamlit |
| Orchestration | Apache Airflow (planned) |
| DB admin | pgAdmin 4 |
| Containerisation | Docker Compose |

---
