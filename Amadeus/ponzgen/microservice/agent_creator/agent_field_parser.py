"""
User Input Parser Module

This module provides a high-level interface for parsing user input to extract agent field information.
It serves as a wrapper around the core input parsing functionality.
"""

from typing import Dict, Any, List, Optional

from .utils.input_parser import input_parser


class UserInputParser:
    """
    High-level interface for parsing user input to extract agent field information.
    This class wraps the core InputParser functionality with a simpler API.
    """
    
    def __init__(self):
        """Initialize the UserInputParser."""
        self._parser = input_parser
    
    async def parse_input(
        self, 
        user_input: str, 
        target_fields: Optional[List[str]] = None,
        model_name: str = "custom-vlm", 
        temperature: float = 0
    ) -> Dict[str, Any]:
        """
        Parse user input to extract field information.
        
        Args:
            user_input: The natural language input from the user
            target_fields: List of field names to extract (if None, detects fields automatically)
            model_name: The name of the LLM to use
            temperature: The temperature setting for the model (0-1)
            
        Returns:
            Dictionary of extracted field values
        
        Raises:
            ValueError: If user_input is empty or target_fields contains invalid fields
        """
        return await self._parser.parse_input(
            user_input,
            target_fields,
            model_name,
            temperature
        )
    
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
        return await self._parser.parse_input_for_field(
            user_input,
            field_name,
            model_name,
            temperature
        )
    
    def _get_available_fields(self) -> List[str]:
        """
        Get the list of available fields.
        
        Returns:
            List of field names
        """
        return self._parser.get_available_fields()
    
    def _get_field_description(self, field_name: str) -> str:
        """
        Get the description for a specific field.
        
        Args:
            field_name: The name of the field
            
        Returns:
            Description string for the field
        """
        return self._parser.get_field_description(field_name)


# Create a singleton instance
user_input_parser = UserInputParser() 