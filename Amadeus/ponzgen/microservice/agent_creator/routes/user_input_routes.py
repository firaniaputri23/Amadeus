"""
User Input Parser Router

This module provides routes for parsing user input to extract agent field information.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
import json
import asyncio

from supabase import Client

from ..utils.input_parser import (
    extract_fields_from_input,
    extract_fields_from_input_stream,
    extract_keywords_from_agent,
    parse_multi_agent_input
)
from ...agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ValidationError, 
    InternalServerError, ERROR_RESPONSES
)

from microservice.agent_field_autofill.utils.field_utils import load_field_descriptions

# Define request and response models with common base class
class BaseParserRequest(BaseModel):
    """Base model for parser requests with common fields."""
    user_input: str = Field(..., description="Natural language input from the user")
    model_name: str = Field("custom-vlm", description="Name of the LLM to use")
    temperature: float = Field(0, description="Temperature setting for the model (0-1)")

class UserInputParseRequest(BaseParserRequest):
    """Request for parsing user input."""
    target_fields: Optional[List[str]] = Field(None, description="List of field names to extract (if None, detects automatically)")

class FieldParseRequest(BaseParserRequest):
    """Request for parsing user input for a specific field."""
    field_name: str = Field(..., description="Name of the field to extract")

class EnrichDataRequest(BaseParserRequest):
    """Request for enriching partial data with information from user input."""
    partial_data: Dict[str, Any] = Field(..., description="Existing partial agent data")

# Create router
router = APIRouter(
    prefix="/user-input",
    tags=["user-input"],
    responses={**ERROR_RESPONSES}
)

# Dependency functions
def get_supabase_client(request: Request) -> Client:
    """Get Supabase client from request state."""
    return request.app.state.supabase

def _validate_user_id(request: Request) -> str:
    """Validate that user_id exists in request state."""
    user_id = request.state.user_id
    if not user_id:
        raise BadRequestError("User ID not found in request state")
    return user_id

# Error handling helper
def _handle_error(e: Exception, context: str) -> None:
    """Handle and re-raise errors with appropriate context."""
    if isinstance(e, (BadRequestError, ValidationError, NotFoundError, InternalServerError)):
        raise
    else:
        raise InternalServerError(f"Failed to {context}: {str(e)}")

# Route handlers

@router.post("/parse-stream")
async def parse_user_input_stream(
    request: Request,
    parse_request: UserInputParseRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Stream the parsing of user input to extract field information.
    
    This endpoint takes natural language input and streams the extracted field values
    as they are generated.
    """
    try:
        _validate_user_id(request)
        
        async def _event_generator():
            """Generate SSE events with field updates."""
            async for field_update in extract_fields_from_input_stream(
                user_input=parse_request.user_input,
                model_name=parse_request.model_name,
                temperature=parse_request.temperature
            ):
                for field, value in field_update.items():
                    # Send each field update as a separate event
                    yield f"event: field_update\ndata: {{\"{field}\": {json.dumps(value)}}}\n\n"
                    
                    # Small delay to prevent overwhelming the client
                    await asyncio.sleep(0.01)
            
            # Signal completion
            yield "event: done\ndata: [DONE]\n\n"
        
        return StreamingResponse(
            _event_generator(),
            media_type="text/event-stream"
        )
    except Exception as e:
        _handle_error(e, "stream parse user input")

@router.post("/parse-field", response_model=Dict[str, Any])
async def parse_field_from_input(
    request: Request,
    field_request: FieldParseRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Parse user input to extract information for a specific field.
    
    This endpoint takes natural language input and a field name, and returns the extracted value.
    """
    try:
        _validate_user_id(request)
        
        try:
            field_value = await extract_fields_from_input(
                user_input=field_request.user_input,
                target_fields=[field_request.field_name],
                model_name=field_request.model_name,
                temperature=field_request.temperature
            )
            
            return {field_request.field_name: field_value.get(field_request.field_name, "")}
        except ValueError as e:
            raise NotFoundError(str(e))
        
    except Exception as e:
        _handle_error(e, "parse field from user input")

@router.get("/field-description/{field_name}", response_model=Dict[str, str])
async def get_field_description(
    request: Request,
    field_name: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get the description for a specific field.
    
    This endpoint returns the description of the specified field.
    """
    try:
        _validate_user_id(request)
        
        field_descriptions = load_field_descriptions()
        description = field_descriptions.get(field_name, "No description available.")
        
        if description == "No description available.":
            raise NotFoundError(f"Field '{field_name}' not found")
            
        return {"field_name": field_name, "description": description}
    except Exception as e:
        _handle_error(e, "get field description")

@router.get("/field-metadata", response_model=Dict[str, Any])
async def get_field_metadata(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get metadata for all available fields in a single call.
    
    This endpoint returns both the list of field names and their descriptions
    in a single response, optimizing client-side requests.
    
    Returns:
        Dictionary containing:
            - fields: List of available field names
            - descriptions: Dictionary mapping field names to descriptions
    """
    try:
        _validate_user_id(request)
        
        field_descriptions = load_field_descriptions()
        
        return {
            "fields": list(field_descriptions.keys()),
            "descriptions": field_descriptions
        }
    except Exception as e:
        _handle_error(e, "get field metadata")

@router.post("/extract-keywords")
async def extract_keywords(
    request: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Extract keywords from agent name and description.
    
    Args:
        request: Dictionary containing:
            - agent_name: Name of the agent
            - description: Description of the agent
            - model_name: Name of the model to use
            - temperature: Temperature setting for the model
            
    Returns:
        Dictionary containing:
            - keywords: List of extracted keywords
    """
    try:
        agent_name = request.get("agent_name", "")
        description = request.get("description", "")
        model_name = request.get("model_name", "custom-vlm")
        temperature = float(request.get("temperature", 0))
        
        if not agent_name or not description:
            raise BadRequestError(
                detail="Both agent_name and description are required",
                additional_info={
                    "missing_fields": [
                        field for field in ["agent_name", "description"] 
                        if not request.get(field)
                    ]
                }
            )
            
        keywords = await extract_keywords_from_agent(
            agent_name=agent_name,
            description=description,
            model_name=model_name,
            temperature=temperature
        )
        
        return {"keywords": keywords}
        
    except Exception as e:
        _handle_error(e, "extract keywords from agent")

class MultiAgentParseRequest(BaseParserRequest):
    """Request for parsing multi-agent input."""
    existing_data: Optional[Dict[str, Any]] = Field(None, description="Existing data for the agents")

@router.post("/parse-multi-agent", response_model=Dict[str, Any])
async def parse_multi_agent(
    request: Request,
    parse_request: MultiAgentParseRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Parse user input to detect multiple agents and their differences.
    
    This endpoint takes natural language input and returns:
    - Whether multiple agents were detected
    - Number of agents
    - Common attributes among all agents
    - Specific variations for each agent
    - Whether more information is needed
    """
    try:
        _validate_user_id(request)
        
        result = await parse_multi_agent_input(
            user_input=parse_request.user_input,
            model_name=parse_request.model_name,
            temperature=parse_request.temperature
        )
        
        # If we have existing data and this is multi-agent, merge the common attributes
        if parse_request.existing_data and result.get("has_multi_agent"):
            # Merge existing data into common attributes
            for key, value in parse_request.existing_data.items():
                if key not in result["common_attributes"] or not result["common_attributes"][key]:
                    result["common_attributes"][key] = value
        
        return result
        
    except Exception as e:
        _handle_error(e, "parse multi-agent input") 