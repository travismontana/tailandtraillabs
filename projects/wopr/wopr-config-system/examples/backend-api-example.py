#!/usr/bin/env python3
"""
Example Backend API using WOPR Config System
"""
from fastapi import FastAPI, HTTPException
import httpx
from wopr.config import init_config, get_str, get_int
from wopr.logging import setup_logging

app = FastAPI(title="WOPR Backend API Example")

# Setup logging
logger = setup_logging("wopr-api")


@app.on_event("startup")
async def startup():
    """Initialize config on startup"""
    init_config()
    logger.info("Config initialized")
    logger.info(f"Camera URL: {get_str('api.camera_service_url')}")
    logger.info(f"Ollama URL: {get_str('api.ollama_url')}")


@app.get("/config/test")
async def test_config():
    """Test endpoint to verify config access"""
    return {
        "storage_base_path": get_str('storage.base_path'),
        "camera_resolution": get_str('camera.default_resolution'),
        "log_level": get_str('logging.default_level'),
        "ollama_url": get_str('api.ollama_url')
    }


@app.post("/games/{game_id}/captures")
async def create_capture(game_id: str):
    """
    Trigger camera capture for a game.
    Uses config service for all settings.
    """
    logger.info(f"Capture requested for game: {game_id}")
    
    # Get camera service URL from config
    camera_url = get_str('api.camera_service_url')
    timeout = get_int('api.camera_timeout_seconds')
    
    logger.info(f"Calling camera service: {camera_url}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{camera_url}/capture",
                json={"game_id": game_id, "subject": "capture"}
            )
            response.raise_for_status()
            
        logger.info(f"Capture successful for game {game_id}")
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"Camera service error: {e}")
        raise HTTPException(status_code=503, detail="Camera service unavailable")


@app.post("/analysis/submit")
async def submit_analysis(image_path: str):
    """
    Submit image for analysis to Ollama.
    Uses config service for Ollama URL and settings.
    """
    ollama_url = get_str('api.ollama_url')
    model = get_str('vision.default_model')
    timeout = get_int('api.ollama_timeout_seconds')
    
    logger.info(f"Submitting analysis: {image_path}")
    logger.info(f"Using model: {model} at {ollama_url}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"Analyze this board game image: {image_path}"
                }
            )
            response.raise_for_status()
            
        logger.info("Analysis completed")
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"Ollama service error: {e}")
        raise HTTPException(status_code=503, detail="Vision service unavailable")


if __name__ == '__main__':
    import uvicorn
    
    # Get host and port from config
    init_config()
    host = get_str('api.host')
    port = get_int('api.port')
    
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
