# WOPR - Wargaming Oversight & Position Recognition

## What is WOPR?

WOPR tracks tabletop game state through computer vision.  Players use a web interface to capture overhead images of their game board. WOPR analyzes the images, detects game pieces, validates moves against rules, and maintains a complete game history.

## User Flow

1. User browses to [https://wopr](https://wopr/) (resolves to k8s ingress)
2. Select game type (Dune Imperium, Star Wars Legion, etc.)
3. Enter game details (players, initial setup)
4. Click "Capture" after each move
5. WOPR analyzes board state, validates rules
6. View game history, replay moves, export state

## Architecture

### Frontend

**wopr-web** - React 18 SPA

- Game selection and setup
- Live capture triggering
- Real-time analysis results display
- Game history/replay viewer
- Config editor (admin)
- Responsive: mobile/desktop, light/dark mode

### API Layer

**wopr-api** - FastAPI (Python 3.11+)

- Port: 8000
- Handles routing and orchestration
- Synchronous endpoints: game CRUD, status queries
- Async task queueing: vision analysis, rule validation
- Direct database access for reads/writes

### Storage & Config

**wopr-config-service** - FastAPI

- Port: 8080
- Centralized configuration service
- PostgreSQL backend (wopr_config database)
- HTTP API: GET/SET config values
- Change history and audit trail
- See Appendix A for schema

**wopr-db** - PostgreSQL 16 StatefulSet

- Databases:
    - wopr_main: game data, captures, analysis
    - wopr_config: configuration store
- 20Gi PVC, single replica (HA later)
- Backups: pg_dump to NAS nightly (TBD)

**wopr-redis** - Redis 7

- Celery task broker
- Config value caching
- Session storage (future)

**NFS Storage** - /mnt/nas/wopr

- Mounted by all pods
- Images: /mnt/nas/wopr/games/{game_id}/
- Backed by existing NAS infrastructure

### Processing Services

**wopr-worker** - Celery workers (Python 3.11+)

- Async task processing
- Multiple replicas for scaling
- Tasks:
    - Vision analysis (30-60s per image)
    - Board state validation
    - Thumbnail generation
    - Historical game replay

**wopr-vision** - Vision processing service

- Ollama + Qwen2-VL:7b for image understanding
- OpenCV for change detection, segmentation
- Future: YOLOv8 custom models per game
- Runs on nodes with GPU access (desktop: 4080 Super)

**wopr-adjudicator** - Rules engine service

- Validates moves against game rules
- Detects illegal plays/cheating
- LLM-based rule interpretation for edge cases
- Coordinates re-analysis requests to wopr-vision
- Rule definitions per game type in config

### Edge Services

**wopr-cam** - Camera service (Raspberry Pi)

- Flask API, port 5000
- Camera Module 3 (12MP, 4K capable)
- Endpoint: POST /capture
- Saves to NFS, returns image path
- Systemd service, runs as wopr user
- 3D printed overhead mount

## Data Flows

### Capture & Analyze (Async)

```
User → wopr-web → wopr-api
                    ↓
              HTTP → wopr-cam → image saved to NFS
                    ↓
              Celery task queued
                    ↓
              wopr-worker picks up task
                    ↓
              calls wopr-vision → analysis
                    ↓
              calls wopr-adjudicator → validation
                    ↓
              saves to wopr-db
                    ↓
              wopr-web polls/WebSocket → displays results

```

### Manual Analysis (User triggered later)

```
User → "Analyze capture #5" → wopr-api
                                ↓
                          Celery task queued
                                ↓
                          (same as above)

```

### Config Updates

```
User → wopr-web config editor → wopr-api
                                   ↓
                            wopr-config-service
                                   ↓
                            PostgreSQL update
                                   ↓
                          All services fetch new value

```

## Tech Stack

- **K8s Cluster**: studio (on-prem)
- **Ingress**: Traefik with cert-manager (TLS)
- **Languages**: Python 3.11+, JavaScript/React
- **Frameworks**: FastAPI, React 18
- **Databases**: PostgreSQL 16, Redis 7
- **Vision**: Ollama (Qwen2-VL), OpenCV, YOLOv8
- **Task Queue**: Celery + Redis
- **Storage**: NFS (existing NAS)
- **GitOps**: ArgoCD
- **Monitoring**: Prometheus, Grafana, Loki

## Future Services

- **wopr-notifier**: WebSocket/SSE for real-time updates
- **wopr-replay**: Game replay and video generation
- **wopr-tournament**: Multi-game tournament tracking
- **wopr-ml-trainer**: Custom model training pipeline