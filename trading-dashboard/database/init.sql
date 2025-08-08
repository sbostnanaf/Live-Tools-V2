-- Trading Dashboard Database Initialization
-- This script sets up the initial database structure and data

-- Create database if not exists
-- (This is handled by Docker environment variables)

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
-- Additional indexes beyond what SQLAlchemy creates

-- Index for fast trade queries by date range
CREATE INDEX IF NOT EXISTS idx_trades_entry_time_desc ON trades(entry_time DESC);

-- Index for balance history queries
CREATE INDEX IF NOT EXISTS idx_balance_history_timestamp_desc ON balance_history(timestamp DESC);

-- Composite index for dashboard queries
CREATE INDEX IF NOT EXISTS idx_trades_account_symbol_time ON trades(account_id, symbol, entry_time);

-- Index for market data queries
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp_desc ON market_data(timestamp DESC);

-- Index for audit log queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp_desc ON audit_logs(timestamp DESC);

-- Create a view for trade statistics
CREATE OR REPLACE VIEW trade_statistics AS
SELECT 
    t.account_id,
    t.symbol,
    t.strategy,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN t.pnl_usd > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN t.pnl_usd < 0 THEN 1 END) as losing_trades,
    ROUND(
        (COUNT(CASE WHEN t.pnl_usd > 0 THEN 1 END) * 100.0 / COUNT(*))::numeric, 
        2
    ) as win_rate,
    ROUND(SUM(t.pnl_usd)::numeric, 2) as total_pnl,
    ROUND(AVG(t.pnl_usd)::numeric, 2) as avg_pnl,
    ROUND(AVG(CASE WHEN t.pnl_usd > 0 THEN t.pnl_usd END)::numeric, 2) as avg_win,
    ROUND(AVG(CASE WHEN t.pnl_usd < 0 THEN t.pnl_usd END)::numeric, 2) as avg_loss,
    MAX(t.pnl_usd) as best_trade,
    MIN(t.pnl_usd) as worst_trade
FROM trades t
WHERE t.status = 'closed'
GROUP BY t.account_id, t.symbol, t.strategy;

-- Create a view for daily P&L summary
CREATE OR REPLACE VIEW daily_pnl AS
SELECT 
    t.account_id,
    DATE(t.exit_time) as trade_date,
    COUNT(*) as trades_count,
    ROUND(SUM(t.pnl_usd)::numeric, 2) as daily_pnl,
    ROUND(SUM(t.fees_usd)::numeric, 2) as total_fees,
    STRING_AGG(DISTINCT t.symbol, ', ') as symbols_traded
FROM trades t
WHERE t.status = 'closed' 
    AND t.exit_time IS NOT NULL
GROUP BY t.account_id, DATE(t.exit_time)
ORDER BY trade_date DESC;

-- Create a function to calculate drawdown
CREATE OR REPLACE FUNCTION calculate_running_balance(account_id_param INTEGER)
RETURNS TABLE(
    trade_id INTEGER,
    exit_time TIMESTAMP WITH TIME ZONE,
    pnl_usd FLOAT,
    running_balance FLOAT,
    peak_balance FLOAT,
    drawdown_pct FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH trade_sequence AS (
        SELECT 
            t.id,
            t.exit_time,
            t.pnl_usd,
            SUM(t.pnl_usd) OVER (ORDER BY t.exit_time) as running_balance
        FROM trades t
        WHERE t.account_id = account_id_param 
            AND t.status = 'closed' 
            AND t.exit_time IS NOT NULL
        ORDER BY t.exit_time
    ),
    with_peaks AS (
        SELECT *,
            MAX(running_balance) OVER (ORDER BY exit_time ROWS UNBOUNDED PRECEDING) as peak_balance
        FROM trade_sequence
    )
    SELECT 
        ts.id::INTEGER,
        ts.exit_time,
        ts.pnl_usd::FLOAT,
        ts.running_balance::FLOAT,
        wp.peak_balance::FLOAT,
        CASE 
            WHEN wp.peak_balance > 0 THEN 
                ((wp.peak_balance - ts.running_balance) / wp.peak_balance * 100)::FLOAT
            ELSE 0::FLOAT
        END as drawdown_pct
    FROM trade_sequence ts
    JOIN with_peaks wp ON ts.id = wp.id
    ORDER BY ts.exit_time;
END;
$$ LANGUAGE plpgsql;

-- Create indexes on views (if supported by PostgreSQL version)
-- Note: Materialized views would be better for performance but require maintenance

-- Insert default admin user (password will be set via API)
-- This will be handled by the application initialization

-- Create default settings table for application configuration
CREATE TABLE IF NOT EXISTS app_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings
INSERT INTO app_settings (key, value, description) VALUES
    ('maintenance_mode', 'false', 'Enable/disable maintenance mode'),
    ('max_trades_per_day', '100', 'Maximum trades allowed per day per account'),
    ('data_retention_days', '365', 'Number of days to keep historical data'),
    ('api_rate_limit', '100', 'API requests per minute limit'),
    ('dashboard_refresh_interval', '30', 'Dashboard refresh interval in seconds')
ON CONFLICT (key) DO NOTHING;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_app_settings_updated_at
    BEFORE UPDATE ON app_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();