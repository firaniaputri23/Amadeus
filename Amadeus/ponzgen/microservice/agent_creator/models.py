"""
Models Module for Agent Field Autofill

This module defines the Pydantic models used in the agent field autofill service.
These models are used for request and response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any

class Tool(BaseModel):
    """Tool model representing a tool available for agents."""
    tool_id: str
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    versions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    on_status: Optional[str] = Field(default="offline")
    company_id: Optional[str] = None

class RecommendationInput(BaseModel):
    """Input for field autofill."""
    field_name: str = Field(..., description="The name of the field to generate")
    json_field: Dict[str, Any] = Field(..., description="JSON object containing other field values")
    available_tools: List[Tool] = Field(..., description="List of available tools that can be recommended")
    existing_field_value: str = Field("", description="Existing value of the field to continue from (if any)")
    return_tool_ids: Optional[bool] = Field(default=True, description="Whether to return tool IDs instead of names for tools field")

class RecommendationResponse(BaseModel):
    """Response for field autofill."""
    field_name: str
    autofilled_value: Any
    reasoning: Optional[str] = None