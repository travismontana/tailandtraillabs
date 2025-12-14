

```mermaid
flowchart LR
  %% ====== Client ======
  U[User<br/>Desktop/Mobile Browser] -->|HTTPS https://wopr| DNS[DNS: wopr -> Studio Cluster Ingress]

  %% ====== Studio K8s Cluster ======
  subgraph K8S[Studio Kubernetes Cluster]
    ING[Ingress / Ingress Controller]
    WEB[wopr-web<br/>Web UI]
    API[wopr-api<br/>FastAPI :8080<br/>Routing + Orchestration]
    CFG[wopr-config_service<br/>Centralized Config API<br/>SSoT: wopr.config.yaml]
    VSN[wopr-vision<br/>CV / Detection / Learning<br/>Goal: state extraction]
    ADJ[wopr-adjudicator<br/>Rules + LLM Orchestrator<br/>Cheat detection]
    DB[(wopr-db<br/>PostgreSQL)]
    CFGDB[(wopr-config-db<br/>Schema/DB in Postgres)]
    OTHER[wopr-...<br/>Other services]
  end

  DNS --> ING --> WEB
  WEB -->|API calls| API

  %% ====== Config flows ======
  API -->|read config| CFG
  WEB -->|edit config (UI)| CFG
  VSN -->|read config| CFG
  ADJ -->|read config| CFG
  OTHER -->|read config| CFG

  %% ====== Core processing flows ======
  API -->|request capture| CAM
  API -->|invoke vision| VSN
  API -->|invoke adjudication| ADJ
  ADJ -->|ask for enhanced scan / targeted regions| VSN

  %% ====== Data persistence ======
  API --> DB
  VSN --> DB
  ADJ --> DB
  CFG --> CFGDB
  CFGDB --- DB

  %% ====== Edge devices & storage ======
  subgraph EDGE[Edge / Home Lab]
    CAM[wopr-cam<br/>Raspberry Pi Web Service<br/>4K-ish Webcam]
    NAS[(NAS Storage)]
  end

  CAM -->|store images| NAS
  API -->|fetch image refs / paths| NAS
  VSN -->|read images| NAS
```
