# WOPR Config System - Quick Start Guide

Get up and running in 5 minutes.

## Prerequisites

- Docker and docker-compose
- Python 3.11+
- curl and jq (for testing)

## Step 1: Start Config Service (2 minutes)

```bash
cd config-service
docker-compose up -d

# Wait for services to be ready
docker-compose logs -f config-service
# Press Ctrl+C once you see "Application startup complete"
```

## Step 2: Seed Configuration (30 seconds)

```bash
cd ..
./scripts/seed-config.sh examples/config.yaml
```

## Step 3: Test the Service (30 seconds)

```bash
./scripts/test-config-service.sh
```

## Step 4: Install WOPR Core Library (1 minute)

```bash
cd wopr-core
pip install -e .
```

## Step 5: Try It Out (1 minute)

```python
from wopr.config import init_config, get_str, get_int
from wopr.storage import imagefilename

# Initialize (uses WOPR_CONFIG_SERVICE_URL env var or default)
init_config()

# Get config values
base_path = get_str('storage.base_path')
print(f"Storage path: {base_path}")

camera_res = get_str('camera.default_resolution')
width = get_int(f'camera.resolutions.{camera_res}.width')
print(f"Camera: {camera_res} = {width}px wide")

# Generate filename
filepath = imagefilename("game123", "capture", sequence=1)
print(f"Image path: {filepath}")
```

## That's It!

Your config service is running and accessible at http://localhost:8080

### Next Steps

- Browse the API: http://localhost:8080/docs (FastAPI auto-generated docs)
- View all config: `curl http://localhost:8080/all | jq .`
- Update a value: `curl -X PUT http://localhost:8080/set/test.key -d '{"value": "test"}'`
- See examples in `examples/` directory
- Deploy to Kubernetes: `kubectl apply -f config-service/k8s/`

### Environment Variables

For your services to find the config service:

```bash
export WOPR_CONFIG_SERVICE_URL=http://localhost:8080
```

Or in Kubernetes:
```yaml
env:
- name: WOPR_CONFIG_SERVICE_URL
  value: http://config-service.wopr.svc.cluster.local:8080
```

### Troubleshooting

**Service won't start:**
```bash
docker-compose logs config-db
docker-compose logs config-service
```

**Can't connect from code:**
```bash
# Check service is running
curl http://localhost:8080/health

# Set URL explicitly
export WOPR_CONFIG_SERVICE_URL=http://localhost:8080
python your_script.py
```

**Database issues:**
```bash
# Reset everything
docker-compose down -v
docker-compose up -d
./scripts/seed-config.sh
```
