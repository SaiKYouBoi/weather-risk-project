# Morocco Weather Risk — Full Project Flow

## Big Picture

```
Open-Meteo API (free, no key)
        │
        │  HTTP GET  (7-day forecast per city)
        ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXTRACT                                 │
│   src/extraction/extract_weather.py                         │
│   Reads: extraction/ma.csv (20 Moroccan cities)             │
│   Writes: data/bronze/weather_raw.json                      │
└─────────────────────────────────────────────────────────────┘
        │
        │  raw JSON (one record per city, 7 days each)
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    TRANSFORM                                 │
│   src/transformation/clean_silver.py                        │
│   Reads: data/bronze/weather_raw.json                       │
│   Writes: data/silver/weather_clean.parquet                 │
└─────────────────────────────────────────────────────────────┘
        │
        │  clean Parquet (typed, validated, deduplicated)
        ▼
┌─────────────────────────────────────────────────────────────┐
│                      LOAD                                    │
│   src/load/load_to_postgres.py                              │
│   Reads: data/silver/weather_clean.parquet                  │
│   Writes: PostgreSQL → cities + weather_daily tables        │
└─────────────────────────────────────────────────────────────┘
        │
        │  SQL (upsert, idempotent)
        ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL                                 │
│   Container: postgres   Port: 5433                          │
│   DB: weather_risk                                          │
│   Tables: cities, weather_daily                             │
└─────────────────────────────────────────────────────────────┘
        │
        ├──────────────────────────┐
        ▼                          ▼
┌──────────────┐         ┌─────────────────┐
│  Streamlit   │         │    pgAdmin       │
│  dashboard   │         │  (DB browser)    │
│  Port: 8501  │         │  Port: 5050      │
└──────────────┘         └─────────────────┘
```

---

## Orchestration Layer (Airflow)

```
Every day at midnight (@daily)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Airflow DAG: weather_risk_pipeline                         │
│  Container: airflow   Port: 8080                            │
│  Metadata DB: airflow-postgres   Port: 5434                 │
│                                                             │
│  Task 1: extract_weather  → runs extract_weather.py         │
│       ↓                                                     │
│  Task 2: clean_silver     → runs clean_silver.py            │
│       ↓                                                     │
│  Task 3: load_to_postgres → runs load_to_postgres.py        │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Step-by-Step

### Step 1 — Extract (Bronze layer)

**File:** [`src/extraction/extract_weather.py`](file:///home/saikyouboi/Documents/AI-BRIEFS/weather-risk/src/extraction/extract_weather.py)  
**Cities:** [`src/extraction/ma.csv`](file:///home/saikyouboi/Documents/AI-BRIEFS/weather-risk/src/extraction/ma.csv) — 20 Moroccan cities with lat/lng

**What it does:**
1. Reads the 20 cities from `ma.csv`
2. For each city, calls the Open-Meteo API with 7 variables:
   - `temperature_2m_max` / `temperature_2m_min`
   - `precipitation_sum`
   - `precipitation_probability_max`
   - `wind_speed_10m_max`
   - `wind_gusts_10m_max`
   - `weather_code`
3. Retries up to 3 times on timeout/connection errors
4. Dumps all 20 city records into a single JSON file

**Output:** `data/bronze/weather_raw.json`
```json
[
  {
    "city": "Casablanca",
    "lat": 33.5992,
    "lng": -7.62,
    "fetched_at": "2026-09-20T12:00:00Z",
    "api_response": { "daily": { "time": [...], "temperature_2m_max": [...] } },
    "error": null
  },
  ...
]
```

---

### Step 2 — Transform (Silver layer)

**File:** [`src/transformation/clean_silver.py`](file:///home/saikyouboi/Documents/AI-BRIEFS/weather-risk/src/transformation/clean_silver.py)

**What it does:**
1. **Flatten** — explodes the nested JSON into one row per city per day (20 cities × 7 days = 140 rows)
2. **Type casting** — dates to `date`, floats to `float`, `precip_prob` to `int`
3. **Quality checks** — drops nulls, filters impossible values (e.g. temp > 55°C)
4. **Deduplicate** — removes duplicate (city, forecast_date, retrieved_at) combos

**Output:** `data/silver/weather_clean.parquet` — 140 clean rows, typed columns

---

### Step 3 — Load (Gold layer)

**File:** [`src/load/load_to_postgres.py`](file:///home/saikyouboi/Documents/AI-BRIEFS/weather-risk/src/load/load_to_postgres.py)

**What it does:**
1. **Categorise** each weather variable into a human-readable label:
   - `temp_category`: mild / hot / extreme_heat / danger
   - `precip_category`: none / light / heavy / extreme
   - `wind_category`: calm / windy / strong / storm

2. **Compute the risk score** (weighted sum, guaranteed 0–100):

```
risk_score = (precip_sum_score  × 0.30)
           + (wind_gusts_score  × 0.30)
           + (precip_prob_score × 0.25)
           + (temp_max_score    × 0.15)
```

3. **Assign a risk label**:
   - 0–25 → `low`
   - 25–50 → `moderate`
   - 50–75 → `high`
   - 75–100 → `critical`

4. **Upsert into PostgreSQL** — `ON CONFLICT DO UPDATE` means re-running is safe, no duplicates

---

### Database Schema

**Table: `cities`**
```
city_id  │ city        │ lat     │ lng     │ population │ region
─────────┼─────────────┼─────────┼─────────┼────────────┼──────────────────
1        │ Casablanca  │ 33.5992 │ -7.62   │ 3752000    │ Grand Casablanca
...
```

**Table: `weather_daily`**
```
city_id │ forecast_date │ temp_max │ precip_sum │ wind_gusts │ risk_score │ risk_label
────────┼───────────────┼──────────┼────────────┼────────────┼────────────┼───────────
1       │ 2026-09-20    │ 34.1     │ 0.0        │ 28.5       │ 12.30      │ low
...
```

---

### Step 4 — Dashboard

**File:** [`dashboard/app.py`](file:///home/saikyouboi/Documents/AI-BRIEFS/weather-risk/dashboard/app.py)  
**URL:** `http://localhost:8501`

Queries PostgreSQL live and renders 5 views:

| Chart                      | Query                                         | Type               |
| -------------------------- | --------------------------------------------- | ------------------ |
| 🌡️ Peak Temperature by City | `MAX(temp_max) GROUP BY city`                 | Bar chart          |
| 💨 Peak Wind Gusts by City  | `MAX(wind_gusts) GROUP BY city`               | Bar chart          |
| ⚠️ Average Risk Score       | `AVG(risk_score) GROUP BY city`               | Bar chart          |
| 📅 Risk Over Time           | `AVG(risk_score) GROUP BY forecast_date`      | Line chart         |
| 🔴 Worst Day Per City       | `DISTINCT ON (city) ORDER BY risk_score DESC` | Colour-coded table |

**Sidebar filters:** city dropdown + date range — all 5 charts update together.  
**Auto-refresh:** every 15 minutes — picks up new data from the next DAG run automatically.

---

### Step 5 — Orchestration (Airflow)

**File:** [`dags/weather_risk_dag.py`](file:///home/saikyouboi/Documents/AI-BRIEFS/weather-risk/dags/weather_risk_dag.py)  
**UI:** `http://localhost:8080` — login: `admin / admin`

```
Schedule: @daily (midnight UTC)

Task graph:
extract_weather ──▶ clean_silver ──▶ load_to_postgres
     ✅                 ✅                  ✅
```

- `retries: 1` — if a task fails, Airflow retries once after 5 minutes
- `catchup=False` — won't try to backfill missed runs
- On success: fresh data is in PostgreSQL, dashboard auto-reflects it on next refresh

---

## Full Infrastructure Map

| Container          | Image                | Port | Role                                    |
| ------------------ | -------------------- | ---- | --------------------------------------- |
| `postgres`         | postgres:17-alpine   | 5433 | Weather data warehouse                  |
| `airflow-postgres` | postgres:17-alpine   | 5434 | Airflow metadata                        |
| `pgadmin`          | pgadmin4             | 5050 | DB browser UI                           |
| `weather-python`   | python:3.12-slim     | —    | Run pipeline manually via `docker exec` |
| `streamlit`        | python:3.12-slim     | 8501 | Live dashboard                          |
| `airflow`          | apache/airflow:2.9.3 | 8080 | Scheduler + webserver                   |

---

## Data Freshness

```
Day 0 (today):   Airflow triggers at midnight
                 → API called for all 20 cities
                 → 140 new rows upserted into weather_daily
                 → Dashboard refreshes automatically at 00:15

Day 1 (tomorrow): Same thing repeats
                  → forecast_dates shift forward by 1 day
                  → old rows updated, new future dates inserted
```

---

## File Structure

```
weather-risk/
│
├── src/                          ← all Python source code
│   ├── extraction/
│   │   ├── extract_weather.py    ← Step 1: fetch from Open-Meteo
│   │   └── ma.csv                ← 20 cities list
│   ├── transformation/
│   │   └── clean_silver.py       ← Step 2: flatten, validate, parquet
│   ├── load/
│   │   └── load_to_postgres.py   ← Step 3: score, categorise, upsert
│   └── db/
│       ├── config.py             ← DB URL from env vars
│       └── connection.py         ← SQLAlchemy engine
│
├── dags/
│   └── weather_risk_dag.py       ← Airflow DAG (wires all 3 steps)
│
├── dashboard/
│   └── app.py                    ← Streamlit (5 charts + filters)
│
├── sql/
│   ├── schema.sql                ← CREATE TABLE statements
│   └── queries.sql               ← 5 analytical queries
│
├── data/
│   ├── bronze/weather_raw.json   ← raw API output
│   └── silver/weather_clean.parquet ← cleaned data
│
├── diagram/
│   └── database.puml             ← PlantUML ERD
│
├── Dockerfile                    ← python + streamlit image
├── Dockerfile.airflow            ← airflow image + project deps
├── docker-compose.yml            ← all 6 services
├── requirements.txt              ← Python dependencies
├── .env                          ← credentials (gitignored)
└── .env.example                  ← template for new developers
```
