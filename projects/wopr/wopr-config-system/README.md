# WOPR Config System

Database-backed centralized configuration service for the WOPR (Tactical Wargaming Adjudication Tracker) project.

## Overview

This system provides:
- **Config Service**: FastAPI-based HTTP service backed by PostgreSQL
- **WOPR Core Library**: Python client library for accessing config
- **Dynamic Updates**: Change configuration without redeploying services
- **Change History**: Full audit trail of all config changes
- **Environment Support**: Multiple environments (dev, staging, prod)
- **YAML Import/Export**: Seed from YAML, export for backups

## Architecture

```
┌─────────────────────────────────────┐
│   Config Service (FastAPI)          │
│   http://config-service:8080        │
└─────────────┬───────────────────────┘
              │
              v
      ┌───────────────┐
      │  PostgreSQL   │
      │  config_db    │
      └───────────────┘

┌─────────┐  ┌─────────┐  ┌─────────┐
│ Camera  │  │ Backend │  │ Worker  │
│ Service │  │   API   │  │ Service │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     └────────────┴────────────┘
       All use wopr-core library
       to fetch config via HTTP
```

## Quick Start

### 1. Start Config Service (Local Development)

```bash
cd config-service
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- Config Service on port 8080

### 2. Seed Initial Configuration

```bash
# Import config.yaml into database
curl -X POST http://localhost:8080/import/yaml \
  -H "Content-Type: text/plain" \
  --data-binary @examples/config.yaml
```

### 3. Test the Service

```bash
# Get a single value
curl http://localhost:8080/get/storage.base_path

# Get entire section
curl http://localhost:8080/section/camera

# Get all config
curl http://localhost:8080/all
```

### 4. Install WOPR Core Library

```bash
cd wopr-core
pip install -e .
```

### 5. Use in Your Code

```python
from wopr.config import init_config, get_str, get_int

# Initialize (points to config service)
init_config()  # Uses WOPR_CONFIG_SERVICE_URL env var

# Fetch config values
base_path = get_str('storage.base_path')
width = get_int('camera.resolutions.4k.width')
```

## Directory Structure

```
wopr-config-system/
├── config-service/         # FastAPI config service
│   ├── app.py             # Main application
│   ├── schema.sql         # Database schema
│   ├── Dockerfile         # Docker image
│   ├── docker-compose.yml # Local development
│   ├── requirements.txt   # Python dependencies
│   └── k8s/              # Kubernetes manifests
│       ├── deployment.yaml
│       └── configmap.yaml
│
├── wopr-core/             # Python client library
│   ├── setup.py          # Package setup
│   ├── pyproject.toml    # Modern packaging
│   ├── wopr/             # Library code
│   │   ├── __init__.py
│   │   ├── config.py     # HTTP config client
│   │   ├── storage.py    # Image path utilities
│   │   ├── logging.py    # Logging setup
│   │   └── constants.py  # Shared constants
│   └── tests/            # Unit tests
│
├── examples/              # Example code
│   ├── config.yaml       # Sample configuration
│   ├── camera-service.py # Camera service example
│   └── backend-api-example.py
│
└── scripts/              # Utility scripts
    ├── seed-config.sh    # Seed database from YAML
    └── test-config-service.sh
```

## API Endpoints

### Read Operations

- `GET /health` - Health check
- `GET /get/{key}` - Get single value (e.g. `/get/storage.base_path`)
- `POST /get` - Get multiple values (body: `{"keys": [...]}`)
- `GET /section/{section}` - Get entire section (e.g. `/section/camera`)
- `GET /all` - Get all configuration
- `GET /history/{key}` - Get change history for a key

### Write Operations

- `PUT /set/{key}` - Set/update value
- `DELETE /delete/{key}` - Delete value

### Import/Export

- `POST /import/yaml` - Import from YAML
- `GET /export/yaml` - Export to YAML

## Configuration Examples

### Update a Value

```bash
curl -X PUT http://localhost:8080/set/camera.default_resolution \
  -H "Content-Type: application/json" \
  -d '{
    "value": "1080p",
    "description": "Changed for testing",
    "updated_by": "bob"
  }'
```

### View Change History

```bash
curl http://localhost:8080/history/camera.default_resolution
```

### Export Current Config

```bash
curl http://localhost:8080/export/yaml > backup.yaml
```

## Environment Variables

### Config Service

- `DATABASE_URL` - PostgreSQL connection string (default: `postgresql://wopr:wopr@config-db:5432/config_db`)
- `WOPR_ENVIRONMENT` - Environment name (default: `default`)

### WOPR Core Library

- `WOPR_CONFIG_SERVICE_URL` - Config service URL (default: `http://config-service:8080`)
- `WOPR_CONFIG_CACHE` - Enable caching (default: `true`)

## Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f config-service/k8s/

# Seed configuration
kubectl exec -n wopr deployment/config-service -- \
  curl -X POST http://localhost:8080/import/yaml \
  --data-binary @/etc/wopr/config.yaml
```

## Development

### Run Tests

```bash
cd wopr-core
pytest tests/
```

### Run Config Service Locally

```bash
cd config-service
pip install -r requirements.txt
python app.py
```

### Add New Configuration

1. Add to `examples/config.yaml`
2. Import: `curl -X POST http://localhost:8080/import/yaml --data-binary @examples/config.yaml`
3. Or set directly: `curl -X PUT http://localhost:8080/set/new.key -d '{"value": "..."}'`

## Features

### Change History

Every config change is tracked:
- What changed
- Old and new values
- Who made the change
- When it happened

```bash
curl http://localhost:8080/history/storage.base_path
```

### Multiple Environments

Support dev, staging, prod configs in one database:

```bash
# Set prod-specific value
curl -X PUT "http://localhost:8080/set/api.host?environment=prod" \
  -d '{"value": "api.production.com"}'

# Get prod config
curl "http://localhost:8080/get/api.host?environment=prod"
```

### Caching

Client library caches values to reduce HTTP calls:

```python
from wopr.config import get_str

# First call: HTTP request
value = get_str('storage.base_path')

# Subsequent calls: cached
value = get_str('storage.base_path')  # No HTTP call
```

## Troubleshooting

### Config service not starting

Check database connection:
```bash
docker-compose logs config-db
docker-compose logs config-service
```

### Client can't connect

Verify service URL:
```bash
export WOPR_CONFIG_SERVICE_URL=http://localhost:8080
python -c "from wopr.config import get_str; print(get_str('storage.base_path'))"
```

### Database schema issues

Re-initialize:
```bash
docker-compose down -v
docker-compose up -d
```

## License

MIT

## Author

Bob - WOPR Project
