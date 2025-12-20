"""
Agent Field Autofill Module

This module handles field autofill generation using LLMs.
It is a simplified version of the agent boilerplate, without memory, tools, or other complex features.
"""

from typing import Dict, Any, Optional, AsyncGenerator
import json
import os
import sys
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from others.prompts.field_prompt_templates import construct_system_prompt
from .utils.field_utils import load_field_descriptions
from ..agent_boilerplate.boilerplate.errors import (
    BadRequestError, InternalServerError, ServiceUnavailableError
)
from ..agent_boilerplate.boilerplate.utils.custom_vlm_model import get_custom_vlm_model
from langchain_core.language_models import LLM

class AgentFieldAutofill:
    """
    Handles field autofill generation using LLMs.
    This class is a simplified version of the AgentBoilerplate class.
    """
    
    def __init__(self):
        """Initialize the AgentFieldAutofill."""
        pass
    
    def get_llm(self, model_name: str = "custom-vlm", temperature: float = 0) -> LLM:
        """
        Get a configured LLM instance.
        
        Args:
            model_name: The name of the model to use
            temperature: The temperature setting for the model (0-1)
            
        Returns:
            A configured ChatOpenAI instance
        """
        try:
            print(f"Initializing LLM: Using Custom VLM instead of {model_name}")
            return get_custom_vlm_model()
        except Exception as e:
            raise InternalServerError(f"Failed to initialize LLM: {str(e)}")
    
    async def generate_autofill(self, field_name: str, json_field: Dict[str, Any], existing_field_value: str = "",
                                model_name: str = "custom-vlm", temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate a field autofill based on other field values.
        
        Args:
            field_name: The name of the field to generate
            json_field: JSON object containing other field values
            model_name: The name of the LLM to use
            temperature: The temperature setting for the model (0-1)
            
        Returns:
            Dictionary containing the autofilled value
        """
        if not field_name:
            raise BadRequestError("Field name cannot be empty")
            
        if not isinstance(json_field, dict):
            raise BadRequestError("json_field must be a valid JSON object")
        
        try:
            # Load field descriptions and construct the system prompt
            field_descriptions = load_field_descriptions()
            system_prompt = construct_system_prompt(field_name, json_field, existing_field_value, field_descriptions)
            
            # Get the LLM
            llm = self.get_llm(model_name, temperature)
            
            # Generate the autofill
            try:
                # Pass system_prompt string directly to avoid list[BaseMessage] -> string formatting issues
                response = await llm.ainvoke(system_prompt)
            except Exception as e:
                raise ServiceUnavailableError(
                    f"LLM service failed to respond: {str(e)}",
                    additional_info={"model": model_name}
                )
            
            # Handle response type (ChatModel returns AIMessage, LLM returns str)
            content = response.content if hasattr(response, 'content') else str(response)

            # Return the autofill
            return {
                "field_name": field_name,
                "autofilled_value": content,
                "reasoning": None  # Could be extracted from the response if needed
            }
        except (BadRequestError, ServiceUnavailableError):
            # Re-raise known errors
            raise
        except Exception as e:
            # Catch any unexpected errors
            raise InternalServerError(
                f"Failed to generate autofill: {str(e)}",
                additional_info={
                    "field_name": field_name,
                    "model": model_name
                }
            )
    
    async def generate_autofill_stream(self, field_name: str, json_field: Dict[str, Any], existing_field_value: str = "",
                                     model_name: str = "custom-vlm", 
                                     temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """
        Generate a field autofill with streaming response.
        
        Args:
            field_name: The name of the field to generate
            json_field: JSON object containing other field values
            model_name: The name of the LLM to use
            temperature: The temperature setting for the model (0-1)
            
        Yields:
            Streaming response chunks
        """
        if not field_name:
            raise BadRequestError("Field name cannot be empty")
            
        if not isinstance(json_field, dict):
            raise BadRequestError("json_field must be a valid JSON object")
        
        try:
            # Load field descriptions and construct the system prompt
            field_descriptions = load_field_descriptions()
            system_prompt = construct_system_prompt(field_name, json_field, existing_field_value, field_descriptions)
            
            # Get the LLM
            llm = self.get_llm(model_name, temperature)
            
            # Start the stream (no thread_id needed)
            yield f"event: status\ndata: {json.dumps({'status': 'Processing your request'})}\n\n"
            
            # Stream the response
            full_response = ""
            try:
                # Pass system_prompt string directly
                async for chunk in llm.astream(system_prompt):
                    content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    if content:
                        full_response += content
                        yield f"event: token\ndata: {json.dumps({'token': content})}\n\n"
            except Exception as e:
                error_message = f"LLM streaming failed: {str(e)}"
                yield f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
                raise ServiceUnavailableError(
                    error_message,
                    additional_info={"model": model_name}
                )
            
            # Signal end of execution with the final response (no thread_id needed)
            end_data = {
                "status": "Autofill Complete",
                "field_name": field_name,
                "autofilled_value": full_response
            }
            yield f"event: status\ndata: {json.dumps(end_data)}\n\n"
        except Exception as e:
            # This error handling is only for non-streaming errors
            # For streaming errors, we yield an error event and then raise
            if not isinstance(e, ServiceUnavailableError):
                error_message = f"Failed to generate autofill stream: {str(e)}"
                yield f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
                raise InternalServerError(
                    error_message,
                    additional_info={
                        "field_name": field_name,
                        "model": model_name
                    }
                )
            else:
                raise

# Create a singleton instance
agent_field_autofill = AgentFieldAutofill()