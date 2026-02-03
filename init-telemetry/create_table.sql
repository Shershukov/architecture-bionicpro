CREATE TABLE prosthesis_telemetry (
                                                id BIGSERIAL PRIMARY KEY,
                                                serial_number VARCHAR(100) NOT NULL,
                                                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                                emg_value FLOAT NOT NULL CHECK (emg_value BETWEEN -100 AND 100),
                                                emg_muscle_group VARCHAR(50) NOT NULL,
                                                esp32_temperature FLOAT NOT NULL CHECK (esp32_temperature BETWEEN -40 AND 85),
                                                esp32_uptime_seconds INTEGER NOT NULL CHECK (esp32_uptime_seconds >= 0),
                                                esp32_signal_strength INTEGER CHECK (esp32_signal_strength BETWEEN -100 AND 0),
                                                battery_level INTEGER NOT NULL CHECK (battery_level BETWEEN 0 AND 100),
                                                battery_voltage FLOAT NOT NULL CHECK (battery_voltage BETWEEN 0 AND 5),
                                                battery_current FLOAT CHECK (battery_current BETWEEN -5 AND 5),
                                                step_count INTEGER DEFAULT 0 CHECK (step_count >= 0),
                                                gait_phase VARCHAR(20) CHECK (gait_phase IN ('stance', 'swing', 'toe_off')),
                                                firmware_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
                                                created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_serial ON prosthesis_telemetry(serial_number);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_recorded_at ON prosthesis_telemetry(recorded_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_serial_time
    ON prosthesis_telemetry(serial_number, recorded_at DESC);