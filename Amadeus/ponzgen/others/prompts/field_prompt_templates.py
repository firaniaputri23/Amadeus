"""
Prompt templates for field autofill.
"""

from typing import Dict, Any, Optional

def construct_system_prompt(
    field_name: str, 
    json_field: Dict[str, Any], 
    existing_field_value: str = "",
    field_descriptions: Optional[Dict[str, str]] = None
) -> str:
    """
    Construct a system prompt for field autofill.
    
    Args:
        field_name: The name of the field to generate
        json_field: JSON object containing other field values
        existing_field_value: Optional existing value for continuation
        field_descriptions: Dictionary of field descriptions, if None an empty dict will be used
        
    Returns:
        System prompt string
    """
    # Use provided field descriptions or empty dict
    if field_descriptions is None:
        field_descriptions = {}
        
    target_field_desc = field_descriptions.get(field_name, "No description available.")

    # Construct the system prompt
    system_prompt = "### System Prompt ###\n"
    system_prompt += f"Fill in the field of : **{field_name}**.\n"
    
    if existing_field_value.strip():
        system_prompt += f"- **Existing Value (Please do continuation autocompletion after this) **: {existing_field_value}\n"
    
    system_prompt += "- Generate the field based on context bellow.\n"
    system_prompt += "\n### Context ###\n"
    
    for key, value in json_field.items():
        description = field_descriptions.get(key, "No description available.")
        system_prompt += f"- Field_name: **{key}** \n Desc: ({description}): {value}\n"
    
    system_prompt += "\n### Instructions ###\n"
    system_prompt += (
        "- Ensure logical consistency with the given data.\n"
        "- Output ONLY the completed field value (direct to answer, no JSON, '', or structured format).\n"
        f"- **Description of this field. You can enhance the result based on here.**: {target_field_desc}\n"
    )
    
    print(system_prompt)
    return system_prompt