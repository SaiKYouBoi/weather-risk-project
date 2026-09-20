CREATE TABLE IF NOT EXISTS cities (
    city_id     SERIAL PRIMARY KEY,
    city        VARCHAR(100) UNIQUE NOT NULL,
    lat         FLOAT NOT NULL,
    lng         FLOAT NOT NULL,
    population  INTEGER,
    region      VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS weather_daily (
    id                  SERIAL PRIMARY KEY,
    city_id             INTEGER REFERENCES cities(city_id),
    forecast_date       DATE NOT NULL,
    retrieved_at        DATE NOT NULL,

    
    temp_max            FLOAT,
    temp_min            FLOAT,
    precip_sum          FLOAT,
    precip_prob         INTEGER,
    wind_speed          FLOAT,
    wind_gusts          FLOAT,
    weather_code        INTEGER,

    
    temp_category       VARCHAR(20),
    precip_category     VARCHAR(20),
    wind_category       VARCHAR(20),

    
    risk_score          FLOAT,
    risk_label          VARCHAR(20),

    
    UNIQUE (city_id, forecast_date, retrieved_at)
);