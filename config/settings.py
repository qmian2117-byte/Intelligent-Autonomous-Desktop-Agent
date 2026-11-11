"""
Configuration settings for DesktopPilot AI.
Strictly local inference with Ollama and Llama 3.1 8B.
"""

from pathlib import Path
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "DesktopPilot AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Local Ollama Server
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_MODEL: str = "llama3.1:8b"
    DEFAULT_AGENT_MODEL: str = "llama3.1:8b"
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT: float = 60.0

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
