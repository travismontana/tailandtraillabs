-- WOPR Config Service Database Schema

-- Config settings table
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    value_type VARCHAR(50) NOT NULL,  -- string, integer, float, boolean, list, dict
    description TEXT,
    environment VARCHAR(50) NOT NULL DEFAULT 'default',  -- default, dev, prod, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100),
    UNIQUE(key, environment)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
CREATE INDEX IF NOT EXISTS idx_settings_environment ON settings(environment);
CREATE INDEX IF NOT EXISTS idx_settings_key_env ON settings(key, environment);

-- Config change history table
CREATE TABLE IF NOT EXISTS config_history (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT NOW(),
    environment VARCHAR(50) DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_history_key ON config_history(key);
CREATE INDEX IF NOT EXISTS idx_history_changed_at ON config_history(changed_at);

-- Seed initial configuration (examples)
INSERT INTO settings (key, value, value_type, description, environment) VALUES
-- Storage
('storage.base_path', '"/mnt/nas/twat"', 'string', 'Base storage path for images', 'default'),
('storage.games_subdir', '"games"', 'string', 'Subdirectory for game data', 'default'),
('storage.default_extension', '"jpg"', 'string', 'Default image extension', 'default'),
('storage.image_extensions', '["jpg", "png"]', 'list', 'Allowed image extensions', 'default'),
('storage.ensure_directories', 'true', 'boolean', 'Auto-create directories', 'default'),
('storage.thumbnail_size', '[480, 480]', 'list', 'Thumbnail dimensions [width, height]', 'default'),

-- Filenames
('filenames.timestamp_format', '"%Y%m%d-%H%M%S"', 'string', 'Timestamp format for filenames', 'default'),
('filenames.image_template', '"{timestamp}-{subject}.{extension}"', 'string', 'Image filename template', 'default'),
('filenames.image_with_sequence_template', '"{timestamp}-{subject}-{sequence:03d}.{extension}"', 'string', 'Image filename template with sequence', 'default'),
('filenames.thumbnail_template', '"{timestamp}-{subject}-thumb.{extension}"', 'string', 'Thumbnail filename template', 'default'),

-- Camera
('camera.default_resolution', '"4k"', 'string', 'Default camera resolution', 'default'),
('camera.resolutions.4k.width', '4608', 'integer', '4K width', 'default'),
('camera.resolutions.4k.height', '2592', 'integer', '4K height', 'default'),
('camera.resolutions.1080p.width', '1920', 'integer', '1080p width', 'default'),
('camera.resolutions.1080p.height', '1080', 'integer', '1080p height', 'default'),
('camera.resolutions.720p.width', '1280', 'integer', '720p width', 'default'),
('camera.resolutions.720p.height', '720', 'integer', '720p height', 'default'),
('camera.capture_delay_seconds', '2', 'integer', 'Delay before capture', 'default'),
('camera.default_format', '"RGB888"', 'string', 'Default image format', 'default'),
('camera.buffer_count', '2', 'integer', 'Camera buffer count', 'default'),

-- Logging
('logging.default_level', '"INFO"', 'string', 'Default log level', 'default'),
('logging.format', '"%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"', 'string', 'Log format string', 'default'),
('logging.date_format', '"%Y-%m-%d %H:%M:%S"', 'string', 'Log date format', 'default'),
('logging.default_log_dir', '"/var/log/wopr"', 'string', 'Default log directory', 'default'),

-- API
('api.host', '"0.0.0.0"', 'string', 'API host', 'default'),
('api.port', '8000', 'integer', 'API port', 'default'),
('api.camera_service_url', '"http://raspberrypi.local:5000"', 'string', 'Camera service URL', 'default'),
('api.camera_timeout_seconds', '30', 'integer', 'Camera request timeout', 'default'),
('api.ollama_url', '"http://desktop:11434"', 'string', 'Ollama service URL', 'default'),
('api.ollama_timeout_seconds', '60', 'integer', 'Ollama request timeout', 'default'),

-- Vision
('vision.default_model', '"qwen2-vl:7b"', 'string', 'Default vision model', 'default'),
('vision.opencv_change_threshold', '30', 'integer', 'OpenCV change detection threshold', 'default'),
('vision.min_change_area_pixels', '1000', 'integer', 'Minimum change area in pixels', 'default'),
('vision.gaussian_blur_kernel', '[21, 21]', 'list', 'Gaussian blur kernel size', 'default'),
('vision.morphology_kernel', '[5, 5]', 'list', 'Morphology kernel size', 'default'),
('vision.morphology_iterations.dilate', '2', 'integer', 'Dilate iterations', 'default'),
('vision.morphology_iterations.erode', '1', 'integer', 'Erode iterations', 'default'),

-- Database
('database.connection_pool_size', '5', 'integer', 'Connection pool size', 'default'),
('database.connection_timeout_seconds', '30', 'integer', 'Connection timeout', 'default'),
('database.max_overflow', '10', 'integer', 'Max overflow connections', 'default'),

-- Game Types
('game_types', '[{"id": "dune_imperium", "display_name": "Dune Imperium"}, {"id": "star_wars_legion", "display_name": "Star Wars Legion"}]', 'list', 'Supported game types', 'default'),

-- Game Statuses
('game_statuses', '["setup", "in_progress", "completed", "abandoned"]', 'list', 'Valid game statuses', 'default'),

-- Analysis Statuses  
('analysis_statuses', '["pending", "processing", "completed", "failed"]', 'list', 'Valid analysis statuses', 'default'),

-- Image Subjects
('image_subjects', '["setup", "capture", "move", "thumbnail"]', 'list', 'Valid image subject types', 'default')


ON CONFLICT (key, environment)
DO UPDATE SET
    value       = EXCLUDED.value,
    value_type  = EXCLUDED.value_type,
    description = EXCLUDED.description,
    updated_at  = NOW(),
    updated_by  = EXCLUDED.updated_by;