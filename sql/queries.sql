-- Q1. Which cities will experience the highest temperatures?

SELECT
    c.city,
    MAX(w.temp_max) AS peak_temp_c
FROM weather_daily w
JOIN cities c ON c.city_id = w.city_id
GROUP BY c.city
ORDER BY peak_temp_c DESC;


-- Which cities will experience the most intense wind surges?

SELECT
    c.city,
    MAX(w.wind_gusts) AS peak_gusts_kmh
FROM weather_daily w
JOIN cities c ON c.city_id = w.city_id
GROUP BY c.city
ORDER BY peak_gusts_kmh DESC;

-- Which cities have the highest average risk?

SELECT
    c.city,
    ROUND(AVG(w.risk_score)::NUMERIC, 2) AS avg_risk_score
FROM weather_daily w
JOIN cities c ON c.city_id = w.city_id
GROUP BY c.city
ORDER BY avg_risk_score DESC;

-- Which periods present the greatest risk?

SELECT
    w.forecast_date,
    ROUND(AVG(w.risk_score)::NUMERIC, 2) AS avg_risk_score
FROM weather_daily w
GROUP BY w.forecast_date
ORDER BY avg_risk_score DESC;

-- For each city, which period presents the highest risk?

SELECT DISTINCT ON (c.city)
    c.city,
    w.forecast_date,
    w.risk_score,
    w.risk_label
FROM weather_daily w
JOIN cities c ON c.city_id = w.city_id
ORDER BY c.city, w.risk_score DESC;