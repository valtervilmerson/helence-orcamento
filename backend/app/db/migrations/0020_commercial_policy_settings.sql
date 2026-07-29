INSERT INTO app_settings (key, value)
VALUES ('discount_limit_percent', '8')
ON CONFLICT(key) DO NOTHING;

INSERT INTO app_settings (key, value)
VALUES ('default_validity_days', '30')
ON CONFLICT(key) DO NOTHING;
