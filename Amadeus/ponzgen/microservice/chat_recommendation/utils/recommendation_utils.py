from typing import List
from langchain_core.messages import HumanMessage, SystemMessage
import logging
import json
import re
import traceback

from ...agent_boilerplate.boilerplate.utils.get_llms import get_llms
from ...agent_boilerplate.boilerplate.errors import BadRequestError, InternalServerError
from others.prompts.recommendation_prompts import create_recommendation_system_prompt, create_recommendation_human_prompt

def extract_topics(text: str) -> List[str]:
    """
    Extract key topics from the input text.
    
    Args:
        text: Input text to extract topics from
        
    Returns:
        List of extracted topics
    """
    # Simple implementation - split by common separators and take first few words
    words = re.split(r'[,\s]+', text.strip())
    # Take first 3 words as topics
    return words[:3]

def sanitize_json_string(content: str) -> str:
    """
    Sanitize JSON string by replacing smart quotes and other common issues.
    """
    # Replace smart double quotes with standard double quote
    content = content.replace('“', '"').replace('”', '"')
    
    # Replace smart single quotes with STANDARD DOUBLE QUOTE (JSON requires double quotes)
    content = content.replace("‘", '"').replace("’", '"')
    
    # Remove trailing commas (e.g. "key": "val", } -> "key": "val" })
    content = re.sub(r',\s*([}\]])', r'\1', content)
    
    return content

def parse_recommendation_response(response: str) -> List[str]:
    """
    Parse the LLM response to extract recommendations.
    
    Args:
        response: LLM response text
        
    Returns:
        List of recommendations
    """
    try:
        # Strip markdown code blocks if present (```json ... ``` or ``` ... ```)
        response = response.strip()
        if response.startswith('```'):
            # Remove opening ```json or ```
            response = re.sub(r'^```(?:json)?\s*\n?', '', response)
            # Remove closing ```
            response = re.sub(r'\n?```\s*$', '', response)
            response = response.strip()
        
        # Sanitize content first
        response = sanitize_json_string(response)
        
        parsed_result = None
        
        # Try direct JSON parsing
        try:
            parsed_result = json.loads(response)
        except json.JSONDecodeError:
            pass
            
        if parsed_result is None:
            # Try to find a JSON array in the response (regex)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    parsed_result = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        if parsed_result is None:
             # Try finding the largest outer bracket pair as a fallback
            try:
                start_idx = response.find('[')
                end_idx = response.rfind(']')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx+1]
                    parsed_result = json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # If we still don't have a result, fallback to line splitting
        if parsed_result is None:
            # Fallback to line-based parsing
            lines = response.strip().split('\n')
            recommendations = []
            for line in lines:
                line = line.strip(' "\'[]{}')
                # Skip empty lines and common delimiters
                if line and not line.startswith(('```', '---', '===', '###')):
                    # Clean up list markers like "1. ", "- "
                    line = re.sub(r'^[\d-]+\.\s*|^-\s*', '', line)
                    recommendations.append(line)
            return recommendations

        # Handle both list and dict formats from parsed JSON
        recommendations = parsed_result
        if isinstance(recommendations, dict):
            if 'recommendations' in recommendations:
                recommendations = recommendations['recommendations']
            else:
                recommendations = list(recommendations.values())
        elif not isinstance(recommendations, list):
            recommendations = [str(recommendations)]
            
        # Clean up recommendations (remove non-strings)
        recommendations = [
            str(rec).strip(' "\'') for rec in recommendations 
            if rec
        ]
            
        return recommendations

    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        # Last ditch effort: return non-empty lines
        return [line.strip() for line in response.split('\n') if line.strip() and len(line.strip()) > 10][:4]

def validate_recommendations(recommendations: List[str]) -> List[str]:
    """
    Validate and clean up recommendations.
    
    Args:
        recommendations: List of recommendations
        
    Returns:
        List of validated recommendations
    """
    # Remove empty recommendations
    recommendations = [rec for rec in recommendations if rec]
    
    # Limit to 4 recommendations
    return recommendations[:4]

async def generate_recommendations_impl(
    user_input: str,
    chat_history_messages: List[str],
    model_name: str = "custom-vlm",
    temperature: float = 0,
    streaming: bool = False
) -> List[str]:
    """
    Implementation of chat recommendations generation.

    Args:
        user_input: The current message from the user
        chat_history_messages: List of previous chat messages
        model_name: Name of the LLM model to use
        temperature: Temperature parameter for the LLM
        streaming: Whether to stream the response (not used)

    Returns:
        List of up to 4 chat recommendations

    Raises:
        BadRequestError: If user_input is empty
        InternalServerError: If recommendation generation fails
    """
    if not user_input:
        raise BadRequestError("User input cannot be empty")

    try:
        print(f"Getting LLM with model: {model_name}, temperature: {temperature}")
        # Get the LLM with specified parameters
        llm = get_llms(model_name=model_name, temperature=temperature)
        print("Got LLM instance")

        print("Generating recommendations...")
        # Generate the recommendations with both system and human messages
        messages = [
            SystemMessage(content=create_recommendation_system_prompt()),
            HumanMessage(content=create_recommendation_human_prompt(user_input, chat_history_messages))
        ]
        
        try:
            # Get response from LLM
            response = await llm.ainvoke(messages)
            
            # check if response is string or object with content attribute
            if isinstance(response, str):
                response_content = response
            elif hasattr(response, 'content'):
                response_content = response.content
            else:
                response_content = str(response)

            print(f"Raw LLM response: {response_content}")

            if not response_content:
                raise InternalServerError("Empty response from LLM")

            recommendations = parse_recommendation_response(response_content)
            print(f"Parsed recommendations: {recommendations}")
            
            if not recommendations or len(recommendations) < 2:
                raise InternalServerError(f"Failed to generate valid recommendations. Response: {response_content}")
                
            validated_recommendations = validate_recommendations(recommendations)
            if len(validated_recommendations) < 2:
                raise InternalServerError(f"Generated recommendations were insufficient. Response: {response_content}")
                
            return validated_recommendations
                
        except Exception as e:
            print(f"Error in LLM invocation or parsing: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Error args: {e.args}")
            print(f"Traceback: {traceback.format_exc()}")
            raise InternalServerError(f"Failed to generate recommendations: {str(e)}")
            
    except Exception as e:
        print(f"Error in generate_recommendations_impl: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        print(f"Traceback: {traceback.format_exc()}")
        raise InternalServerError(f"Failed to initialize LLM: {str(e)}") 