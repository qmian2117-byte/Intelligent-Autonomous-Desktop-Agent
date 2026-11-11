"""
Unified launcher for DesktopPilot AI Backend & Control Dashboard.
Executes pre-flight checks and launches the server.
"""

import sys
import time
import webbrowser
import uvicorn
from config.settings import settings
from utils.logger import logger


def main():
    print("=" * 65)
    print(f"🚀 Launching {settings.APP_NAME} (v{settings.APP_VERSION})")
    print("=" * 65)
    print(f"• Host:              http://{settings.HOST}:{settings.PORT}")
    print(f"• Dashboard UI:      http://{settings.HOST}:{settings.PORT}/")
    print(f"• Swagger API Docs:  http://{settings.HOST}:{settings.PORT}/docs")
    print(f"• Target Model:      {settings.LLM_MODEL} (Local Ollama)")
    print(f"• Ollama Endpoint:   {settings.OLLAMA_BASE_URL}")
    print("=" * 65)

    # Optional: auto-open browser after 1 second delay
    import threading
    def open_browser():
        time.sleep(1.2)
        webbrowser.open(f"http://{settings.HOST}:{settings.PORT}/")

    threading.Thread(target=open_browser, daemon=True).start()

    # Start Uvicorn server
    uvicorn.run(
        "api.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )


if __name__ == "__main__":
    main()
