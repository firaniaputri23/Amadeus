"""
Agent Field Autofill Router

This module provides routes for field autofill generation.
"""

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
import json
import traceback
from supabase import Client
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from ..models import RecommendationInput, RecommendationResponse, Tool
from ..tool_autofill import tool_autofill
from ...agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ValidationError, 
    InternalServerError, handle_pydantic_validation_error, ERROR_RESPONSES
)
from ...mcp_tools.routes.tools import get_supabase_client, get_tools

# Create router
router = APIRouter(
    prefix="/agent-creator-autofill",
    tags=["agent-creator-autofill"],
    responses={**ERROR_RESPONSES}
)

async def fetch_tools_from_db(supabase: Client, user_id: str, company_id: Optional[str] = None) -> List[Tool]:
    """Helper function to fetch tools from the database via get_tools endpoint.
    
    Args:
        supabase: Supabase client instance
        user_id: User ID from the request state
        company_id: Optional company ID to filter tools by
    """
    try:
        # Create a mock request object with the actual user_id
        class MockRequest:
            def __init__(self, user_id):
                self.state = type('State', (), {'user_id': user_id})()
                self.method = "GET"
                self.query_params = {}
        
        if not user_id:
            print("Warning: No user_id provided")
            return []
            
        mock_request = MockRequest(user_id)
        
        # Get tools using the existing get_tools function
        tool_responses = await get_tools(
            request=mock_request,
            company_id=company_id,  # Pass through company_id filter
            supabase=supabase
        )
        
        if not tool_responses:
            return []
            
        # Convert ToolResponse objects to Tool objects
        tools = []
        for tool in tool_responses:
            try:
                tools.append(Tool(
                    tool_id=str(tool.get("tool_id", "")),
                    name=str(tool.get("name", "")),
                    description=str(tool.get("description", "") or ""),
                    input_schema=tool.get("input_schema"),
                    output_schema=tool.get("output_schema"),
                    versions=tool.get("versions", []),  # Include versions
                    on_status=tool.get("on_status", "offline"),  # Include status
                    company_id=tool.get("company_id")  # Include company_id
                ))
            except Exception as e:
                print(f"Error creating Tool object: {str(e)}")
                continue
                
        return sorted(tools, key=lambda x: x.name.lower())
    except Exception as e:
        print(f"Failed to fetch tools from database: {str(e)}")
        print(traceback.format_exc())
        return []

def _verify_json_serialization(data: Any) -> Any:
    """Helper function to ensure data is serializable. """
    try:
        json.dumps(data)
        return data
    except Exception as e:
        print(f"Data serialization error: {str(e)}")
        
        # Handle different types of data
        if isinstance(data, dict):
            sanitized_dict = {}
            for key, value in data.items():
                try:
                    json.dumps({key: value})
                    sanitized_dict[key] = value
                except:
                    print(f"Field {key} couldn't be serialized, using empty string")
                    sanitized_dict[key] = ""
            return sanitized_dict
        elif isinstance(data, list):
            return []
        else:
            return

async def _parse_recommendation_input(request: Request) -> RecommendationInput:
    """Parse and validate input from both GET and POST requests."""
    request_method = request.method.upper()
    
    try:
        if request_method == "GET":
            # Extract parameters from query
            field_name = request.query_params.get("field_name", "")
            json_field_str = request.query_params.get("json_field", "{}")
            
            try:
                json_field = json.loads(json_field_str)
            except json.JSONDecodeError:
                raise BadRequestError("Invalid JSON in json_field parameter")
                
            existing_field_value = request.query_params.get("existing_field_value", "")
            return_tool_ids = request.query_params.get("return_tool_ids", "").lower() == "true"
            
            # Get token from query parameters for EventSource authentication
            token = request.query_params.get("token", "")
            if token:
                # Set the token in the request state for auth middleware
                request.state.token = token
            
            if not field_name:
                raise BadRequestError("field_name is required")
        else:
            # POST request with a JSON body
            try:
                data = await request.json()
                return RecommendationInput(**data)
            except PydanticValidationError as e:
                raise handle_pydantic_validation_error(e)
            except json.JSONDecodeError:
                raise BadRequestError("Invalid JSON in request body")
        
        # Return validated model for GET requests
        if request_method == "GET":
            return RecommendationInput(
                field_name=field_name,
                json_field=json_field,
                existing_field_value=existing_field_value,
                return_tool_ids=return_tool_ids
            )
    except PydanticValidationError as e:
        raise handle_pydantic_validation_error(e)
    except (BadRequestError, ValidationError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Error parsing request: {str(e)}")

async def _prepare_autofill_params(
    request: Request, 
    supabase: Client
) -> tuple[str, Dict, str, List[Tool], bool]:
    """Prepare parameters needed for autofill generation."""
    # Get user_id from request state (set by middleware)
    user_id = request.state.user_id
    if not user_id:
        raise BadRequestError("User ID not found in request state")
    
    # Parse input parameters
    recommendation_input = await _parse_recommendation_input(request)
    field_name = recommendation_input.field_name
    json_field = _verify_json_serialization(recommendation_input.json_field)
    existing_field_value = recommendation_input.existing_field_value
    return_tool_ids = recommendation_input.return_tool_ids
    
    # Default to empty tools list
    available_tools = []
    
    # If this is the tools field, fetch all tools from the database
    if field_name in ["tools", "mcphub_recommended_tools"]:
        # Log the request data for debugging
        print(f"Tool autofill request for {field_name}. JSON field: {json_field}")
        
        # Fetch all available tools from the database
        available_tools = await fetch_tools_from_db(supabase, user_id, None)
        print(f"Fetched {len(available_tools)} tools from database for autofill")
        
    # If tools list is not empty, ensure it's serializable
    if available_tools:
        try:
            json.dumps([{
                "tool_id": tool.tool_id,
                "name": tool.name,
                "description": tool.description if tool.description else ""
            } for tool in available_tools])
        except Exception:
            # If serialization fails, use empty tool list
            available_tools = []
            
    return field_name, json_field, existing_field_value, available_tools, return_tool_ids

@router.get("/tools", response_model=List[Tool])
async def get_available_tools(
    request: Request,
    company_id: Optional[str] = Query(None, description="Optional company ID to filter tools by"),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get all available tools that can be used by agents.
    
    This endpoint retrieves a list of all available tools with their IDs, names, descriptions,
    versions, and status information. Tools can be optionally filtered by company ID.
    
    Args:
        request: FastAPI request object
        company_id: Optional company ID to filter tools by
        supabase: Supabase client instance
        
    Returns:
        List[Tool]: List of available tools with their details
    """
    try:
        user_id = request.state.user_id
        
        # Query tools from Supabase with optional company filter
        tools = await fetch_tools_from_db(supabase, user_id, company_id)
        return tools
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.post("/invoke", response_model=RecommendationResponse)
async def invoke_autofill(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Autofill a field based on other field values.
    
    This endpoint takes a field name and JSON field values and returns an autofilled value for the field.
    """
    try:
        field_name, json_field, existing_field_value, available_tools, return_tool_ids = (
            await _prepare_autofill_params(request, supabase)
        )
        
        # Generate the autofill
        try:
            # Handle mcphub_recommended_tools field type
            if field_name == "mcphub_recommended_tools":
                response = await tool_autofill.generate_autofill(
                    field_name=field_name,
                    json_field=json_field,
                    existing_field_value=existing_field_value,
                    available_tools=available_tools,
                    return_tool_ids=return_tool_ids
                )
                return response
            
            # Handle other field types
            response = await tool_autofill.generate_autofill(
                field_name=field_name,
                json_field=json_field,
                existing_field_value=existing_field_value,
                available_tools=available_tools,
                return_tool_ids=return_tool_ids
            )
        except Exception as e:
            raise InternalServerError(f"Failed to generate autofill: {str(e)}")
        
        return response
    except (BadRequestError, ValidationError, InternalServerError) as e:
        raise
    except Exception as e:
        raise InternalServerError(f"Unexpected error: {str(e)}")
