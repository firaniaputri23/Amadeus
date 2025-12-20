"""
Input Parser Module

This module provides utilities for parsing user input to extract field information.
It uses LLM to analyze natural language input and extract structured field data
based on the field descriptions.
"""

import json
import re

from typing import Dict, Any, List, Optional, Union, AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
import logging

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from microservice.agent_field_autofill.utils.field_utils import load_field_descriptions
from others.prompts.input_parser_prompts import (
    create_extraction_prompt,
    create_keyword_extraction_prompt,
    create_multi_agent_parsing_prompt
)

from microservice.agent_boilerplate.boilerplate.utils.get_llms import get_llms

class InputParser:
    """
    Parses user input to extract structured field information.
    Uses LLM to analyze natural language input and derive field values.
    """
    
    def __init__(self):
        """Initialize the InputParser with field descriptions."""
        self.field_descriptions = load_field_descriptions()
    
    def _validate_input(self, user_input: str) -> None:
        """
        Validate user input.
        
        Args:
            user_input: The natural language input from the user
            
        Raises:
            ValueError: If user_input is empty
        """
        if not user_input.strip():
            raise ValueError("User input cannot be empty")
    
    def _validate_fields(self, target_fields: List[str]) -> None:
        """
        Validate that all target fields exist.
        
        Args:
            target_fields: List of field names to validate
            
        Raises:
            ValueError: If any field name is invalid
        """
        invalid_fields = [field for field in target_fields if field not in self.field_descriptions]
        if invalid_fields:
            raise ValueError(f"Invalid field names: {', '.join(invalid_fields)}")
    
    def _create_extraction_prompt(self, user_input: str) -> str:
        """
        Create a prompt for extracting field information from user input.
        
        Args:
            user_input: The natural language input from the user
            
        Returns:
            Prompt string for the LLM
        """
        return create_extraction_prompt(user_input, self.field_descriptions)
    
    @staticmethod
    def _parse_json_structure(response_content: str, pattern: str, is_list: bool = False) -> Union[Dict[str, Any], List[str]]:
        """
        Helper method to parse JSON from a text using a regex pattern.
        
        Args:
            response_content: The text content to parse
            pattern: Regex pattern to extract JSON
            is_list: Whether to parse as a list or dictionary
            
        Returns:
            Parsed JSON as dictionary/list or empty dict/list if parsing fails
        """
        json_match = re.search(pattern, response_content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if (is_list and isinstance(result, list)) or (not is_list and isinstance(result, dict)):
                    return result
            except json.JSONDecodeError:
                pass
        
        return [] if is_list else {}
    
    @staticmethod
    def _sanitize_json_string(content: str) -> str:
        """
        Sanitize JSON string by replacing smart quotes and other common issues.
        """
        # Replace smart double quotes with standard double quote
        content = content.replace('“', '"').replace('”', '"')
        
        # Replace smart single and double quotes
        content = content.replace("‘", '"').replace("’", '"')
        content = content.replace("“", '"').replace("”", '"')
        
        # Replace common JSON-breaking characters
        content = content.replace('\xa0', ' ') # Non-breaking space

        # Remove markdown escaping for underscores (e.g., agent\_count -> agent_count)
        content = content.replace(r'\_', '_')
        
        # Handle cases where the LLM outputs Python-style dicts with single quotes
        # 1. Replace single-quoted keys: 'key': -> "key":
        content = re.sub(r"'([\w@\s]+)':", r'"\1":', content)
        
        # 2. Replace single-quoted string values: : 'value' -> : "value"
        # Be careful not to replace apostrophes inside words (like user's)
        # We look for: : \s* ' (content) ' 
        # But parsing arbitrary strings with regex is hard, so we do a simpler heuristic for common simple values
        # We look for : '...' but avoiding internal quotes if possible, or just blind replace if simple
        
        # A more robust approach for values: Look for : '...' followed by comma or brace
        content = re.sub(r":\s*'([^']*)'(?=\s*[,}\]])", r': "\1"', content)
        
        # 3. Also handle empty single quoted strings: : '' -> : ""
        content = content.replace(": ''", ': ""')

        # 4. Unquoted keys: { key: -> { "key": 
        content = re.sub(r"([{,]\s*)([\w@]+):", r'\1"\2":', content)
        
        # Remove trailing commas (e.g. "key": "val", } -> "key": "val" })
        content = re.sub(r',\s*([}\]])', r'\1', content)
        
        return content

    @staticmethod
    def _parse_json_from_response(response_content: str) -> Dict[str, Any]:
        """
        Parse JSON dictionary from LLM response, handling various formats.
        
        Args:
            response_content: The raw response content from the LLM
            
        Returns:
            Parsed JSON as dictionary or empty dict if parsing fails
        """
        # Sanitize content first
        response_content = InputParser._sanitize_json_string(response_content)

        # Try direct JSON parsing
        try:
            return json.loads(response_content)
        except json.JSONDecodeError:
            # Try to repair truncated JSON
            repaired = InputParser._repair_truncated_json(response_content)
            try:
                if repaired != response_content:
                    return json.loads(repaired)
            except json.JSONDecodeError:
                pass
            
        # Try extracting JSON from code block
        result = InputParser._parse_json_structure(response_content, r'```(?:json)?\s*(.*?)\s*```')
        if result:
            return result
            
        # Try extracting any JSON-like structure
        result = InputParser._parse_json_structure(response_content, r'(\{.*\})')
        if result:
            return result
        
        # Try finding the largest outer bracket pair as a fallback
        try:
            # Look for everything between the first '{' and the last '}'
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}')
            
            if start_idx != -1:
                # If we have a closing brace, use that range
                if end_idx != -1 and end_idx > start_idx:
                    json_str = response_content[start_idx:end_idx+1]
                else:
                    # If no closing brace, take everything from the start and try to repair it
                    json_str = response_content[start_idx:]
                
                # A final attempt to fix single quotes in the extracted block
                if '"' not in json_str or (json_str.find("'") < json_str.find('"') and "'" in json_str):
                    json_str = json_str.replace("'", '"')
                    
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Final attempt: repair the extracted block if it's truncated
                    repaired_block = InputParser._repair_truncated_json(json_str)
                    try:
                        return json.loads(repaired_block)
                    except json.JSONDecodeError:
                        pass
        except (json.JSONDecodeError, ValueError):
            pass

        # Return empty dict if all extraction attempts failed
        return {}

    @staticmethod
    def _repair_truncated_json(json_str: str) -> str:
        """Attempt to repair truncated JSON by closing open braces and brackets."""
        json_str = json_str.strip()
        if not json_str:
            return ""
            
        # Balance braces and brackets
        braces = json_str.count('{') - json_str.count('}')
        brackets = json_str.count('[') - json_str.count(']')
        
        # Remove trailing colon or comma which might prevent parsing even after closing
        json_str = re.sub(r'[:,\s]+$', '', json_str)
        
        # If inside a string value that isn't closed
        if json_str.count('"') % 2 != 0:
            json_str += '"'
            
        # Close open structures
        json_str += ']' * max(0, brackets)
        json_str += '}' * max(0, braces)
        
        return json_str
    
    @staticmethod
    def _parse_list_from_response(response_content: str) -> List[str]:
        """
        Parse JSON list from LLM response, handling various formats.
        
        Args:
            response_content: The raw response content from the LLM
            
        Returns:
            Parsed list or empty list if parsing fails
        """
        # Try direct JSON parsing
        try:
            result = json.loads(response_content)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
            
        # Try extracting list from code block
        result = InputParser._parse_json_structure(response_content, r'```(?:json)?\s*(\[.*?\])\s*```', is_list=True)
        if result:
            return result
            
        # Try extracting any list-like structure
        result = InputParser._parse_json_structure(response_content, r'(\[.*?\])', is_list=True)
        if result:
            return result
        
        # Return empty list if all extraction attempts failed
        return []

    async def parse_input(
        self, 
        user_input: str, 
        model_name: str = "custom-vlm", 
        temperature: float = 0
    ) -> Dict[str, Any]:
        """
        Parse user input to extract field information in a single step.
        
        Args:
            user_input: The natural language input from the user
            model_name: The name of the LLM to use
            temperature: The temperature setting for the model (0-1)
            
        Returns:
            Dictionary of extracted field values
            
        Raises:
            ValueError: If user_input is empty
        """
        self._validate_input(user_input)
        
        # Extract all fields from input
        result = await extract_fields_from_input(
            user_input,
            model_name, 
            temperature
        )
        
        return result

    async def parse_input_for_field(
        self, 
        user_input: str, 
        field_name: str,
        model_name: str = "custom-vlm", 
        temperature: float = 0
    ) -> Any:
        """
        Parse user input to extract information for a specific field.
        
        Args:
            user_input: The natural language input from the user
            field_name: The name of the field to extract
            model_name: The name of the LLM to use
            temperature: The temperature setting for the model (0-1)
            
        Returns:
            Extracted value for the specified field
            
        Raises:
            ValueError: If field_name doesn't exist or user_input is empty
        """
        self._validate_input(user_input)
        self._validate_fields([field_name])
        
        extracted_data = await extract_fields_from_input(
            user_input, 
            model_name, 
            temperature
        )
        
        return extracted_data.get(field_name, "")


    def get_available_fields(self) -> List[str]:
        """
        Get the list of available fields.
        
        Returns:
            List of field names
        """
        return list(self.field_descriptions.keys())
    
    def get_field_description(self, field_name: str) -> str:
        """
        Get the description for a specific field.
        
        Args:
            field_name: The name of the field
            
        Returns:
            Description string for the field
        """
        return self.field_descriptions.get(field_name, "No description available.")

# Create a singleton instance
input_parser = InputParser()

async def extract_fields_from_input(
    user_input: str, 
    model_name: str = "custom-vlm", 
    temperature: float = 0
) -> Dict[str, Any]:
    """
    Extract field information from user input using an LLM in a single step.
    
    Args:
        user_input: The natural language input from the user
        model_name: The name of the LLM to use
        temperature: The temperature setting for the model (0-1)
        
    Returns:
        Dictionary of extracted field values
    """
    field_descriptions = input_parser.field_descriptions
    
    # Create the extraction prompt
    prompt = input_parser._create_extraction_prompt(user_input)
    
    # Get LLM and generate extraction
    try:
        llm = get_llms(model_name, temperature)
        
        system_message = SystemMessage(content="You are a strict JSON generator. Output only valid JSON.")
        response = await llm.ainvoke(
            [system_message, HumanMessage(content=prompt)]
        )
        
        # Parse the response
        content = response.content if hasattr(response, 'content') else str(response)
        result = InputParser._parse_json_from_response(content)
        
        # Apply default values for empty fields
        if "description" in result and not result["description"]:
            # Use agent_name for the default description if available
            agent_name = result.get("agent_name", "This agent")
            result["description"] = f"{agent_name} is designed to assist users with their tasks."
            
        return result
            
    except Exception as e:
        print(f"Error extracting fields: {str(e)}")
        return {}


async def extract_fields_from_input_stream(
    user_input: str, 
    model_name: str = "custom-vlm", 
    temperature: float = 0
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream the extraction of field information from user input using an LLM.
    
    Args:
        user_input: The natural language input from the user
        model_name: The name of the LLM to use
        temperature: The temperature setting for the model (0-1)
        
    Yields:
        Dictionary updates with the extracted field values as they are generated
    """
    # Create the extraction prompt 
    prompt = input_parser._create_extraction_prompt(user_input)
    
    # Get LLM and generate extraction
    try:
        llm = get_llms(model_name, temperature)
        
        system_message = SystemMessage(content="You are a strict JSON generator. Output only valid JSON.")
        
        # Start with empty content to accumulate tokens
        accumulated_content = ""
        partial_result = {}
        
        # Use streaming response
        async for chunk in llm.astream(
            [system_message, HumanMessage(content=prompt)]
        ):
            if not hasattr(chunk, 'content'):
                continue
                
            content_chunk = chunk.content
            accumulated_content += content_chunk
            
            # Try to parse the accumulated content
            extracted_data = InputParser._parse_json_from_response(accumulated_content)
            
            # Log debug info occasionally
            if len(accumulated_content) % 50 == 0:
                print(f"DEBUG Stream: Content length {len(accumulated_content)}")
                print(f"DEBUG Stream: Content peek: {accumulated_content[-100:]}")  # Log last 100 chars

            # Process all extracted fields
            for field, field_value in extracted_data.items():
                # Yield if we have a value and it's different from what we last yielded
                # We yield even for empty strings if the field was previously unknown
                if field_value is not None and field_value != partial_result.get(field):
                    partial_result[field] = field_value
                    # Yield an update for this field
                    logger.info(f"Yielding field update: {field}")
                    yield {field: field_value}
        
        # Final safety yield - ensure we send everything we have at the end
        if partial_result:
            logger.info(f"Final yield of {len(partial_result)} fields")
            yield partial_result
        else:
            # If we still have nothing, try one last aggressive parse of the full content
            last_ditch_result = InputParser._parse_json_from_response(accumulated_content)
            if last_ditch_result:
                logger.info(f"Last ditch extraction successful: {list(last_ditch_result.keys())}")
                yield last_ditch_result
            else:
                logger.warning("All extraction attempts failed for stream.")
                yield {}
            
    except Exception as e:
        print(f"Error streaming field extraction: {str(e)}")
        yield {}

async def extract_keywords_from_agent(
    agent_name: str,
    description: str,
    model_name: str = "custom-vlm",
    temperature: float = 0
) -> List[str]:
    """
    Extract 5-6 relevant keywords from agent name and description.
    
    Args:
        agent_name: The name of the agent
        description: The description of the agent
        model_name: The name of the LLM to use
        temperature: The temperature setting for the model (0-1)
        
    Returns:
        List of 5-6 keywords
    """
    
    try:
        llm = get_llms(model_name, temperature)
        
        prompt = create_keyword_extraction_prompt(agent_name, description)
        
        system_message = SystemMessage(content="You are a strict JSON generator. Output only valid JSON.")
        response = await llm.ainvoke(
            [system_message, HumanMessage(content=prompt)]
        )
        
        # Parse the response
        content = response.content if hasattr(response, 'content') else str(response)
        keywords = InputParser._parse_list_from_response(content)
        
        # Ensure we have 5-6 keywords
        if len(keywords) < 5:
            keywords.extend(['automation', 'helper'][:5 - len(keywords)])
        elif len(keywords) > 6:
            keywords = keywords[:6]
            
        return keywords
            
    except Exception as e:
        return ['automation', 'helper', 'assistant']  # Default keywords on error 

async def parse_multi_agent_input(
    user_input: str,
    model_name: str = "custom-vlm",
    temperature: float = 0
) -> Dict[str, Any]:
    """
    Parse user input to detect multiple agents and their differences.
    
    Args:
        user_input: The natural language input from the user
        model_name: The name of the LLM to use
        temperature: The temperature setting for the model (0-1)
        
    Returns:
        Dictionary containing:
        - agent_count: Detected number of agents
        - has_multi_agent: Whether multiple agents were detected
        - common_attributes: Dictionary of attributes common to all agents
        - agent_variations: List of dictionaries with agent-specific differences
        - need_more_info: Whether more information is needed from the user
    """
    try:
        llm = get_llms(model_name, temperature)
        
        prompt = create_multi_agent_parsing_prompt(user_input)
        
        system_message = SystemMessage(content="You are a strict JSON generator. Output only valid JSON. Do not add any conversational text or markdown.")
        response = await llm.ainvoke(
            [system_message, HumanMessage(content=prompt)]
        )
        
        # Parse the response
        content = response.content if hasattr(response, 'content') else str(response)
        result = InputParser._parse_json_from_response(content)
        
        # Ensure the response has the expected structure
        if not result:
            return {
                "has_multi_agent": True,
                "agent_count": 1,
                "common_attributes": {},
                "agent_variations": [],
                "need_more_info": True,
                "missing_info": f"Could not parse the input. Raw output: {content[:200]}..." 
            }
            
        # Set defaults for any missing fields
        result["has_multi_agent"] = True
        result.setdefault("agent_count", len(result.get("agent_variations", [])) or 1)
        result.setdefault("common_attributes", {})
        result.setdefault("agent_variations", [])
        result.setdefault("need_more_info", len(result.get("agent_variations", [])) == 0)
        result.setdefault("missing_info", "" if not result.get("need_more_info") else "Need more details about each agent's specific attributes.")
        
        # Convert any agent_style to agent_name for consistency
        if "agent_style" in result["common_attributes"]:
            result["common_attributes"]["agent_name"] = result["common_attributes"].pop("agent_style")
            
        # Ensure each agent variation has agent_name and description
        for agent in result["agent_variations"]:
            if "agent_style" in agent and "agent_name" not in agent:
                agent["agent_name"] = agent.pop("agent_style")
                
            if "agent_name" not in agent:
                agent["agent_name"] = "Unnamed Agent"
                
            if "description" not in agent:
                agent["description"] = "No specific description provided"

        # FORCE need_more_info to False if we have any agents
        # This overrides LLM hesitation - we prefer to show Draft agents than block the user
        if len(result["agent_variations"]) > 0 or result.get("agent_count", 0) > 0:
            result["need_more_info"] = False
            result["missing_info"] = ""
            result["has_multi_agent"] = True
        
        return result
        
        return result
            
    except Exception as e:
        print(f"Error parsing multi-agent input: {str(e)}")
        return {
            "has_multi_agent": True,
            "agent_count": 1,
            "common_attributes": {},
            "agent_variations": [],
            "need_more_info": True,
            "missing_info": f"Error analyzing input: {str(e)}"
        } 