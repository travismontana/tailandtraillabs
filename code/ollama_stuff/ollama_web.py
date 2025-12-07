#!/usr/bin/env python3
"""
ollama_web.py - Web interface for ollama_chat

Usage:
    ./ollama_web.py --host 0.0.0.0 --port 8080
    ./ollama_web.py --config ~/.ollama_chat.yaml
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import argparse
import json
import requests
import base64
import shutil
import uvicorn
import re
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

# Configuration defaults
DEFAULT_OLLAMA_HOST = "groth.abode.tailandtraillabs.org:11434"
DEFAULT_MODEL = "qwen2-vl:7b"
DEFAULT_HISTORY_COUNT = 10
DEFAULT_TIMEOUT = 120
CONVERSATIONS_DIR = Path("/data/twat/conversations")
UPLOADS_DIR = Path("/data/twat/uploads")
PROMPTS_DIR = Path("/data/twat/prompts")
TEMP_DIR = Path("/tmp/ollama_web")

# Create necessary directories
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# FastAPI app
app = FastAPI(title="Ollama Web Interface")

# Templates
templates = Jinja2Templates(directory="templates")

# Pydantic models for API
class ChatRequest(BaseModel):
    convo_id: str
    prompt: str
    model: str
    history_count: int = 10
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    json_extract: bool = False
    validate_json: bool = False
    image_ids: List[str] = []

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    tokens_estimate: int

class ConversationListItem(BaseModel):
    id: str
    message_count: int
    last_updated: str

class ModelInfo(BaseModel):
    name: str
    size_gb: float
    modified_at: str

class PromptTemplate(BaseModel):
    id: str
    name: str
    content: str
    description: Optional[str] = None

# Helper functions
def estimate_tokens(text: str) -> int:
    """Rough token estimation"""
    return len(text) // 4

def extract_json(text: str) -> str:
    """Extract JSON from response"""
    import re
    json_block = re.search(r'```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```', text)
    if json_block:
        return json_block.group(1).strip()
    
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if json_match:
        return json_match.group(1).strip()
    
    return text

class ConversationManager:
    """Manages conversation history and Ollama interactions"""
    
    def __init__(
        self,
        convo_id: str,
        model: str,
        ollama_host: str,
        history_count: int = 10,
        timeout: int = 120,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ):
        self.convo_id = convo_id
        self.model = model
        self.ollama_url = f"http://{ollama_host}/api/generate"
        self.ollama_host = ollama_host
        self.history_count = history_count
        self.timeout = timeout
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.history_file = CONVERSATIONS_DIR / f"{convo_id}.json"
    
    def load_history(self) -> str:
        """Load conversation history"""
        if not self.history_file.exists():
            return ""
        
        with open(self.history_file, 'r') as f:
            history = json.load(f)
        
        recent = history[-self.history_count:] if self.history_count > 0 else []
        
        if not recent:
            return ""
        
        context = "Previous conversation:\n"
        for exchange in recent:
            context += f"\nUser: {exchange['prompt']}\n"
            context += f"Assistant: {exchange['response']}\n"
        
        return context
    
    def save_interaction(self, prompt: str, response: str, had_images: int = 0):
        """Save interaction to history"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        history.append({
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'response': response,
            'model': self.model,
            'had_images': had_images
        })
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def ask(self, prompt: str, image_paths: Optional[List[Path]] = None) -> str:
        """Send request to Ollama"""
        history_context = self.load_history()
        
        full_prompt = ""
        if self.system_prompt:
            full_prompt += f"System: {self.system_prompt}\n\n"
        
        if history_context:
            full_prompt += f"{history_context}\n\n"
        
        full_prompt += f"User: {prompt}\nAssistant:"
        
        payload = {
            'model': self.model,
            'prompt': full_prompt,
            'stream': False
        }
        
        if self.temperature is not None:
            payload['options'] = {'temperature': self.temperature}
        
        if image_paths:
            images = []
            for image_path in image_paths:
                with open(image_path, 'rb') as img:
                    encoded = base64.b64encode(img.read()).decode()
                    images.append(encoded)
            payload['images'] = images
        
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            ai_response = result['response']
            
            self.save_interaction(prompt, ai_response, had_images=len(image_paths) if image_paths else 0)
            
            return ai_response
            
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Ollama request failed: {e}")

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/models")
async def list_models(host: str = DEFAULT_OLLAMA_HOST) -> List[ModelInfo]:
    """Get list of available models from Ollama"""
    url = f"http://{host}/api/tags"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        models = response.json().get('models', [])
        
        return [
            ModelInfo(
                name=m.get('name', 'unknown'),
                size_gb=m.get('size', 0) / (1024**3),
                modified_at=m.get('modified_at', 'unknown')
            )
            for m in models
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")

@app.get("/api/conversations")
async def list_conversations() -> List[ConversationListItem]:
    """Get list of all conversations"""
    convos = []
    
    for convo_file in sorted(CONVERSATIONS_DIR.glob("*.json")):
        try:
            with open(convo_file, 'r') as f:
                history = json.load(f)
            
            convos.append(ConversationListItem(
                id=convo_file.stem,
                message_count=len(history),
                last_updated=history[-1]['timestamp'] if history else "unknown"
            ))
        except Exception:
            continue
    
    return convos

@app.get("/api/conversations/{convo_id}")
async def get_conversation(convo_id: str):
    """Get conversation history"""
    history_file = CONVERSATIONS_DIR / f"{convo_id}.json"
    
    if not history_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    with open(history_file, 'r') as f:
        history = json.load(f)
    
    return {"id": convo_id, "history": history}

@app.delete("/api/conversations/{convo_id}")
async def delete_conversation(convo_id: str):
    """Delete a conversation"""
    history_file = CONVERSATIONS_DIR / f"{convo_id}.json"
    
    if history_file.exists():
        history_file.unlink()
        return {"status": "deleted", "id": convo_id}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")

@app.get("/api/prompts")
async def list_prompts() -> List[PromptTemplate]:
    """Get list of available prompt templates"""
    prompts = []
    
    for prompt_file in sorted(PROMPTS_DIR.glob("*.txt")):
        try:
            content = prompt_file.read_text().strip()
            
            # Try to extract name and description from first lines if they're comments
            lines = content.split('\n')
            name = prompt_file.stem.replace('_', ' ').title()
            description = None
            actual_content = content
            
            # If first line starts with #, use it as name
            if lines[0].startswith('# '):
                name = lines[0][2:].strip()
                # If second line starts with #, use it as description
                if len(lines) > 1 and lines[1].startswith('# '):
                    description = lines[1][2:].strip()
                    actual_content = '\n'.join(lines[2:]).strip()
                else:
                    actual_content = '\n'.join(lines[1:]).strip()
            
            prompts.append(PromptTemplate(
                id=prompt_file.stem,
                name=name,
                content=actual_content,
                description=description
            ))
        except Exception as e:
            print(f"Error reading prompt {prompt_file}: {e}")
            continue
    
    return prompts

@app.get("/api/prompts/{prompt_id}")
async def get_prompt(prompt_id: str) -> PromptTemplate:
    """Get a specific prompt template"""
    prompt_file = PROMPTS_DIR / f"{prompt_id}.txt"
    
    if not prompt_file.exists():
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    try:
        content = prompt_file.read_text().strip()
        lines = content.split('\n')
        name = prompt_id.replace('_', ' ').title()
        description = None
        actual_content = content
        
        if lines[0].startswith('# '):
            name = lines[0][2:].strip()
            if len(lines) > 1 and lines[1].startswith('# '):
                description = lines[1][2:].strip()
                actual_content = '\n'.join(lines[2:]).strip()
            else:
                actual_content = '\n'.join(lines[1:]).strip()
        
        return PromptTemplate(
            id=prompt_id,
            name=name,
            content=actual_content,
            description=description
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prompts")
async def save_prompt(
    prompt_id: str = Form(...),
    name: str = Form(...),
    content: str = Form(...),
    description: Optional[str] = Form(None)
):
    """Save a new prompt template"""
    # Sanitize prompt_id
    if not re.match(r'^[a-zA-Z0-9_-]+$', prompt_id):
        raise HTTPException(400, "Invalid prompt ID")
    
    prompt_file = PROMPTS_DIR / f"{prompt_id}.txt"
    
    # Build file content with metadata
    file_content = f"# {name}\n"
    if description:
        file_content += f"# {description}\n"
    file_content += content
    
    prompt_file.write_text(file_content)
    
    return {"status": "saved", "id": prompt_id}

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt template"""
    prompt_file = PROMPTS_DIR / f"{prompt_id}.txt"
    
    if prompt_file.exists():
        prompt_file.unlink()
        return {"status": "deleted", "id": prompt_id}
    else:
        raise HTTPException(status_code=404, detail="Prompt not found")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload an image or file"""
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = Path(file.filename).suffix
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = UPLOADS_DIR / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "file_id": unique_filename,
        "filename": file.filename,
        "path": str(file_path),
        "size": file_path.stat().st_size
    }

@app.post("/api/chat")
async def chat(
    convo_id: str = Form(...),
    prompt: str = Form(...),
    model: str = Form(...),
    ollama_host: str = Form(DEFAULT_OLLAMA_HOST),
    history_count: int = Form(10),
    temperature: Optional[float] = Form(None),
    system_prompt: Optional[str] = Form(None),
    json_extract: bool = Form(False),
    validate_json: bool = Form(False),
    file_ids: str = Form("")  # Comma-separated file IDs
) -> ChatResponse:
    """Send a chat message"""
    
    # Parse file IDs
    image_paths = []
    if file_ids:
        for file_id in file_ids.split(','):
            file_id = file_id.strip()
            if file_id:
                file_path = UPLOADS_DIR / file_id
                if file_path.exists():
                    image_paths.append(file_path)
    
    # Create conversation manager
    manager = ConversationManager(
        convo_id=convo_id,
        model=model,
        ollama_host=ollama_host,
        history_count=history_count,
        timeout=DEFAULT_TIMEOUT,
        temperature=temperature,
        system_prompt=system_prompt
    )
    
    # Get response
    try:
        response = manager.ask(prompt, image_paths or None)
        
        # Extract JSON if requested
        if json_extract:
            response = extract_json(response)
        
        # Validate JSON if requested
        if validate_json:
            try:
                json.loads(response)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        
        return ChatResponse(
            response=response,
            timestamp=datetime.now().isoformat(),
            tokens_estimate=estimate_tokens(response)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def main():
    # Update global default
    global DEFAULT_OLLAMA_HOST
    
    parser = argparse.ArgumentParser(description='Ollama Web Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--ollama-host', default=DEFAULT_OLLAMA_HOST, help='Default Ollama host')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    
    args = parser.parse_args()
    DEFAULT_OLLAMA_HOST = args.ollama_host

    print(f"Starting Ollama Web Interface on {args.host}:{args.port}")
    print(f"Default Ollama host: {DEFAULT_OLLAMA_HOST}")
    print(f"Conversations directory: {CONVERSATIONS_DIR}")
    print(f"Uploads directory: {UPLOADS_DIR}")
    print(f"Prompts directory: {PROMPTS_DIR}")
    
    uvicorn.run(
        "ollama_web:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == '__main__':
    main()
