#!/usr/bin/env python3
"""
WOPR Config Service - Centralized Configuration HTTP API
"""
from flask import Flask, jsonify, request
import yaml
from pathlib import Path
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config.yaml once at startup
CONFIG_FILE = os.getenv('WOPR_CONFIG_FILE', '/etc/wopr/config.yaml')
config_data = {}


def load_config():
    """Load configuration from YAML file"""
    global config_data
    
    if not Path(CONFIG_FILE).exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
    
    with open(CONFIG_FILE, 'r') as f:
        config_data = yaml.safe_load(f)
    
    logger.info(f"Loaded config from {CONFIG_FILE}")


def get_nested_value(data: dict, key_path: str, default=None):
    """
    Get value from nested dict using dot notation.
    
    Examples:
        get_nested_value(data, 'storage.base_path')
        get_nested_value(data, 'camera.resolutions.4k.width')
    """
    parts = key_path.split('.')
    value = data
    
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default
    
    return value


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'config_file': CONFIG_FILE})


@app.route('/reload', methods=['POST'])
def reload():
    """Reload configuration from file"""
    try:
        load_config()
        return jsonify({'status': 'reloaded', 'config_file': CONFIG_FILE})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get/<path:key>', methods=['GET'])
def get_value(key: str):
    """
    Get configuration value by dot-notation key.
    
    Examples:
        GET /get/storage.base_path
        GET /get/camera.resolutions.4k.width
        GET /get/logging.default_level
    """
    value = get_nested_value(config_data, key)
    
    if value is None:
        return jsonify({'error': f'Key not found: {key}'}), 404
    
    return jsonify({'key': key, 'value': value})


@app.route('/get', methods=['POST'])
def get_multiple():
    """
    Get multiple configuration values at once.
    
    Request:
        POST /get
        {"keys": ["storage.base_path", "camera.resolutions.4k.width"]}
    
    Response:
        {
            "storage.base_path": "/mnt/nas/twat",
            "camera.resolutions.4k.width": 4608
        }
    """
    try:
        keys = request.json.get('keys', [])
    except:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    if not isinstance(keys, list):
        return jsonify({'error': 'keys must be a list'}), 400
    
    result = {}
    for key in keys:
        value = get_nested_value(config_data, key)
        if value is not None:
            result[key] = value
    
    return jsonify(result)


@app.route('/section/<section>', methods=['GET'])
def get_section(section: str):
    """
    Get entire configuration section.
    
    Examples:
        GET /section/storage
        GET /section/camera
        GET /section/camera.resolutions
    """
    value = get_nested_value(config_data, section)
    
    if value is None:
        return jsonify({'error': f'Section not found: {section}'}), 404
    
    return jsonify(value)


@app.route('/all', methods=['GET'])
def get_all():
    """Get entire configuration"""
    return jsonify(config_data)


if __name__ == '__main__':
    load_config()
    
    host = os.getenv('CONFIG_SERVICE_HOST', '0.0.0.0')
    port = int(os.getenv('CONFIG_SERVICE_PORT', '8080'))
    
    app.run(host=host, port=port)