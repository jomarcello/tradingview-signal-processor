-- Voeg indexen toe voor snellere queries
CREATE INDEX idx_subscribers_assets ON subscribers USING gin(assets);
CREATE INDEX idx_subscribers_timeframes ON subscribers USING gin(preferred_timeframes);

-- Materialized view voor veelgebruikte queries
CREATE MATERIALIZED VIEW active_subscribers AS
SELECT * FROM subscribers 
WHERE status = 'active' 
AND last_active > NOW() - INTERVAL '30 days'; 