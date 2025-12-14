#!/usr/bin/env python3
"""
WOPR Config Service - Database-backed Configuration Service
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import yaml
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WOPR Config Service", version="1.0.0")

# Database connection
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://wopr:wopr@config-db:5432/config_db'
)
ENVIRONMENT = os.getenv('WOPR_ENVIRONMENT', 'default')


@contextmanager
def get_db():
    """Database connection context manager"""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


class ConfigValue(BaseModel):
    """Config value model"""
    key: str
    value: Any
    value_type: str
    description: Optional[str] = None
    environment: str = 'default'


class ConfigUpdate(BaseModel):
    """Config update model"""
    value: Any
    description: Optional[str] = None
    updated_by: Optional[str] = None


def parse_value(value_str: str, value_type: str) -> Any:
    """Parse JSON-encoded value based on type"""
    try:
        parsed = json.loads(value_str)
        
        # Type validation
        if value_type == 'string' and not isinstance(parsed, str):
            raise ValueError(f"Expected string, got {type(parsed)}")
        elif value_type == 'integer' and not isinstance(parsed, int):
            raise ValueError(f"Expected integer, got {type(parsed)}")
        elif value_type == 'float' and not isinstance(parsed, (int, float)):
            raise ValueError(f"Expected float, got {type(parsed)}")
        elif value_type == 'boolean' and not isinstance(parsed, bool):
            raise ValueError(f"Expected boolean, got {type(parsed)}")
        elif value_type == 'list' and not isinstance(parsed, list):
            raise ValueError(f"Expected list, got {type(parsed)}")
        elif value_type == 'dict' and not isinstance(parsed, dict):
            raise ValueError(f"Expected dict, got {type(parsed)}")
        
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def infer_type(value: Any) -> str:
    """Infer value type"""
    if isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, int):
        return 'integer'
    elif isinstance(value, float):
        return 'float'
    elif isinstance(value, list):
        return 'list'
    elif isinstance(value, dict):
        return 'dict'
    else:
        return 'string'


@app.get("/health")
def health():
    """Health check"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "environment": ENVIRONMENT}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503


@app.get("/get/{key:path}")
def get_value(key: str, environment: str = None):
    """
    Get configuration value by key.
    
    Examples:
        GET /get/storage.base_path
        GET /get/camera.resolutions.4k.width?environment=prod
    """
    if environment is None:
        environment = ENVIRONMENT
    
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Try exact match first
            cur.execute(
                """
                SELECT key, value, value_type, description, environment
                FROM settings
                WHERE key = %s AND environment = %s
                """,
                (key, environment)
            )
            row = cur.fetchone()
            
            # Fallback to default environment
            if not row and environment != 'default':
                cur.execute(
                    """
                    SELECT key, value, value_type, description, environment
                    FROM settings
                    WHERE key = %s AND environment = 'default'
                    """,
                    (key,)
                )
                row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Key not found: {key}")
            
            parsed_value = parse_value(row['value'], row['value_type'])
            
            return {
                'key': row['key'],
                'value': parsed_value,
                'value_type': row['value_type'],
                'description': row['description'],
                'environment': row['environment']
            }


@app.post("/get")
def get_multiple(request: dict):
    """
    Get multiple configuration values.
    
    Request:
        POST /get
        {
            "keys": ["storage.base_path", "camera.resolutions.4k.width"],
            "environment": "prod"
        }
    """
    keys = request.get('keys', [])
    environment = request.get('environment', ENVIRONMENT)
    
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            placeholders = ','.join(['%s'] * len(keys))
            cur.execute(
                f"""
                SELECT key, value, value_type
                FROM settings
                WHERE key IN ({placeholders}) 
                  AND (environment = %s OR environment = 'default')
                ORDER BY CASE WHEN environment = %s THEN 0 ELSE 1 END
                """,
                (*keys, environment, environment)
            )
            rows = cur.fetchall()
    
    # Build result dict, preferring environment-specific values
    result = {}
    seen = set()
    
    for row in rows:
        if row['key'] not in seen:
            parsed_value = parse_value(row['value'], row['value_type'])
            result[row['key']] = parsed_value
            seen.add(row['key'])
    
    return result


@app.get("/section/{section:path}")
def get_section(section: str, environment: str = None):
    """
    Get all keys in a section.
    
    Examples:
        GET /section/storage
        GET /section/camera.resolutions
    """
    if environment is None:
        environment = ENVIRONMENT
    
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Find all keys that start with section prefix
            cur.execute(
                """
                SELECT key, value, value_type, description
                FROM settings
                WHERE key LIKE %s 
                  AND (environment = %s OR environment = 'default')
                ORDER BY CASE WHEN environment = %s THEN 0 ELSE 1 END, key
                """,
                (f"{section}.%", environment, environment)
            )
            rows = cur.fetchall()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"Section not found: {section}")
    
    # Build nested dict
    result = {}
    seen = set()
    
    for row in rows:
        if row['key'] in seen:
            continue
        seen.add(row['key'])
        
        # Remove section prefix
        relative_key = row['key'][len(section) + 1:]
        parts = relative_key.split('.')
        
        # Navigate to nested position
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set value
        parsed_value = parse_value(row['value'], row['value_type'])
        current[parts[-1]] = parsed_value
    
    return result


@app.get("/all")
def get_all(environment: str = None):
    """Get entire configuration as nested dict"""
    if environment is None:
        environment = ENVIRONMENT
    
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT key, value, value_type
                FROM settings
                WHERE environment = %s OR environment = 'default'
                ORDER BY CASE WHEN environment = %s THEN 0 ELSE 1 END, key
                """,
                (environment, environment)
            )
            rows = cur.fetchall()
    
    # Build nested dict
    result = {}
    seen = set()
    
    for row in rows:
        if row['key'] in seen:
            continue
        seen.add(row['key'])
        
        parts = row['key'].split('.')
        current = result
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        parsed_value = parse_value(row['value'], row['value_type'])
        current[parts[-1]] = parsed_value
    
    return result


@app.put("/set/{key:path}")
def set_value(key: str, update: ConfigUpdate, environment: str = None):
    """
    Set/update configuration value.
    
    Request:
        PUT /set/storage.base_path
        {
            "value": "/new/path",
            "description": "Updated storage path",
            "updated_by": "bob"
        }
    """
    if environment is None:
        environment = ENVIRONMENT
    
    value_type = infer_type(update.value)
    value_json = json.dumps(update.value)
    
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get old value for history
            cur.execute(
                "SELECT value FROM settings WHERE key = %s AND environment = %s",
                (key, environment)
            )
            old_row = cur.fetchone()
            old_value = old_row['value'] if old_row else None
            
            # Upsert new value
            cur.execute(
                """
                INSERT INTO settings (key, value, value_type, description, environment, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (key) WHERE environment = %s
                DO UPDATE SET 
                    value = EXCLUDED.value,
                    value_type = EXCLUDED.value_type,
                    description = COALESCE(EXCLUDED.description, settings.description),
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                RETURNING *
                """,
                (key, value_json, value_type, update.description, environment, update.updated_by, environment)
            )
            result = cur.fetchone()
            
            # Record history
            cur.execute(
                """
                INSERT INTO config_history (key, old_value, new_value, changed_by, environment)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (key, old_value, value_json, update.updated_by, environment)
            )
            
            conn.commit()
    
    return {
        'key': result['key'],
        'value': parse_value(result['value'], result['value_type']),
        'value_type': result['value_type'],
        'description': result['description']
    }


@app.delete("/delete/{key:path}")
def delete_value(key: str, environment: str = None):
    """Delete configuration value"""
    if environment is None:
        environment = ENVIRONMENT
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM settings WHERE key = %s AND environment = %s RETURNING key",
                (key, environment)
            )
            deleted = cur.fetchone()
            
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Key not found: {key}")
            
            conn.commit()
    
    return {"deleted": key}


@app.get("/history/{key:path}")
def get_history(key: str, limit: int = 10):
    """Get change history for a key"""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT key, old_value, new_value, changed_by, changed_at, environment
                FROM config_history
                WHERE key = %s
                ORDER BY changed_at DESC
                LIMIT %s
                """,
                (key, limit)
            )
            rows = cur.fetchall()
    
    return [
        {
            'key': row['key'],
            'old_value': json.loads(row['old_value']) if row['old_value'] else None,
            'new_value': json.loads(row['new_value']) if row['new_value'] else None,
            'changed_by': row['changed_by'],
            'changed_at': row['changed_at'].isoformat(),
            'environment': row['environment']
        }
        for row in rows
    ]


@app.post("/import/yaml")
async def import_yaml(request: dict):
    """
    Import configuration from YAML.
    
    Request:
        POST /import/yaml
        {
            "yaml_content": "<YAML string>",
            "environment": "prod",
            "updated_by": "bob"
        }
    """
    yaml_content = request.get('yaml_content', '')
    environment = request.get('environment', 'default')
    updated_by = request.get('updated_by', 'system')
    
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    
    def flatten_dict(d: dict, prefix: str = '') -> dict:
        """Flatten nested dict into dot-notation keys"""
        items = {}
        for k, v in d.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(flatten_dict(v, new_key))
            else:
                items[new_key] = v
        return items
    
    flat = flatten_dict(data)
    
    with get_db() as conn:
        with conn.cursor() as cur:
            for key, value in flat.items():
                value_type = infer_type(value)
                value_json = json.dumps(value)
                
                cur.execute(
                    """
                    INSERT INTO settings (key, value, value_type, environment, updated_by)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (key) WHERE environment = %s
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        value_type = EXCLUDED.value_type,
                        updated_at = NOW(),
                        updated_by = EXCLUDED.updated_by
                    """,
                    (key, value_json, value_type, environment, updated_by, environment)
                )
            
            conn.commit()
    
    return {"imported": len(flat), "environment": environment}


@app.get("/export/yaml")
def export_yaml(environment: str = None):
    """Export configuration as YAML"""
    config = get_all(environment)
    yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
    return {"yaml": yaml_str, "environment": environment or ENVIRONMENT}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)
