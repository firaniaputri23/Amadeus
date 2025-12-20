"""
Input Parser Prompt Templates

This module provides prompt templates for the input parser module.
"""

from typing import Dict, Any, List

def create_extraction_prompt(user_input: str, field_descriptions: Dict[str, str]) -> str:
    """
    Create a prompt for extracting field information from user input.
    
    Args:
        user_input: The natural language input from the user
        field_descriptions: Dictionary mapping field names to their descriptions
        
    Returns:
        Prompt string for the LLM
    """
    prompt_parts = [
        "### Task ###",
        "Extract information for the following fields from the user input. Analyze the text carefully and identify any information that matches the field descriptions.\n",
        
        "### Field Descriptions ###"
    ]
    
    for field, description in field_descriptions.items():
        prompt_parts.append(f"- {field}: {description}")
    
    prompt_parts.extend([
        "\n### User Input ###",
        user_input,
        
        "\n### Instructions ###",
        "1. Only extract information for fields that are explicitly or implicitly mentioned in the user input.",
        "2. For each mentioned field, extract relevant information if present in the user input.",
        "3. Return only the extracted information, not explanations or reasoning.",
        "4. Format your response as a valid JSON object with the field names as keys.",
        "5. For the 'agent_style' field, create an agent style that will be used to generate the agent's behavior.",
        "6. For the 'description' field, you MUST provide a concise one-sentence summary about the agent's purpose and capabilities, even if there's limited information. Never leave this field empty. Default description: This agent is designed to assist users with their tasks.",
        
        "\n### Response Format ###",
        "Only return the JSON object. Do not wrap it in markdown code blocks. Do not add any conversational text."
    ])
    
    return "\n".join(prompt_parts)

def create_keyword_extraction_prompt(agent_name: str, description: str) -> str:
    """
    Create a prompt for extracting keywords from agent name and description.
    
    Args:
        agent_name: The name of the agent
        description: The description of the agent
        
    Returns:
        Prompt string for the LLM
    """
    return f"""
    ### Task ###
    Extract 5-6 most relevant keywords from the agent name and description below.
    Keywords should be single words that best represent the agent's core field and functionality.
    
    ### Agent Information ###
    Name: {agent_name}
    Description: {description}
    
    ### Instructions ###
    1. Return exactly 5-6 single-word keywords
    2. Keywords should be lowercase
    3. Keywords should be specific and descriptive
    4. Return as a JSON array of strings
    5. Do not include stop words or generic terms like "agent" or "assistant" or "solver"
    6. Include words that are relevant to the agent's field and functionality
    
    ### Response Format ###
    Only return the JSON array. Do not wrap it in markdown code blocks. Do not add any conversational text.
    """

def create_multi_agent_parsing_prompt(user_input: str) -> str:
    """
    Create a prompt for parsing multi-agent input.
    
    Args:
        user_input: The natural language input from the user
        
    Returns:
        Prompt string for the LLM
    """
    return f"""
    ### Task ###
    Analyze the user input to determine if they are describing multiple agents and if so, extract information about each agent.
    
    ### User Input ###
    {user_input}
    
    ### Instructions ###
    1. Identify how many distinct agents are being described.
    2. Extract common attributes that apply to all agents (if any).
    3. Extract specific differences between agents.
    4. Return your analysis as a JSON object with the following structure:
    
    ```json
    {{
        "agent_count": <number of agents detected>,
        "common_attributes": {{
            "agent_name": "<common name pattern if applicable>",
            "description": "<common description if applicable>",
            "other_common_field": "<value>"
            ...
        }},
        "agent_variations": [
            {{
                "agent_name": "<name of agent 1>",
                "description": "<specific description for agent 1>",
                "specific_field_1": "<value specific to agent 1>"
            }},
            {{
                "agent_name": "<name of agent 2>",
                "description": "<specific description for agent 2>",
                "specific_field_2": "<value specific to agent 2>"
            }},
            ...
        ],
        "need_more_info": true/false,
        "missing_info": "<description of what information is missing>"
    }}
    ```
    
    5. Set need_more_info to true if you cannot determine the number of agents or clear differences between them.
    6. Be precise about differentiating factors between agents.
    7. Make sure every agent variation has at minimum these fields:
       - agent_name (a unique name for each agent)
       - description (a specific description for each agent)
    8. Don't use "agent_style" - use "agent_name" instead for naming fields consistently.
    9. All agents must have the same field structure (include the same fields even if empty).
    
    ### Response Format ###
    Only return the JSON object. Do not wrap it in markdown code blocks. Do not add any conversational text.
    """ 