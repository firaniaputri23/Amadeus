"""
Agent Field Autofill Module

This module handles field autofill generation using LLMs.
It is a simplified version of the agent boilerplate, without memory, tools, or other complex features.
"""

# Standard library imports
from typing import Dict, Any, Optional, AsyncGenerator, List
import json
import os
import sys
import re
from datetime import datetime
import asyncio

# Third-party imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Local imports
from .utils.mcphub_compass import get_recommended_tools
from ..agent_boilerplate.boilerplate.errors import (
    BadRequestError, InternalServerError, ServiceUnavailableError
)

from ..agent_boilerplate.boilerplate.utils.get_llms import get_llms

class ToolAutofill:
    """
    Handles field autofill generation using LLMs.
    This class is a simplified version of the AgentBoilerplate class.
    
    Main responsibilities:
    1. Generate field values based on existing fields and agent context
    2. Handle special fields like tools and tool recommendations
    3. Provide both direct and streaming interfaces for field generation
    """
    
    # Default tool recommendations when API calls or LLM generations fail
    DEFAULT_MCP_TOOLS = [
        {"name": "MCP GitHub", "description": "Provides GitHub integration to search repositories, create issues and PRs."},
        {"name": "MCP Google Calendar", "description": "Allows scheduling and managing calendar events and appointments."},
        {"name": "MCP Gmail", "description": "Enables reading, sending, and managing emails."}
    ]
    
    DEFAULT_MCPHUB_TOOLS = [
        {"name": "GitHub Tools", "description": "Provides GitHub integration to search repositories, create issues and PRs.", "url": "https://github.com"},
        {"name": "Google Calendar", "description": "Allows scheduling and managing calendar events and appointments.", "url": "https://calendar.google.com"}
    ]
    
    def __init__(self):
        """Initialize the AgentFieldAutofill."""
        pass
    
    def _validate_input(self, field_name: str, json_field: Dict[str, Any]) -> None:
        """
        Validate the input parameters.
        
        This method is called at the beginning of generation methods to ensure
        that the required parameters are present and valid.
        
        Args:
            field_name: The name of the field to generate
            json_field: JSON object containing other field values
            
        Raises:
            BadRequestError: If input validation fails
        """
        if not field_name:
            raise BadRequestError("Field name cannot be empty")
            
        if not isinstance(json_field, dict):
            raise BadRequestError("json_field must be a valid JSON object")
    
    async def _get_recommended_tools(
        self,
        agent_name: str,
        description: str,
        keywords: List[str],
        available_tools: List[Any],
        model_name: str = "custom-vlm",
        temperature: float = 0
    ) -> List[str]:
        """
        Use LLM to recommend tools based on agent description and keywords.
        
        Args:
            agent_name: Name of the agent
            description: Description of the agent's purpose
            keywords: List of keywords describing the agent
            available_tools: List of available tools
            model_name: The name of the LLM to use
            temperature: The temperature setting for the model
            
        Returns:
            List of recommended tool IDs
        """
        try:
            # Format tools for LLM prompt
            tool_descriptions = []
            tool_id_map = {}  # Map tool names to IDs for lookup
            
            for tool in available_tools:
                tool_descriptions.append(f"- {tool.name}: {tool.description}")
                tool_id_map[tool.name.lower()] = tool.tool_id
            
            # Create prompt for LLM
            prompt = f"""Given an AI agent with the following keywords:

Agent Name: {agent_name}
Agent Description: {description}

Keywords: {', '.join(keywords)}

And the following available tools:
{chr(10).join(tool_descriptions)}

Please analyze the agent's purpose and select the most relevant tools it needs to function effectively. 
Return your response as a JSON array of tool names. 

First, analyze the keywords and the agent's purpose.
Then, calculate the relevance score for each tool based on the agent's purpose and the tool's description.
Only include tools that you are highly confident have a relevance score of 0.8 or higher.

Example response format:
["Tool Name 1", "Tool Name 2"]"""

            # Get LLM instance
            llm = get_llms(model_name=model_name, temperature=temperature)
            
            # Generate response
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            
            # Extract tool names from response
            try:
                tool_names = json.loads(response.content)
                if not isinstance(tool_names, list):
                    raise ValueError("Response is not a list")
                    
                # Convert tool names to IDs
                tool_ids = []
                for name in tool_names:
                    tool_id = tool_id_map.get(name.lower())
                    if tool_id:
                        tool_ids.append(tool_id)
                
                return tool_ids
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, try to extract array using regex
                import re
                matches = re.findall(r'"([^"]+)"', response.content)
                tool_ids = []
                for name in matches:
                    tool_id = tool_id_map.get(name.lower())
                    if tool_id:
                        tool_ids.append(tool_id)
                return tool_ids
                
        except Exception as e:
            print(f"Error getting tool recommendations: {str(e)}")
            return []

    async def _handle_tools_field(self, available_tools: List[Any], return_tool_ids: bool, json_field: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle the special case for the 'tools' field.
        
        Now uses LLM to recommend relevant tools based on agent description.
        If no recommendations can be made, returns an empty list instead of all tools.
        
        Args:
            available_tools: List of available tools
            return_tool_ids: Whether to return tool IDs or names
            json_field: JSON object containing field values
            
        Returns:
            Dictionary with autofill information
        """
        # Handle case where no tools are available
        if len(available_tools) == 0:
            return {
                "field_name": "tools",
                "autofilled_value": [],
                "reasoning": "No tools available in the database."
            }
        
        # If we have agent information, use LLM to recommend tools
        if json_field and json_field.get("agent_name") and json_field.get("description"):
            agent_name = json_field.get("agent_name", "")
            description = json_field.get("description", "")
            keywords = json_field.get("keywords", [])
            
            # Get recommended tools
            recommended_tools = await self._get_recommended_tools(
                agent_name=agent_name,
                description=description,
                keywords=keywords,
                available_tools=available_tools
            )
            
            if recommended_tools:
                if return_tool_ids:
                    return {
                        "field_name": "tools",
                        "autofilled_value": recommended_tools,
                        "reasoning": "Selected tools based on agent's purpose and capabilities."
                    }
                else:
                    # Convert IDs to names if needed
                    tool_names = []
                    for tool_id in recommended_tools:
                        for tool in available_tools:
                            if tool.tool_id == tool_id:
                                tool_names.append(tool.name)
                                break
                    return {
                        "field_name": "tools",
                        "autofilled_value": tool_names,
                        "reasoning": "Selected tools based on agent's purpose and capabilities."
                    }
        
        # Return empty list if no recommendations could be made
        return {
            "field_name": "tools",
            "autofilled_value": [],
            "reasoning": "No specific tool recommendations could be made. Please select tools manually."
        }
    
    async def _handle_mcphub_recommended_tools(self, json_field: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the special case for the 'mcphub_recommended_tools' field.
        
        This field uses the MCPHUB Compass API to get tool recommendations
        based on the agent's keywords from the frontend.
        
        Args:
            json_field: JSON object containing field values
            
        Returns:
            Dictionary with autofill information
        """
        # Get keywords from frontend
        keywords = json_field.get("keywords", [])
        
        # Check if we have any keywords
        if not keywords:
            return {
                "field_name": "mcphub_recommended_tools",
                "autofilled_value": "[]",
                "reasoning": "No keywords available for tool recommendations."
            }
            
        try:
            # Call the MCPHUB Compass API to get tool recommendations using only keywords
            tools_data = await get_recommended_tools(keywords=keywords)
            
            return {
                "field_name": "mcphub_recommended_tools",
                "autofilled_value": json.dumps(tools_data),
                "reasoning": "Generated MCPHUB tool recommendations based on agent keywords."
            }
        except Exception as e:
            # Fall back to default tools if API call fails
            return {
                "field_name": "mcphub_recommended_tools",
                "autofilled_value": json.dumps(self.DEFAULT_MCPHUB_TOOLS),
                "reasoning": f"Error fetching MCPHUB recommendations, using defaults. Error: {str(e)}"
            }
    
    async def generate_autofill(
        self, 
        field_name: str, 
        json_field: Dict[str, Any], 
        available_tools: List[Any],
        existing_field_value: str = "",
        return_tool_ids: bool = True,
        model_name: str = "custom-vlm", 
        temperature: float = 0
    ) -> Dict[str, Any]:
        """
        Generate a field autofill based on other field values.
        
        This is the main entry point for generating field values. It dispatches
        to specialized handlers based on the field name.
        
        Flow:
        1. Validate inputs
        2. Handle special fields with custom logic
        3. Process standard fields using LLM
        4. Return formatted response
        
        Args:
            field_name: The name of the field to generate
            json_field: JSON object containing other field values
            available_tools: List of available tools that can be recommended
            existing_field_value: Existing value of the field to continue from (if any)
            return_tool_ids: Whether to return tool IDs instead of names for tools field (defaults to True)
            model_name: The name of the LLM to use
            temperature: The temperature setting for the model (0-1)
            
        Returns:
            Dictionary containing the autofilled value
        """
        try:
            # Step 1: Validate inputs
            self._validate_input(field_name, json_field)
            
            # Skip autofill for agent_name, description, and agent_style
            if field_name in ["agent_name", "description", "agent_style"]:
                return {
                    "field_name": field_name,
                    "autofilled_value": existing_field_value,
                    "reasoning": "Autofill skipped for this field."
                }
            
            # Step 2: Handle special fields with specific logic
            # Special case: Tools field (returns all available tools)
            if field_name == "tools":
                return await self._handle_tools_field(available_tools, return_tool_ids, json_field)
            
            # Special case: MCPHUB tool recommendations (uses external API)
            if field_name == "mcphub_recommended_tools":
                return await self._handle_mcphub_recommended_tools(json_field)
            
            # Return empty for any other fields
            return {
                "field_name": field_name,
                "autofilled_value": "",
                "reasoning": "Field not supported for autofill."
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
    
    async def generate_autofill_stream(
        # currently not used
        self, 
        field_name: str, 
        json_field: Dict[str, Any], 
        available_tools: List[Any],
        existing_field_value: str = "",
        return_tool_ids: bool = True,
        model_name: str = "custom-vlm", 
        temperature: float = 0
    ) -> AsyncGenerator[str, None]:
        """Stream the generation of field autofill."""
        try:
            # Step 1: Validate inputs
            self._validate_input(field_name, json_field)
            
            # Skip autofill for agent_name, description, and agent_style
            if field_name in ["agent_name", "description", "agent_style"]:
                yield f"data: {json.dumps(existing_field_value)}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # Step 2: Handle special fields with specific streaming logic
            # Special case: MCPHUB tool recommendations (uses external API)
            if field_name == "mcphub_recommended_tools":
                async for chunk in self._stream_mcphub_recommended_tools(json_field):
                    yield chunk
                return
            
            # Special case: Tools field (returns all available tools)
            if field_name == "tools":
                async for chunk in self._stream_tools_field(available_tools, return_tool_ids):
                    yield chunk
                return
            
            # For any other fields, return empty
            yield f"data: {json.dumps('')}\n\n"
            yield "data: [DONE]\n\n"
                
        except (BadRequestError, ServiceUnavailableError, InternalServerError):
            # Re-raise known errors
            raise
        except Exception as e:
            # Catch any unexpected errors
            raise InternalServerError(
                f"Failed to generate autofill stream: {str(e)}",
                additional_info={
                    "field_name": field_name,
                    "model": model_name
                }
            )

# Create a singleton instance for reuse across the application
tool_autofill = ToolAutofill()