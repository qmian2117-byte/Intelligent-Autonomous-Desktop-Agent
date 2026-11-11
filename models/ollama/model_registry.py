"""
Model registry and configuration for DesktopPilot AI.
Detects and links local Ollama model storage.
"""

from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Any, List

# Path to the local Ollama models repository discovered in workspace
LOCAL_OLLAMA_STORAGE = Path(r"E:\OPEN_CV\DESKTOP\Ollama_Models")

class ModelSpec(BaseModel):
    name: str
    tag: str
    base_architecture: str
    parameter_size: str
    is_multimodal_vision: bool
    supports_tool_calling: bool
    suitability_for_desktop_agent: str
    recommended_role: str

AVAILABLE_LOCAL_MODELS: Dict[str, ModelSpec] = {
    "qwen2.5:1.5b": ModelSpec(
        name="qwen2.5",
        tag="1.5b",
        base_architecture="Qwen2.5-Instruct",
        parameter_size="1.5B (~986 MB)",
        is_multimodal_vision=False,
        supports_tool_calling=False,  # 1.5B has weak JSON/tool-call reliability
        suitability_for_desktop_agent="Low to Moderate (Limited Reasoning)",
        recommended_role="Fast intent classification, simple text parsing, voice transcript cleanup"
    ),
    "visiontwin-ai:latest": ModelSpec(
        name="visiontwin-ai",
        tag="latest",
        base_architecture="Qwen2.5-Instruct (Fine-tuned/Prompt-wrapped)",
        parameter_size="1.5B",
        is_multimodal_vision=False,  # Text-only despite the 'vision' name
        supports_tool_calling=False,
        suitability_for_desktop_agent="Unsuitable (Industrial Prompt Locked)",
        recommended_role="Not recommended for desktop control (Locked to industrial manual QA)"
    ),
    # Recommended production models for LangGraph Desktop Agent:
    "qwen2.5:7b": ModelSpec(
        name="qwen2.5",
        tag="7b",
        base_architecture="Qwen2.5-Instruct",
        parameter_size="7B (~4.7 GB)",
        is_multimodal_vision=False,
        supports_tool_calling=True,
        suitability_for_desktop_agent="High (Excellent for Tool Calling & LangGraph)",
        recommended_role="Primary Reasoning & Tool-calling Agent"
    ),
    "llama3.2-vision:11b": ModelSpec(
        name="llama3.2-vision",
        tag="11b",
        base_architecture="Llama-3.2-Vision-Instruct",
        parameter_size="11B (~7.9 GB)",
        is_multimodal_vision=True,
        supports_tool_calling=True,
        suitability_for_desktop_agent="High (Full Screen Understanding)",
        recommended_role="Desktop Screenshot Vision & UI Element Grounding"
    )
}

