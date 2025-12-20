"""
Models Module

This module defines the Pydantic models used in the agent boilerplate.
These models are used for request and response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class AgentInputMessage(BaseModel):
    """Input message for the agent."""
    messages: str
    context: str = ""
    image_path: Optional[str] = None


class AgentInputConfig(BaseModel):
    """Configuration for the agent invocation."""
    configurable: Dict[str, Any] = Field(
        default_factory=lambda: {"thread_id": "1"}
    )


class AgentInputMetadata(BaseModel):
    """Metadata for the agent invocation."""
    model_name: str = "custom-vlm"
    reset_memory: bool = False
    load_from_json: bool = True  # Kept for backward compatibility with frontend
    agent_style: str = ""


class AgentInput(BaseModel):
    """Input for agent invocation."""
    input: AgentInputMessage
    config: AgentInputConfig = Field(default_factory=AgentInputConfig)
    metadata: AgentInputMetadata = Field(default_factory=AgentInputMetadata)
    agent_config: Optional[Dict[str, Any]] = None


class ToolConfig(BaseModel):
    """Configuration for a tool."""
    tool_id: str
    name: str
    description: Optional[str] = None
    versions: List[Dict[str, Any]] = Field(default_factory=list)