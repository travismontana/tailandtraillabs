-- Config settings table
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    value_type VARCHAR(50) NOT NULL,  -- string, integer, float, boolean, list, dict
    description TEXT,
    environment VARCHAR(50) DEFAULT 'default',  -- default, dev, prod, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Index for fast lookups
CREATE INDEX idx_settings_key ON settings(key);
CREATE INDEX idx_settings_environment ON settings(environment);
CREATE INDEX idx_settings_key_env ON settings(key, environment);

-- Config change history
CREATE TABLE IF NOT EXISTS config_history (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT NOW(),
    environment VARCHAR(50) DEFAULT 'default'
);

CREATE INDEX idx_history_key ON config_history(key);
CREATE INDEX idx_history_changed_at ON config_history(changed_at);

-- Example data
INSERT INTO settings (key, value, value_type, description) VALUES
('storage.base_path', '"/mnt/nas/twat"', 'string', 'Base storage path for images'),
('storage.games_subdir', '"games"', 'string', 'Subdirectory for game data'),
('storage.default_extension', '"jpg"', 'string', 'Default image extension'),
('storage.image_extensions', '["jpg", "png"]', 'list', 'Allowed image extensions'),
('storage.ensure_directories', 'true', 'boolean', 'Auto-create directories'),

('camera.default_resolution', '"4k"', 'string', 'Default camera resolution'),
('camera.resolutions.4k.width', '4608', 'integer', '4K width'),
('camera.resolutions.4k.height', '2592', 'integer', '4K height'),
('camera.resolutions.1080p.width', '1920', 'integer', '1080p width'),
('camera.resolutions.1080p.height', '1080', 'integer', '1080p height'),

('logging.default_level', '"INFO"', 'string', 'Default log level'),
('api.camera_service_url', '"http://raspberrypi.local:5000"', 'string', 'Camera service URL'),
('api.ollama_url', '"http://desktop:11434"', 'string', 'Ollama service URL')

ON CONFLICT (key) DO NOTHING;