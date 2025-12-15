# WOPR Project Status

**Last Updated:** 2025-12-14
**Current Phase:** Phase 1 - Infrastructure

---

**Things I'd like now that I've had time to process things**
- on wopr_config - needs a UI that can edit the thing like yaml.
- local config cache, cache invalidation, config versioning in the DB, auto config rollback if a problem detected, problem detection. 
- status page
- telemetry 
- add telemetry to config and core module
- centralize the core module
- 

---

## 🎯 Current Focus

**20251214 - 2025, Dec 14**
**What I'm actively working on right now:**
- [ ] Setting up config service in k8s cluster
- [X] rpi + webcam (Bus 001 Device 003: ID 328f:00ec EMEET EMEET SmartCam C960 4K)
- [X] have a python script to caputre the images using the wopr-config python module.
- [X] writing a service to run on woprcam (the pi) and take the image.
- [X] Decision: naming convention, so wopr-config_service not wopr-config-service, because the thing is "config_service" and wopr is the "app" or "env" or whatever. - seperates major things, _ is spaces in names in names of services or apps, so app-service_name.
- [ ] want to see how to integrate a proper project mangement system easily into claude and my github so I can use 1 ui for code and pm tracking, and claude is updated.  Or if I can just do diffs like this, where I update this section, and paste it into claude, that'd work, but I'd like him to at least see my code and keep updated of what's going on. Do this:
```
git commit -m "feat: wopr-cam_service flask endpoint"

# Update STATUS.md
# Add commit message to "Recently Completed"

# When chatting with Claude
git log --oneline -10 > recent_work.txt
# Paste STATUS.md + recent_work.txt
```

**Where to pick up:**
- Get wopr_config in k8s
- python module distribution
- 

**Time estimate to complete current tasks:** 

---

## ✅ Recently Completed (Last 7 Days)

- [x] 2025-12-14: Config system built (wopr-config-service)
- [x] 2025-12-14: WOPR core library created
- [x] 2025-12-14: Documentation framework started
- [x] 2025-12-14: Milestones defined

---

## 🚧 Blockers / Issues

**Active blockers:**
- None currently

**Questions/Decisions needed:**
- Should wopr-vision and wopr-adjudicator be separate services or combined?
- 

**Waiting on:**
- Hardware: RPi Camera Module 3 (ETA: )
- 

---

## 📋 Next Steps (Prioritized)

1. Deploy config service to k8s
2. Set up PostgreSQL (wopr-db)
3. Configure NFS mounts on k8s nodes
4. Build wopr-cam service skeleton
5. 

---

## 📊 Quick Stats

| Metric | Status |
|--------|--------|
| Services Deployed | 0/9 |
| Tests Passing | N/A |
| Database Migrations | 0 created |
| Last Successful Capture | N/A |
| Total Games Tracked | 0 |
| Config Service | Local only |

---

## 🔧 Environment Status

**What's running where:**
- **Local (docker-compose):**
  - [x] wopr-config-service (port 8080)
  - [x] wopr-config-db (PostgreSQL)
  
- **K8s Cluster (studio):**
  - [ ] Nothing deployed yet
  
- **Raspberry Pi:**
  - [ ] Not set up yet
  
- **Desktop (Ollama):**
  - [ ] Not configured yet

---

## 📝 Technical Decisions Made

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-14 | Use database-backed config service | Dynamic updates without redeployment |
| 2025-12-14 | Celery for async processing | Vision analysis takes 30-60s, can't block API |
| 2025-12-14 | FastAPI for wopr-api | Modern, async-capable, good docs |
| | | |

---

## 🐛 Known Issues

- None yet

---

## 💡 Ideas / Future Enhancements

- Consider WebSocket for real-time UI updates instead of polling
- Look into persistent volume claims for PostgreSQL HA
- 

---

## 📚 Resources / Links

**Documentation:**
- Architecture doc: `~/Documents/wopr/files/TWAT_2.0_Architecture_Guide.md`
- Config system: `~/Documents/wopr/files/wopr-config-system/`
- This status: `~/Documents/wopr/STATUS.md`

**External:**
- Qwen2-VL docs: https://github.com/QwenLM/Qwen2-VL
- FastAPI docs: https://fastapi.tiangolo.com/
- Celery docs: https://docs.celeryq.dev/

---

## 🗂️ Phase Tracking

### Phase 0: Foundation ✅
- [x] Architecture design
- [x] Tech stack decisions
- [x] Config system implementation
- [x] Documentation started

### Phase 1: Infrastructure (IN PROGRESS)
**Config & Storage**
- [x] wopr-config-service - HTTP API
- [x] wopr-config-db - PostgreSQL schema
- [x] wopr-core library - Python client
- [ ] Deploy config service to k8s ← CURRENT
- [ ] Test config service from all hosts
- [ ] NFS mount on k8s nodes
- [ ] Directory structure: `/mnt/nas/wopr/games/`

**Database**
- [ ] PostgreSQL StatefulSet deployed
- [ ] wopr_main database schema
- [ ] Database migrations (Alembic)
- [ ] Backup strategy

**Message Queue**
- [ ] Redis deployed
- [ ] Celery configured
- [ ] Test task queue

### Phase 2: Camera & Capture
- [ ] Hardware acquired
- [ ] Camera mounted
- [ ] wopr-cam service built
- [ ] Test captures

### Phase 3: API Layer
- [ ] wopr-api scaffolded
- [ ] Database models
- [ ] Endpoints implemented
- [ ] Deployed to k8s

### Phase 4: Vision Processing
- [ ] Ollama setup
- [ ] OpenCV implementation
- [ ] wopr-worker deployed

### Phase 5: Frontend
- [ ] wopr-web scaffolded
- [ ] UI components built
- [ ] Deployed

### Phase 6-10: (See full milestone doc)

---

## 📅 Timeline / Milestones

**Target Dates:**
- [ ] 2025-12-21: Phase 1 complete (Infrastructure)
- [ ] 2025-12-28: Phase 2 complete (Camera working)
- [ ] 2026-01-11: Phase 3-4 complete (API + Vision)
- [ ] 2026-01-18: MVP complete (Phases 1-7)

**Actual Completion:**
- 

---

## 🔖 Session Notes

**2025-12-14 - Initial Setup**
- Created config system with Claude
- Decided on architecture
- Got all files packaged up
- Ready to start implementation

**[DATE] - [What you worked on]**
- 
- 
- 

---

## 🆘 Help Needed From Claude

**Next time we chat, I need help with:**
1. Deploying config service to k8s (ArgoCD vs kubectl)
2. Database schema design for wopr_main
3. 

**Questions to ask:**
- 
- 

---

## 🎓 Things I Learned

- Database-backed config is way more flexible than files
- Celery isn't as scary as it sounds
- 

---

## Usage Instructions

**How to update this file:**
1. Update "Last Updated" date at top
2. Move completed items from "Current Focus" to "Recently Completed"
3. Check off boxes as you complete tasks
4. Add new blockers/questions as they come up
5. Update stats (services deployed, etc.)
6. Add session notes each time you work on WOPR

**How to use with Claude:**
- Upload this file at start of conversation
- Or paste the relevant sections (Current Focus, Blockers, Next Steps)
- I'll know exactly where you are without re-explaining everything