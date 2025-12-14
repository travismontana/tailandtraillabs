from wopr.config import get_config
from wopr.logging import setup_logging

config = get_config()
logger = setup_logging("wopr-api", config=config)

# Use config throughout
app = FastAPI()

@app.post("/games/{game_id}/captures")
async def create_capture(game_id: str):
    # Camera URL from config
    camera_url = config.api.camera_service_url
    
    # Timeout from config
    timeout = config.api.camera_timeout_seconds
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{camera_url}/capture", ...)
    
    return response