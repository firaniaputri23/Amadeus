"""
Field Utilities Module

This module provides utilities for working with field descriptions and autofills.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

def load_field_descriptions() -> Dict[str, str]:
    """
    Load field descriptions from the config file.
    
    Returns:
        Dictionary mapping field names to their descriptions
    """
    try:
        field_desc_path = Path("config/field_desc.json")
        if not field_desc_path.exists():
            print(f"Warning: Field description file not found at {field_desc_path}. Using empty descriptions.")
            return {}
            
        with open(field_desc_path, "r") as file:
            field_descriptions = json.load(file)
        return field_descriptions
    except Exception as e:
        print(f"Error loading field descriptions: {e}")
        return {}