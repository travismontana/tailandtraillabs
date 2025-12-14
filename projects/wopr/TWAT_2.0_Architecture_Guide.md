# TWAT 2.0 - System Architecture & Implementation Guide

**Project:** Tactical Wargaming Adjudication Tracker  
**Version:** 2.0 MVP  
**Date:** December 13, 2025  
**Author:** Bob

---

## Executive Summary

TWAT 2.0 is a computer vision-based board game tracking system that captures, analyzes, and tracks game state for tabletop games like Dune Imperium and Star Wars Legion. The MVP focuses on user-initiated image capture via web interface, automated vision analysis using local AI models, and basic game state management.

## System Architecture

### High-Level Component Diagram

```
User Devices (iPad/Phone/Desktop)
         |
         | HTTPS
         v
    Ingress/LB (Traefik)
         |
    +----|----+
    |         |
    v         v
Frontend   Backend API
(React)    (FastAPI)
             |
    +--------|--------+
    |        |        |
    v        v        v
PostgreSQL NAS    Camera API
(State)   (Images)  (RPi)
                      |
                      v
                 RPi Camera
                 Module 3

Vision Processing (Desktop - 4080 Super):
  - Ollama (Qwen2-VL)
  - OpenCV (Change Detection)
  - YOLO (Future - Custom Models)
```

### Technology Stack

**Infrastructure:**
- Kubernetes: k3s clusters
- GitOps: ArgoCD
- Ingress: Traefik
- TLS: cert-manager + Let's Encrypt
- Storage: NFS to existing NAS

**Backend:**
- Framework: FastAPI (Python 3.11+)
- Database: PostgreSQL 16
- ORM: SQLAlchemy
- Validation: Pydantic v2

**Frontend:**
- Framework: React 18 or vanilla HTML/JS
- Build: Vite or Create React App
- State: React Context or Zustand

**Camera Capture:**
- Hardware: Raspberry Pi 4/5 + Camera Module 3 (12MP)
- Software: picamera2 library
- API: Flask or FastAPI
- Mount: 3D printed overhead arm

**Vision Processing:**
- VLM: Ollama + Qwen2-VL:7b (Alibaba)
- CV: OpenCV for change detection
- Custom: YOLOv8/v11 (future game-specific models)
- Hardware: NVIDIA 4080 Super (16GB VRAM)

---

## Data Models

### Game
```python
class Game:
    id: UUID
    name: str  # "Bob vs Alice - Dune Imperium"
    game_type: GameType  # Enum: dune_imperium, star_wars_legion
    status: GameStatus  # Enum: setup, in_progress, completed, abandoned
    created_at: datetime
    updated_at: datetime
    current_turn: int
    current_phase: str
    metadata: dict  # Game-specific flexible data
    
    # Relationships
    players: List[Player]
    captures: List[Capture]
    states: List[GameState]
```

### Player
```python
class Player:
    id: UUID
    game_id: UUID
    name: str
    position: int  # 1, 2, 3, etc.
    color: str  # "blue", "red" for piece identification
```

### Capture
```python
class Capture:
    id: UUID
    game_id: UUID
    sequence: int  # 0=initial setup, 1=first move, etc.
    image_path: str  # Relative to NAS mount
    thumbnail_path: str
    captured_at: datetime
    triggered_by: str  # user_id or "auto"
    analysis_status: AnalysisStatus  # pending, processing, completed, failed
    analysis_results: dict  # VLM output, changes detected, etc.
    notes: str  # User-provided context
```

### GameState
```python
class GameState:
    id: UUID
    game_id: UUID
    capture_id: UUID  # State derived from this capture
    turn: int
    phase: str
    board_state: dict  # Grid positions, piece locations
    resources: dict  # Player resources (spice, solari, etc.)
    detected_changes: dict  # What changed from previous state
    validation_notes: dict  # Rules engine output (future)
    created_at: datetime
```

---

## API Specification

**Base URL:** `https://twat.yourdomain.com/api/v1`

### Game Management Endpoints

#### Create Game
```http
POST /games

Request:
{
  "name": "Bob vs Alice - Dune Imperium",
  "game_type": "dune_imperium",
  "players": [
    {"name": "Bob", "position": 1, "color": "blue"},
    {"name": "Alice", "position": 2, "color": "red"}
  ]
}

Response: 201 Created
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Bob vs Alice - Dune Imperium",
  "game_type": "dune_imperium",
  "status": "setup",
  "created_at": "2025-12-13T10:00:00Z",
  "players": [...],
  "current_turn": 0
}
```

#### Get Game
```http
GET /games/{game_id}

Response: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Bob vs Alice - Dune Imperium",
  "status": "in_progress",
  "current_turn": 3,
  "captures": [...],
  "latest_state": {...}
}
```

#### List Games
```http
GET /games?status=in_progress&limit=10&offset=0

Response: 200 OK
{
  "games": [...],
  "total": 5,
  "page": 1,
  "page_size": 10
}
```

#### Update Game
```http
PATCH /games/{game_id}

Request:
{
  "status": "completed",
  "current_turn": 10
}

Response: 200 OK
```

#### Delete Game
```http
DELETE /games/{game_id}

Response: 204 No Content
```

### Capture Management Endpoints

#### Trigger Capture
```http
POST /games/{game_id}/captures

Request:
{
  "trigger_camera": true,
  "notes": "Initial board setup",
  "resolution": "4k"  # Optional: "4k", "1080p", "720p"
}

Response: 202 Accepted
{
  "capture_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "capturing",
  "image_url": null
}
```

#### Get Capture
```http
GET /games/{game_id}/captures/{capture_id}

Response: 200 OK
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "sequence": 0,
  "image_url": "/images/games/{game_id}/cap_0_20251213_100000.jpg",
  "thumbnail_url": "/images/games/{game_id}/thumb_0_20251213_100000.jpg",
  "captured_at": "2025-12-13T10:00:00Z",
  "analysis_status": "completed",
  "analysis_results": {
    "changed_regions": [...],
    "detected_pieces": [...],
    "confidence": 0.85
  }
}
```

#### List Captures
```http
GET /games/{game_id}/captures

Response: 200 OK
{
  "captures": [
    {"id": "...", "sequence": 0, "thumbnail_url": "..."},
    {"id": "...", "sequence": 1, "thumbnail_url": "..."}
  ]
}
```

#### Request Analysis
```http
POST /games/{game_id}/captures/{capture_id}/analyze

Request:
{
  "model": "qwen2-vl",  # Optional override
  "detect_changes": true,
  "identify_pieces": true
}

Response: 202 Accepted
{
  "status": "queued",
  "job_id": "analysis_123"
}
```

### State Management Endpoints

#### Get Current State
```http
GET /games/{game_id}/state

Response: 200 OK
{
  "current_turn": 3,
  "phase": "agent_placement",
  "board_state": {
    "grid": [[null, null, ...], [...]],
    "pieces": [
      {
        "type": "fremen_warrior",
        "player": 1,
        "position": {"x": 2, "y": 3}
      }
    ]
  },
  "resources": {
    "player_1": {"spice": 5, "water": 2, "solari": 3},
    "player_2": {"spice": 3, "water": 1, "solari": 5}
  }
}
```

#### Update State
```http
POST /games/{game_id}/state

Request:
{
  "turn": 3,
  "phase": "combat",
  "board_state": {...},
  "source": "manual"  # or "vision_analysis"
}

Response: 201 Created
```

### Camera Control Endpoints

#### Capture Image
```http
POST /camera/capture

Request:
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "resolution": "4k",
  "format": "jpeg"
}

Response: 200 OK
{
  "image_path": "/mnt/nas/twat/games/{game_id}/cap_3_20251213.jpg",
  "size_bytes": 8388608,
  "captured_at": "2025-12-13T10:00:00Z"
}
```

#### Get Camera Status
```http
GET /camera/status

Response: 200 OK
{
  "status": "ready",  # or "busy", "error"
  "last_capture": "2025-12-13T09:55:00Z",
  "available_resolutions": ["4k", "1080p", "720p"],
  "camera_model": "RPi Camera Module 3"
}
```

### Analysis Job Endpoints

#### Submit Analysis Job
```http
POST /analysis/vision

Request:
{
  "capture_id": "660e8400-e29b-41d4-a716-446655440001",
  "model": "qwen2-vl",
  "params": {
    "detect_changes": true,
    "identify_pieces": true,
    "compare_to_capture_id": "550e8400-..."
  }
}

Response: 202 Accepted
{
  "job_id": "analysis_456",
  "status": "queued",
  "estimated_duration": "10s"
}
```

#### Get Job Status
```http
GET /analysis/jobs/{job_id}

Response: 200 OK
{
  "job_id": "analysis_456",
  "status": "completed",  # queued, processing, completed, failed
  "created_at": "2025-12-13T10:00:00Z",
  "completed_at": "2025-12-13T10:00:12Z",
  "results": {...},
  "error": null
}
```

---

## User Interaction Flows

### Flow 1: Create Game & Initial Setup

1. **User opens web app on iPad**
   - Frontend loads game list

2. **User clicks "New Game"**
   - Form appears: Game name, type (dropdown), player names/colors

3. **User submits form**
   - Frontend → API: `POST /games`
   - API creates Game record, status="setup"
   - Response redirects to `/games/{id}`

4. **User sees game page**
   - Empty capture gallery
   - "Capture Initial Setup" button prominent
   - Game info displayed

5. **User clicks "Capture Initial Setup"**
   - Frontend → API: `POST /games/{id}/captures?trigger_camera=true`
   - API → Camera Service: `POST /camera/capture`
   - Camera Service:
     - Triggers RPi picamera2.capture()
     - Writes to NFS: `/mnt/nas/twat/games/{id}/cap_0_{timestamp}.jpg`
     - Generates thumbnail (480px width)
     - Returns image_path
   - API:
     - Creates Capture record (sequence=0, analysis_status="pending")
     - Returns 202 Accepted with capture_id

6. **Frontend polls for capture completion**
   - `GET /games/{id}/captures/{capture_id}` every 2 seconds
   - Once image_url populated, display thumbnail
   - Show "Analysis queued..." message

7. **Background: Vision Analysis**
   - API background worker picks up pending capture
   - Calls Ollama: `POST http://desktop:11434/api/generate`
     - Model: qwen2-vl:7b
     - Prompt: "Describe this Dune Imperium board setup. Identify all visible pieces, their colors, and positions."
   - Ollama processes (8-15 seconds)
   - Returns analysis results
   - API updates Capture.analysis_results, analysis_status="completed"
   - Creates initial GameState record

8. **Frontend receives update**
   - Next poll returns analysis_status="completed"
   - Displays: "Analysis complete"
   - Shows detected pieces summary
   - User can review, correct if needed

### Flow 2: Mid-Game Move Capture

1. **User makes move on physical board**

2. **User clicks "Capture Move" in web UI**
   - Frontend → API: `POST /games/{id}/captures`

3. **Camera capture**
   - Same as Flow 1, but sequence increments
   - New image: `cap_3_{timestamp}.jpg`

4. **Change detection (OpenCV)**
   - API retrieves previous capture image (sequence=2)
   - Runs OpenCV diff:
     ```python
     gray1 = cv2.cvtColor(img_prev, cv2.COLOR_BGR2GRAY)
     gray2 = cv2.cvtColor(img_new, cv2.COLOR_BGR2GRAY)
     diff = cv2.absdiff(gray1, gray2)
     _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
     contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
     changed_regions = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 1000]
     ```
   - Identifies bounding boxes of changed regions

5. **Targeted VLM analysis**
   - API → Ollama with focused prompt:
     - "These regions changed: [(x, y, w, h), ...]. What pieces moved? What changed?"
   - Ollama returns: "Blue fremen warrior moved from space E4 to F5"

6. **State update**
   - API updates GameState:
     - Updates board_state.pieces positions
     - Increments turn counter
     - Records detected_changes

7. **Rules validation (future)**
   - Rules engine checks move legality
   - Adds validation_notes to GameState

8. **Frontend update**
   - Displays new capture thumbnail
   - Shows move description: "Blue fremen: E4 → F5"
   - Highlights validation warnings if any

### Flow 3: Game History Review

1. **User clicks "History" tab**
   - Frontend → API: `GET /games/{id}/captures`

2. **API returns capture list**
   - All captures with thumbnails, ordered by sequence

3. **Frontend displays timeline**
   - Horizontal scrollable gallery of thumbnails
   - Labels: "Setup", "Turn 1", "Turn 2", etc.

4. **User clicks thumbnail**
   - Frontend → API: `GET /games/{id}/captures/{cap_id}`
   - Displays full-size image
   - Shows analysis results
   - Shows game state at that point in time

5. **User can navigate**
   - Previous/Next buttons
   - Jump to specific turn
   - Compare side-by-side

---

## Component Implementation Details

### Backend (FastAPI)

#### Directory Structure
```
/app
├── main.py                 # FastAPI app, CORS, middleware
├── config.py              # Settings (Pydantic BaseSettings)
├── db.py                  # Database session, engine
├── dependencies.py        # Common dependencies (DB session, auth)
│
├── models/                # SQLAlchemy ORM models
│   ├── __init__.py
│   ├── game.py
│   ├── player.py
│   ├── capture.py
│   └── state.py
│
├── schemas/               # Pydantic request/response schemas
│   ├── __init__.py
│   ├── game.py
│   ├── player.py
│   ├── capture.py
│   └── state.py
│
├── routers/               # API route handlers
│   ├── __init__.py
│   ├── games.py
│   ├── captures.py
│   ├── camera.py
│   ├── analysis.py
│   └── health.py
│
├── services/              # Business logic
│   ├── __init__.py
│   ├── camera.py          # RPi camera client
│   ├── vision.py          # Ollama/OpenCV integration
│   ├── storage.py         # NAS/image handling
│   ├── thumbnail.py       # Image processing
│   └── rules.py           # Game rules engine (future)
│
└── workers/               # Background tasks
    ├── __init__.py
    └── analysis.py        # Vision analysis worker
```

#### Key Dependencies (requirements.txt)
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
aiofiles==23.2.1
httpx==0.26.0
pillow==10.2.0
opencv-python==4.9.0.80
numpy==1.26.3
celery==5.3.6
redis==5.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

#### Example: Game Router
```python
# app/routers/games.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app import models, schemas
from app.dependencies import get_db

router = APIRouter(prefix="/games", tags=["games"])

@router.post("/", response_model=schemas.Game, status_code=201)
def create_game(
    game: schemas.GameCreate,
    db: Session = Depends(get_db)
):
    db_game = models.Game(
        name=game.name,
        game_type=game.game_type,
        status="setup"
    )
    db.add(db_game)
    db.flush()
    
    # Create players
    for player_data in game.players:
        player = models.Player(
            game_id=db_game.id,
            **player_data.dict()
        )
        db.add(player)
    
    db.commit()
    db.refresh(db_game)
    return db_game

@router.get("/{game_id}", response_model=schemas.Game)
def get_game(
    game_id: UUID,
    db: Session = Depends(get_db)
):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@router.get("/", response_model=List[schemas.Game])
def list_games(
    status: str = None,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(models.Game)
    if status:
        query = query.filter(models.Game.status == status)
    games = query.offset(offset).limit(limit).all()
    return games
```

#### Example: Vision Service
```python
# app/services/vision.py
import httpx
import cv2
import numpy as np
from typing import Dict, List, Tuple
from app.config import settings

class VisionService:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL
    
    async def analyze_image(
        self,
        image_path: str,
        prompt: str = None
    ) -> Dict:
        """Send image to Ollama VLM for analysis"""
        
        # Read and encode image
        with open(image_path, 'rb') as f:
            import base64
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Default prompt if none provided
        if not prompt:
            prompt = (
                "Analyze this board game image. "
                "Identify all visible game pieces, their colors, "
                "and their positions on the board."
            )
        
        # Call Ollama API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                }
            )
            response.raise_for_status()
            result = response.json()
        
        return {
            "model": self.model,
            "response": result['response'],
            "confidence": 0.85  # Placeholder, VLMs don't return confidence
        }
    
    def detect_changes(
        self,
        image1_path: str,
        image2_path: str,
        threshold: int = 30
    ) -> List[Tuple[int, int, int, int]]:
        """Detect changed regions between two images using OpenCV"""
        
        # Load images
        img1 = cv2.imread(image1_path)
        img2 = cv2.imread(image2_path)
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Blur to reduce noise
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
        
        # Compute difference
        diff = cv2.absdiff(gray1, gray2)
        
        # Threshold
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        
        # Morphological operations
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=2)
        thresh = cv2.erode(thresh, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Extract bounding boxes for significant changes
        changed_regions = []
        for contour in contours:
            if cv2.contourArea(contour) > 1000:  # Min area threshold
                x, y, w, h = cv2.boundingRect(contour)
                changed_regions.append((x, y, w, h))
        
        return changed_regions
```

### Frontend (React)

#### Component Structure
```
/src
├── App.jsx
├── index.jsx
├── api.js                 # API client
├── config.js             # Environment config
│
├── components/
│   ├── GameList.jsx
│   ├── GameCard.jsx
│   ├── GameView.jsx
│   ├── CaptureButton.jsx
│   ├── CaptureGallery.jsx
│   ├── BoardState.jsx
│   ├── PlayerResources.jsx
│   └── GameHistory.jsx
│
├── hooks/
│   ├── useGame.js
│   ├── useCaptures.js
│   └── usePolling.js
│
├── contexts/
│   └── GameContext.jsx
│
└── styles/
    └── main.css
```

#### Example: GameView Component
```javascript
// src/components/GameView.jsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api';
import CaptureButton from './CaptureButton';
import CaptureGallery from './CaptureGallery';
import BoardState from './BoardState';

function GameView() {
  const { gameId } = useParams();
  const [game, setGame] = useState(null);
  const [captures, setCaptures] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadGame();
    loadCaptures();
  }, [gameId]);
  
  const loadGame = async () => {
    try {
      const data = await api.getGame(gameId);
      setGame(data);
    } catch (error) {
      console.error('Failed to load game:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const loadCaptures = async () => {
    try {
      const data = await api.listCaptures(gameId);
      setCaptures(data.captures);
    } catch (error) {
      console.error('Failed to load captures:', error);
    }
  };
  
  const handleCaptureComplete = (newCapture) => {
    setCaptures([...captures, newCapture]);
    loadGame(); // Refresh game state
  };
  
  if (loading) return <div>Loading...</div>;
  if (!game) return <div>Game not found</div>;
  
  return (
    <div className="game-view">
      <header>
        <h1>{game.name}</h1>
        <div className="game-meta">
          <span>Turn {game.current_turn}</span>
          <span>Phase: {game.current_phase}</span>
          <span className={`status ${game.status}`}>{game.status}</span>
        </div>
      </header>
      
      <div className="game-content">
        <div className="capture-section">
          <CaptureButton 
            gameId={gameId} 
            onComplete={handleCaptureComplete}
          />
          <CaptureGallery captures={captures} />
        </div>
        
        <div className="state-section">
          <BoardState gameId={gameId} />
        </div>
      </div>
    </div>
  );
}

export default GameView;
```

#### Example: API Client
```javascript
// src/api.js
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };
    
    const response = await fetch(url, config);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }
    
    return response.json();
  }
  
  // Game endpoints
  createGame(data) {
    return this.request('/games', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  getGame(gameId) {
    return this.request(`/games/${gameId}`);
  }
  
  listGames(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/games?${query}`);
  }
  
  // Capture endpoints
  createCapture(gameId, data = {}) {
    return this.request(`/games/${gameId}/captures`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  getCapture(gameId, captureId) {
    return this.request(`/games/${gameId}/captures/${captureId}`);
  }
  
  listCaptures(gameId) {
    return this.request(`/games/${gameId}/captures`);
  }
}

export default new ApiClient();
```

### Camera Service (Raspberry Pi)

#### Implementation
```python
# /opt/twat-camera/app.py
from flask import Flask, request, jsonify
from picamera2 import Picamera2
import os
import time
from pathlib import Path

app = Flask(__name__)
picam = Picamera2()

NAS_MOUNT = "/mnt/nas/twat"

RESOLUTIONS = {
    '4k': (4608, 2592),
    '1080p': (1920, 1080),
    '720p': (1280, 720)
}

@app.route('/capture', methods=['POST'])
def capture():
    data = request.json
    game_id = data['game_id']
    resolution = data.get('resolution', '4k')
    
    # Validate resolution
    if resolution not in RESOLUTIONS:
        return jsonify({'error': 'Invalid resolution'}), 400
    
    # Configure camera
    size = RESOLUTIONS[resolution]
    config = picam.create_still_configuration(
        main={"size": size},
        buffer_count=2
    )
    picam.configure(config)
    
    # Generate paths
    timestamp = int(time.time())
    game_dir = Path(NAS_MOUNT) / 'games' / game_id
    game_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"cap_{timestamp}.jpg"
    filepath = game_dir / filename
    
    try:
        # Capture image
        picam.start()
        time.sleep(2)  # Let camera adjust
        picam.capture_file(str(filepath))
        picam.stop()
        
        # Get file stats
        file_size = filepath.stat().st_size
        
        return jsonify({
            'image_path': str(filepath.relative_to(NAS_MOUNT)),
            'size_bytes': file_size,
            'captured_at': timestamp,
            'resolution': resolution
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'ready',
        'camera_model': 'RPi Camera Module 3',
        'available_resolutions': list(RESOLUTIONS.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

#### Systemd Service
```ini
# /etc/systemd/system/twat-camera.service
[Unit]
Description=TWAT Camera Service
After=network.target nfs-client.target
Requires=nfs-client.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/twat-camera
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 /opt/twat-camera/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### NFS Mount Configuration
```bash
# /etc/fstab entry on RPi
nas.yourdomain.com:/volume1/twat  /mnt/nas/twat  nfs  defaults,_netdev  0  0
```

---

## Kubernetes Deployment

### Namespace
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: twat
  labels:
    name: twat
```

### Backend Deployment
```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twat-backend
  namespace: twat
  labels:
    app: twat-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: twat-backend
  template:
    metadata:
      labels:
        app: twat-backend
    spec:
      containers:
      - name: api
        image: registry.yourdomain.com/twat-backend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: twat-db-creds
              key: url
        - name: NAS_MOUNT_PATH
          value: /mnt/nas/twat
        - name: OLLAMA_URL
          value: http://desktop.yourdomain.com:11434
        - name: CAMERA_URL
          value: http://raspberrypi.local:5000
        - name: PYTHONUNBUFFERED
          value: "1"
        volumeMounts:
        - name: nas-storage
          mountPath: /mnt/nas/twat
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: nas-storage
        nfs:
          server: nas.yourdomain.com
          path: /volume1/twat
---
apiVersion: v1
kind: Service
metadata:
  name: twat-backend
  namespace: twat
spec:
  selector:
    app: twat-backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
```

### Frontend Deployment
```yaml
# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twat-frontend
  namespace: twat
  labels:
    app: twat-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: twat-frontend
  template:
    metadata:
      labels:
        app: twat-frontend
    spec:
      containers:
      - name: nginx
        image: registry.yourdomain.com/twat-frontend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 80
          name: http
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: twat-frontend
  namespace: twat
spec:
  selector:
    app: twat-frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
```

### Database StatefulSet
```yaml
# postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: twat-db
  namespace: twat
spec:
  serviceName: twat-db
  replicas: 1
  selector:
    matchLabels:
      app: twat-db
  template:
    metadata:
      labels:
        app: twat-db
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          value: twat
        - name: POSTGRES_USER
          value: twat
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: twat-db-creds
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: db-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: db-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: local-path
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: twat-db
  namespace: twat
spec:
  selector:
    app: twat-db
  ports:
  - protocol: TCP
    port: 5432
    targetPort: 5432
  clusterIP: None
```

### Ingress
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: twat-ingress
  namespace: twat
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.middlewares: default-redirect-https@kubernetescrd
spec:
  ingressClassName: traefik
  tls:
  - hosts:
    - twat.yourdomain.com
    secretName: twat-tls
  rules:
  - host: twat.yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: twat-backend
            port:
              number: 8000
      - path: /images
        pathType: Prefix
        backend:
          service:
            name: twat-backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: twat-frontend
            port:
              number: 80
```

---

## GitOps Repository Structure

```
/repos/twat-gitops/
├── README.md
├── applications/
│   └── twat.yaml              # ArgoCD Application manifest
│
├── base/
│   ├── namespace.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── kustomization.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── kustomization.yaml
│   ├── database/
│   │   ├── statefulset.yaml
│   │   ├── service.yaml
│   │   └── kustomization.yaml
│   └── ingress/
│       ├── ingress.yaml
│       └── kustomization.yaml
│
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   ├── backend-patch.yaml
│   │   └── ingress-patch.yaml
│   └── prod/
│       ├── kustomization.yaml
│       ├── backend-patch.yaml
│       ├── ingress-patch.yaml
│       └── sealed-secrets.yaml
│
└── scripts/
    ├── deploy-dev.sh
    └── deploy-prod.sh
```

### ArgoCD Application
```yaml
# applications/twat.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: twat
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://gitlab.yourdomain.com/bob/twat-gitops.git
    targetRevision: main
    path: overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: twat
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

---

## Configuration Management

### Backend Environment Variables
```bash
# Database
DATABASE_URL=postgresql://twat:password@twat-db:5432/twat

# Storage
NAS_MOUNT_PATH=/mnt/nas/twat
IMAGE_BASE_URL=https://twat.yourdomain.com/images

# External Services
OLLAMA_URL=http://desktop.yourdomain.com:11434
CAMERA_URL=http://raspberrypi.local:5000

# Vision Configuration
OLLAMA_MODEL=qwen2-vl:7b
OPENCV_CHANGE_THRESHOLD=30
MIN_CHANGE_AREA=1000

# API Configuration
API_CORS_ORIGINS=https://twat.yourdomain.com,http://localhost:3000
API_KEY=generate-secure-api-key-here
LOG_LEVEL=INFO

# Workers
CELERY_BROKER_URL=redis://twat-redis:6379/0
CELERY_RESULT_BACKEND=redis://twat-redis:6379/0
```

---

## MVP Roadmap

### Week 1-2: Hardware & Infrastructure
- [ ] Order RPi Camera Module 3
- [ ] 3D print camera mount
- [ ] Setup RPi with camera service
- [ ] Configure NFS mount on RPi
- [ ] Test capture to NAS

### Week 2-3: Backend Development
- [ ] Scaffold FastAPI project
- [ ] Database models & migrations
- [ ] Game CRUD endpoints
- [ ] Capture endpoints
- [ ] Camera service client
- [ ] Celery workers

### Week 3-4: Frontend Development
- [ ] React project setup
- [ ] Game list & create
- [ ] Game view with capture
- [ ] Capture gallery
- [ ] Polling for updates

### Week 4-5: Vision Integration
- [ ] Setup Ollama on desktop
- [ ] Test Qwen2-VL
- [ ] OpenCV change detection
- [ ] Vision service integration
- [ ] Analysis worker queue

### Week 5-6: Testing & Deployment
- [ ] End-to-end testing
- [ ] K8s manifests
- [ ] ArgoCD config
- [ ] Deploy to cluster
- [ ] Monitoring & alerts

---

## Hardware Bill of Materials

**Minimum Setup:**
- Raspberry Pi 4 (4GB) or Pi 5: $55-75
- RPi Camera Module 3: $25
- MicroSD card (64GB): $10
- Power supply: $10
- Camera mount (3D printed): $5
- **Total: ~$105-125**

---

**Document Version:** 1.0  
**Last Updated:** December 13, 2025
