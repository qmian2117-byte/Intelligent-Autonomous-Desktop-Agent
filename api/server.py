"""
FastAPI Server Gateway for DesktopPilot AI.
Exposes RESTful endpoints and real-time WebSockets for the desktop client.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from config.settings import settings
from api.routes.agent_routes import router as agent_router
from api.routes.chat_routes import chat_router
from api.websocket.stream import telemetry_manager
from database.session import init_db
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown hooks."""
    logger.info("Initializing DesktopPilot AI backend...")
    # Initialize database tables
    try:
        await init_db()
        logger.info("Database schema initialized.")
    except Exception as e:
        logger.warning(f"Database initialization warning (aiosqlite): {e}")

    yield

    logger.info("Shutting down DesktopPilot AI backend...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous local AI Desktop Automation Agent powered by LangGraph & Ollama.",
    lifespan=lifespan
)

# Configure CORS restricted to local desktop clients (Web UI, Electron, Tauri, Localhost)
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include agent & chat routes
app.include_router(agent_router)
app.include_router(chat_router)


# Real-time Telemetry WebSocket
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Real-time streaming channel for live task logs, screenshots, and agent state."""
    await telemetry_manager.connect(websocket)
    try:
        while True:
            # Keep connection open, receive ping/client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        telemetry_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket session error: {e}")
        telemetry_manager.disconnect(websocket)


# Mount frontend static files (HTML, CSS, JS)
FRONTEND_DIR = Path("frontend")
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="127.0.0.1", port=8000, reload=True)

