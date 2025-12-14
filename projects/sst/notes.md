# Single Source of Truth

```
┌─────────────────────────────────────────────────┐
│         Config Service (FastAPI)                │
│  - REST API for CRUD operations                 │
│  - Reads from PostgreSQL                        │
│  - Optional YAML import/export                  │
│  - WebSocket for live updates (future)          │
└────────────────┬────────────────────────────────┘
                 │
                 v
         ┌───────────────┐
         │  PostgreSQL   │
         │  config_db    │
         │               │
         │  Tables:      │
         │  - settings   │
         │  - history    │
         └───────────────┘
```
