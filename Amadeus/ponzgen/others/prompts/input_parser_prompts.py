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
    Analyze the user input to detect multiple agents. Your goal is to ALWAYS generate valid, complete agent definitions, even if the input is minimal. 
    You must INFER and GENERATE missing details based on the roles described.
    
    ### User Input ###
    {user_input}
    
    ### Instructions ###
    1. Identify distinct agents. If the user says "frontend backend devops", you detect 3 agents.
    2. INFER the following fields for EACH agent based on their implied role:
       - agent_name: A creative, professional name (e.g., "Frontend" -> "PixelArchitect", "UI/UX Specialist").
       - description: A detailed professional summary of their responsibilities.
       - agent_style: A persona definition (e.g., "I am a meticulous DevOps engineer...").
       - tools: A list of likely tools they would use (e.g., Frontend -> ["React", "HTML", "CSS"], DevOps -> ["Docker", "Kubernetes"]).
       - experience: Estimated years of experience (e.g., "Senior", "5 years").
       - industry: The likely industry (e.g., "Software Development", "E-commerce").
       - target_audience: Who they serve (e.g., "End Users", "Development Team").
       - specialization: Core focus (e.g., "Responsive Design", "CI/CD Pipelines").
       - response_length: "concise" or "detailed".
       - formality_level: "professional" or "casual".
       - on_status: true.
       - company_id: "".
    
    3. Return your analysis as a JSON object with the following structure:
    
    ```json
    {{
        "agent_count": <number of agents detected>,
        "common_attributes": {{
            "industry": "<inferred common industry>",
            "company_id": ""
        }},
        "agent_variations": [
            {{
                "agent_name": "<inferred name>",
                "description": "<inferred description>",
                "agent_style": "<inferred style>",
                "tools": ["<inferred tool 1>", "<inferred tool 2>"],
                "experience": "<inferred experience>",
                "target_audience": "<inferred audience>",
                "specialization": "<inferred specialization>",
                "response_length": "detailed",
                "formality_level": "professional",
                "on_status": true
            }},
            ...
        ],
        "need_more_info": false,
        "missing_info": ""
    }}
    ```
    
    4. CRITICAL: Set `need_more_info` to `true` ONLY if the input is completely nonsensical. If you can guess the roles, SET IT TO `false` and FILL IN THE BLANKS.
    5. Be creative! If the user says "startup team", invent a CEO, CTO, and Product Manager.
    6. Ensure `tools` is always a list of strings.
    
    ### Response Format ###
    Only return the JSON object. Do not wrap it in markdown code blocks. Do not add any conversational text.
    """
