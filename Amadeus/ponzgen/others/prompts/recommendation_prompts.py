"""
Recommendation Prompt Templates

This module provides prompt templates for the chat recommendation module.
"""

def create_recommendation_system_prompt() -> str:
    """
    Create the system prompt for recommendation generation.
    
    Returns:
        System prompt string for the LLM
    """
    return """You are a helpful AI assistant. Based on the following conversation history and current user input,
generate up to 4 relevant chat recommendations. You MUST format your response as a JSON array of strings, with no other text.
Each recommendation should be specific to the user's request, mentioning exact tools, commands, or techniques.

### Response Format ###
You must output ONLY a valid JSON array of strings. 
Do not wrap the JSON in markdown code blocks. 
Do not include any conversational text like "Here are the recommendations:" or "I hope this helps".
Your entire output should start with '[' and end with ']'.

Example response:
[
    "Use FastAPI's built-in OAuth2PasswordBearer for user authentication, implementing JWT tokens with a 15-minute expiry.",
    "Create a SQLAlchemy model for users with email, hashed_password, and is_active fields, then implement CRUD operations.",
    "Set up Pydantic models for request/response validation, including UserCreate and UserResponse schemas.",
    "Implement rate limiting using FastAPI's dependencies and Redis for storing request counts."
]"""

def create_recommendation_human_prompt(user_input: str, chat_history_messages: list) -> str:
    """
    Create the human prompt for recommendation generation.
    
    Args:
        user_input: The current message from the user
        chat_history_messages: List of previous chat messages
        
    Returns:
        Human prompt string for the LLM
    """
    history_text = '\n'.join(chat_history_messages) if chat_history_messages else 'No previous messages'

    return f"""Based on the following conversation history and current user input, generate 2-4 relevant technical recommendations.
Focus on providing specific, actionable advice that directly addresses the user's needs.

Conversation History:
{history_text}

Current User Input:
{user_input}

Provide recommendations that are:
1. Are directly related to the current conversation
2. Help move the conversation forward
3. Are specific and actionable
4. Are concise (1-2 sentences each)""" 