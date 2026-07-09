-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    age INT,
    gender VARCHAR(10),
    device_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_users_device_type ON users(device_type);

-- ============================================================================
-- HEALTH_METRICS HYPERTABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS health_metrics (
    id BIGSERIAL,
    user_id INT NOT NULL REFERENCES users(user_id),
    metric_name VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    time TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (id, time)
);

-- Convert to hypertable with 1-day time chunks
SELECT create_hypertable(
    'health_metrics',
    'time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- ============================================================================
-- INDEXES for performance
-- ============================================================================
-- Most queries: SELECT ... WHERE user_id = X AND time > NOW() - INTERVAL
CREATE INDEX IF NOT EXISTS idx_health_metrics_user_time 
    ON health_metrics (user_id, time DESC);

-- Analytic queries: SELECT ... WHERE metric_name = X
CREATE INDEX IF NOT EXISTS idx_health_metrics_metric_time 
    ON health_metrics (metric_name, time DESC);

-- Device filtering
CREATE INDEX IF NOT EXISTS idx_health_metrics_metadata_quality
    ON health_metrics USING GIN (metadata);

-- ============================================================================
-- COMPRESSION POLICY
-- ============================================================================
-- Compress chunks older than 7 days (background job)
-- SELECT add_compression_policy(
--    'health_metrics',
--    INTERVAL '7 days',
--   if_not_exists => TRUE
--);

-- ============================================================================
-- RETENTION POLICY
-- ============================================================================
-- Keep data for 90 days (optional; remove if you want unlimited retention)
SELECT add_retention_policy(
    'health_metrics',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- ============================================================================
-- MATERIALIZED VIEW for quick stats
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_user_stats AS
SELECT
    user_id,
    time_bucket('1 day', time) AS day,
    metric_name,
    COUNT(*) AS sample_count,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    STDDEV(value) AS stddev_value
FROM health_metrics
GROUP BY user_id, time_bucket('1 day', time), metric_name;

CREATE INDEX IF NOT EXISTS idx_daily_user_stats_user_day 
    ON daily_user_stats (user_id, day DESC);

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Check hypertable was created
-- SELECT * FROM timescaledb_information.hypertables;
