CREATE DATABASE IF NOT EXISTS prosthetics_analytics;

CREATE TABLE IF NOT EXISTS prosthetics_analytics.dim_users_orders
(
    user_id UInt32,
    full_name String,
    birth_date Date,
    city String,
    prosthesis_serial String,
    model_name String,
    model_price Decimal(10, 2),
    order_date DateTime,
    status Enum8('DONE' = 1, 'ORDER_ACCEPTED' = 2, 'MANUFACTURING' = 3, 'READY_FOR_TRYING_ON' = 4),
    delivered_at Nullable(DateTime),
    age_at_order UInt8 MATERIALIZED toYear(order_date) - toYear(birth_date),
    _loaded_at DateTime DEFAULT now()
    )
    ENGINE = ReplacingMergeTree(_loaded_at)
    PARTITION BY toYYYYMM(order_date)
    ORDER BY (user_id, prosthesis_serial, order_date);

CREATE TABLE IF NOT EXISTS prosthetics_analytics.fact_telemetry (
                                                                    serial_number String,
                                                                    recorded_at DateTime,
                                                                    emg_value Float32,
                                                                    emg_muscle_group LowCardinality(String),
    esp32_temperature Float32,
    esp32_uptime_seconds UInt32,
    esp32_signal_strength Int16,
    battery_level UInt8,
    battery_voltage Float32,
    battery_current Float32,
    step_count UInt32,
    gait_phase LowCardinality(String),
    firmware_version LowCardinality(String),
    _loaded_at DateTime DEFAULT now()
    )
    ENGINE = MergeTree()
    PARTITION BY toYYYYMM(recorded_at)
    ORDER BY (serial_number, recorded_at)
    TTL recorded_at + INTERVAL 2 YEAR;

CREATE MATERIALIZED VIEW prosthetics_analytics.mv_user_daily_stats
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, date)
AS
SELECT
    up.user_id AS user_id,
    toDate(pt.recorded_at) AS date,
    anyLast(u.full_name) AS full_name,
    anyLast(u.city) AS city,
    anyLast(pm.model_name) AS model_name,
    anyLast(up.status) AS status,
    max(pt.recorded_at) AS last_recorded_at,
    sum(pt.step_count) AS total_steps,
    avg(pt.emg_value) AS avg_emg,
    avg(pt.battery_level) AS avg_battery_level,
    min(pt.battery_level) AS min_battery_level,
    argMax(pt.firmware_version, pt.recorded_at) AS latest_firmware,
    now() AS _loaded_at
FROM prosthetics_analytics.fact_telemetry pt
    JOIN prosthetics_analytics.dim_users_orders up
ON pt.serial_number = up.prosthesis_serial
    JOIN prosthetics_analytics.dim_users_orders u
    ON up.user_id = u.user_id
    JOIN prosthetics_analytics.dim_users_orders pm
    ON up.prosthesis_serial = pm.prosthesis_serial
GROUP BY
    user_id,
    date;