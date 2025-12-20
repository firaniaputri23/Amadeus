"""
Models Module for Agent Field Autofill

This module defines the Pydantic models used in the agent field autofill service.
These models are used for request and response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class RecommendationInput(BaseModel):
    """Input for field autofill."""
    field_name: str = Field(..., description="The name of the field to generate")
    json_field: Dict[str, Any] = Field(..., description="JSON object containing other field values")
    existing_field_value: str = Field("", description="Existing value of the field to continue from (if any)")

class RecommendationResponse(BaseModel):
    """Response for field autofill."""
    field_name: str
    autofilled_value: Any
    reasoning: Optional[str] = None