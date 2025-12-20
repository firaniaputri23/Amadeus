"""
Agent Field Autofill Router

This module provides routes for field autofill generation.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import json
from supabase import Client
from pydantic import ValidationError as PydanticValidationError

from ..models import RecommendationInput, RecommendationResponse
from ..agent_field_autofill import agent_field_autofill
from ...agent_boilerplate.boilerplate.errors import (
    BadRequestError, NotFoundError, ValidationError, 
    InternalServerError, handle_pydantic_validation_error, ERROR_RESPONSES
)

# Create router
router = APIRouter(
    prefix="/agent-field-autofill",
    tags=["agent-field-autofill"],
    responses={**ERROR_RESPONSES}
)

# Dependency to get Supabase client
def get_supabase_client(request: Request):
    return request.app.state.supabase

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
        # Try to parse and validate the input
        try:
            data = await request.json()
            recommendation_input = RecommendationInput(**data)
        except PydanticValidationError as e:
            raise handle_pydantic_validation_error(e)
        except json.JSONDecodeError:
            raise BadRequestError("Invalid JSON in request body")
            
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        if not user_id:
            raise BadRequestError("User ID not found in request state")
        
        # Extract input parameters
        field_name = recommendation_input.field_name
        json_field = recommendation_input.json_field
        existing_field_value = recommendation_input.existing_field_value
        
        # Generate the autofill
        try:
            response = await agent_field_autofill.generate_autofill(
                field_name=field_name,
                json_field=json_field,
                existing_field_value=existing_field_value
            )
        except Exception as e:
            raise InternalServerError(f"Failed to generate autofill: {str(e)}")
        
        return response
    except (BadRequestError, ValidationError, InternalServerError) as e:
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")

@router.post("/invoke-stream", responses={**ERROR_RESPONSES})
@router.get("/invoke-stream", responses={**ERROR_RESPONSES})  # Add GET support for EventSource
async def invoke_autofill_stream(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Autofill a field with streaming response.
    
    This endpoint takes a field name and JSON field values and returns a streaming response
    with the autofilled value for the field.
    """
    try:
        # Get user_id from request state (set by middleware)
        user_id = request.state.user_id
        
        # Handle both POST (JSON body) and GET (query parameters) requests
        request_method = request.method.upper()
        
        if request_method == "GET":
            # This is a GET request, extract parameters from query
            try:
                field_name = request.query_params.get("field_name", "")
                json_field_str = request.query_params.get("json_field", "{}")
                json_field = json.loads(json_field_str)
                existing_field_value = request.query_params.get("existing_field_value", "")
                
                # Get token from query parameters for EventSource authentication
                token = request.query_params.get("token", "")
                if token:
                    # Set the token in the request state for auth middleware
                    request.state.token = token
                
                if not field_name:
                    raise BadRequestError("field_name is required")
                
                # Validate using the model
                try:
                    recommendation_input = RecommendationInput(
                        field_name=field_name,
                        json_field=json_field,
                        existing_field_value=existing_field_value
                    )
                except PydanticValidationError as e:
                    raise handle_pydantic_validation_error(e)
            except json.JSONDecodeError:
                raise BadRequestError("Invalid JSON in json_field parameter")
        else:
            # This is a POST request with a JSON body
            try:
                data = await request.json()
                recommendation_input = RecommendationInput(**data)
            except PydanticValidationError as e:
                raise handle_pydantic_validation_error(e)
            except json.JSONDecodeError:
                raise BadRequestError("Invalid JSON in request body")
                
            field_name = recommendation_input.field_name
            json_field = recommendation_input.json_field
            existing_field_value = recommendation_input.existing_field_value
        
        # Return streaming response
        return StreamingResponse(
            agent_field_autofill.generate_autofill_stream(
                field_name=field_name,
                json_field=json_field,
                existing_field_value=existing_field_value
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except (BadRequestError, ValidationError) as e:
        # Re-raise known client errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise InternalServerError(f"Unexpected error: {str(e)}")